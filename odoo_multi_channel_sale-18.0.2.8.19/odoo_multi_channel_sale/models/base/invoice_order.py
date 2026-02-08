# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import api, models
from logging import getLogger
_logger = getLogger(__name__)

class MultiChannelSkeleton(models.TransientModel):
    _inherit = 'multi.channel.skeleton'

    def _get_journal_code(self, string, sep=' '):
        """
        Takes payment method as argumnet and generates a jurnal code.
        """
        tl = [t.title()[0] for t in string.split(sep)]
        code = ''.join(tl)
        code = code[0:3]
        is_exist = self.env['account.journal'].search([('code', '=', code)])
        if is_exist:
            for i in range(99):
                is_exist = self.env['account.journal'].search(
                    [('code', '=', code + str(i))])
                if not is_exist:
                    return code + str(i)[-5:]
        return code

    def _get_journal_name(self, string):
        is_exist = self.env['account.journal'].search([('name', '=', string)])
        if is_exist:
            for i in range(99):
                is_exist = self.env['account.journal'].search(
                    [('name', '=', string + str(i))])
                if not is_exist:
                    return string + str(i)
        return string

    @api.model
    def CreatePaymentMethod(self, ChannelID, PaymentMethod):
        """
        Takes PaymentMethod as argument and returns Journal ID
        """
        journal_id = False
        status_message = ''
        if PaymentMethod:
            journal_id = 0
            MapObj = self.env['channel.account.journal.mappings']
            exists = MapObj.search(
                [('store_journal_name', '=', PaymentMethod),('channel_id', '=', ChannelID.id)])
            if not exists:
                journal = {
                    'name': self._get_journal_name(PaymentMethod),
                    'code': self._get_journal_code(PaymentMethod),
                    'type': 'bank',
                }
                journal_obj = self.env['account.journal'].create(journal)
                journal_id = journal_obj.id
                if journal_obj:
                    MapVals = {
                        'name': journal_obj.name,
                        'store_journal_name': PaymentMethod,
                        'journal_code': journal_obj.code,
                        'odoo_journal': journal_id,
                        'odoo_journal_id': journal_id,
                        'channel_id': ChannelID.id,
                        'ecom_store': ChannelID.channel}
                    MapObj.create(MapVals)
            else:
                journal_id = exists[0].odoo_journal_id
        return {
            'journal_id': journal_id,
            'status_message': status_message
        }

    @api.model
    def create_order_invoice(self, order_obj):
        """Creates Order Invoice by request from Store.
        @param order_id: Odoo Order ID
        @return: a dictionary containig Odoo Invoice IDs and Status with Status Message
        """
        invoice_id = False
        status = True
        status_message = "Invoice==> Created. "
        try:
            if not order_obj.invoice_ids:
                invoice_id = order_obj._create_invoices()
            else:
                status = False
                status_message = "<br/>Already Created"
        except Exception as e:
            status = False
            status_message = "<br/>Error in creating Invoice: %s <br/>" % str(e)
        finally:
            return {
                'status': status,
                'status_message': status_message,
                'invoice_id': invoice_id and invoice_id[0]
            }

    @api.model
    def SetOrderPaid(self, payment_data):
        """Make the order Paid in Odoo using store payment data
        @param payment_data: A standard dictionary consisting of 'order_id', 'journal_id', 'amount'
        @param context: A Dictionary with key 'ecommerce' to identify the request from E-Commerce
        @return:  A dictionary of status and status message of transaction"""
        context = dict(self._context or {})
        status = True
        counter = 0
        draft_invoice_ids = self.env['account.move']
        invoice_id = False
        journal_id = payment_data.get('journal_id', False)
        sale_obj = self.env['sale.order'].browse(payment_data['order_id'])
        status_message = ""
        date_invoice = payment_data.get('date_invoice')
        if not sale_obj.invoice_ids:
            create_invoice = self.create_order_invoice(sale_obj)
            status_message += create_invoice['status_message']
            if create_invoice['status']:
                draft_invoice_ids += create_invoice['invoice_id']
        elif sale_obj.invoice_ids:
            for invoice in sale_obj.invoice_ids:
                if invoice.state == 'posted':
                    invoice_id = invoice.id
                elif invoice.state == 'draft':
                    if date_invoice:
                        invoice.write({'invoice_date': date_invoice})
                    draft_invoice_ids += invoice
                counter += 1
        if counter <= 1:
            try:
                if draft_invoice_ids:
                    invoice_id = draft_invoice_ids[0]
                    if date_invoice:
                        invoice_id.write({'invoice_date': date_invoice})
                    invoice_id.action_post()
                    invoice_id = invoice_id.id
                # Setting Context for Payment Wizard
                register_wizard = self.env['account.payment.register'].with_context({
                    'active_model': 'account.move',
                    'active_ids': [invoice_id]
                })
                register_wizard_obj = register_wizard.create({
                    'journal_id': journal_id
                })
                register_wizard_obj.action_create_payments()
                status_message += 'Invoice==> Paid. '
            except Exception as e:
                status = False
                status_message = "<br/>Error while invoice processing.%r<br/>" % (e)

        else:
            status = False
            status_message = "<br/>Multiple validated Invoices found for the Odoo order. Cannot make Payment<br/>"
        return {
            'status_message': status_message,
            'status': status
        }

    @api.model
    def _ConfirmOrderAndCreateInvoice(self, OrderObj, ChannelID, PaymentMethod,
                                      OrderState=False, CreateInvoice=False, InvoiceState=False, ShipOrder=False, **kwargs):
        """
        Confirm order in odoo..
        @arguments order object , channel object ,order state, invoice state, payment method
        """
        status = True
        context = dict(self._context or {})
        status_message = ""
        draft_invoice_ids = []
        invoice_id = False
        sale_obj = self.env['sale.order']

        if OrderState and OrderState in ['sale', 'done']:
            if OrderObj.state in ['draft', 'sent']:
                res = self._ConfirmOdooOrder(OrderObj, **kwargs)
                status_message += res['status_message']
                status = res['status']
            if PaymentMethod and CreateInvoice:
                res_payment = self.CreatePaymentMethod(
                    ChannelID, PaymentMethod)
                data = {
                    'order_id': OrderObj.id,
                    'journal_id': res_payment['journal_id'],
                    'channel_id': ChannelID,
                    'order_state': OrderState,
                    'invoice_state': InvoiceState,
                    'date_invoice': kwargs.get('date_invoice')
                }
                date_invoice = kwargs.get('date_invoice')
                if date_invoice:
                    data['date_invoice'] = date_invoice
                if res_payment['status_message']:
                    status_message += res_payment['status_message']
                if InvoiceState == 'open':
                    create_invoice = self.create_order_invoice(OrderObj)
                    status_message += create_invoice['status_message']
                    status = create_invoice['status']
                if InvoiceState == 'paid':
                    res = self.SetOrderPaid(data)
                    status_message += res['status_message']
                    status = res['status']
            if OrderState and OrderState == 'done':
                sale_obj.action_lock()
                status_message += "Order==> Done ."
        if OrderState and OrderState == 'shipped' or ShipOrder:
            res = self.set_order_shipped(OrderObj.id, **kwargs)
            if res:
                status_message += res['status_message']
                status = res['status']

        return {'status_message': status_message,
                'status': status
                }
