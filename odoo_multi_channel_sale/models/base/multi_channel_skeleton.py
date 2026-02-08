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
    _name = 'multi.channel.skeleton'
    _description = 'Multi Channel Skeleton'

    @api.model
    def _ConfirmOdooOrder(self, order_obj, **kwargs):
        """ Confirms Odoo Order from E-Commerce
        @param order_id: Odoo/ERP Sale Order ID
        @return: a dictionary of True or False based on Transaction Result with status_message"""
        context = self._context or {}
        status = True
        status_message = ""
        try:
            order_obj.action_confirm()
            if kwargs.get('confirmation_date'):
                order_obj.write({'date_order': kwargs.get('confirmation_date')})
            status_message += "Order==> Confirmed. "
        except Exception as e:
            status_message += "Error in Confirming Order on Odoo: %s<br/>" % str(
                e)
            status = False
        finally:
            return {
                'status': status,
                'status_message': status_message
            }

    @api.model
    def _cancel_order(self, order_id, channel_id):
        status_message = ''
        status = True
        try:
            order_id.with_context(disable_cancel_warning=True).action_cancel()
            status_message += '<br/> Order ==> Cancelled. '
        except Exception as e:
            status_message += '%s' % (e)
            Status = False
        return dict(
            status_message=status_message,
            status=status,
        )

    def _SetOdooOrderState(self, order_id, channel_id, feed_order_state='', payment_method=False, **kwargs):
        status_message = "<br/>Order %s " % (order_id.name)
        if channel_id and order_id and order_id.order_line:
            context = dict(self._context or {})
            order_state = ''
            create_invoice = False
            ship_order = False
            invoice_state = ''
            om_order_state_ids = channel_id.order_state_ids
            order_state_ids = om_order_state_ids.filtered(
                lambda state: state.channel_state == feed_order_state) or channel_id.order_state_ids.filtered(
                    'default_order_state')
            if order_state_ids:
                state_id = order_state_ids[0]
                order_state = state_id.odoo_order_state
                create_invoice = state_id.odoo_create_invoice
                invoice_state = state_id.odoo_set_invoice_state
                ship_order = state_id.odoo_ship_order
            if order_state in ['cancelled']:
                res = self.with_context(context)._cancel_order(
                    order_id, channel_id)
                status_message += res['status_message']
            # In case if we enable updating cancel orders state in Odoo
            # elif order_id.state == "cancel" and order_state != "cancelled":
                # order_id.action_draft()
            else:
                res = self.with_context(context)._ConfirmOrderAndCreateInvoice(
                    order_id, channel_id, payment_method, order_state,
                    create_invoice, invoice_state, ship_order, **kwargs)
                status_message += res['status_message']
        return status_message
