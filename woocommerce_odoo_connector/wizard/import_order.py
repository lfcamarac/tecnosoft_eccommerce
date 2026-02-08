# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    See LICENSE file for full copyright and licensing details.
##########H#########Y#########P#########N#########O#########S##################

from dateutil.parser import parse

import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError
from odoo import api, fields, models,_


class ImportWoocommerceOrders(models.TransientModel):
    _name = 'import.woocommerce.orders'
    _inherit = 'import.orders'
    _description = "Import Woocommerce Orders"

    def _get_order_by_id(self, woocommerce, channel_id, **kwargs):
        order = woocommerce.get(f"orders/{kwargs.get('woocommerce_object_id')}").json()
        if "message" in order:
            raise UserError(f'Error in getting Order : {order["message"]}')
        return [self._process_order(woocommerce, channel_id, order)]

    def import_now(self, **kwargs):
        woocommerce = self._context.get('woocommerce')
        channel = self._context.get("channel_id")
        if kwargs.get('woocommerce_filter_type') == "all":
            kwargs.update({'woocommerce_object_id':False})
            kwargs.update({'woocommerce_import_date_from':False})
        elif kwargs.get('woocommerce_filter_type') == "by_date":
             kwargs.update({'woocommerce_object_id':False})
        if kwargs.get('woocommerce_object_id'):
            ids_res = str(kwargs.get('woocommerce_object_id')).split(',')
            ids_len = len(ids_res)
            if 1<ids_len<=100:
                data_list = self.with_context(ids_res_order=True)._get_order_all(woocommerce, channel, **kwargs)
            elif ids_len>100:
                raise UserError('Number of ids must be less than or equal to 100')
            else:
                data_list = self._get_order_by_id(woocommerce, channel, **kwargs)
        elif kwargs.get('woocommerce_import_date_from'):
            data_list = self._filter_order_using_date(
                woocommerce, channel, **kwargs)
        else:
            data_list = self._get_order_all(woocommerce, channel, **kwargs)
        return data_list

    def _get_woocommerce_discount_lines(self,woocommerce,data):
        amount = sum([float(line.get('discount')) for line in data["coupon_lines"]])
        tax_ids = [{"id": tax_line["rate_id"]} for tax_line in data["tax_lines"]]
        vals = {
            'line_name': "Discount",
            'line_price_unit': float(amount),
            'line_product_uom_qty': 1,
            "line_source":"discount",
            "line_taxes" : self._process_taxes(woocommerce, tax_ids)
        }
        return vals

    def _get_woocommerce_order_line(self, woocommerce, channel, data):
        order_lines = []
        prod_env = self.env["import.woocommerce.products"].create({
            "channel_id":channel.id,
            "operation":"import"
        }).woocommerce_create_product_feed
        for line in data["line_items"]:
            product_id = line["product_id"]
            feed_id = prod_env(
                woocommerce,channel, product_id)
            store_variant_id = line['variation_id']
            order_line_dict = {
                'line_name': line['name'],
                'line_price_unit': float(line['subtotal'])/int(line['quantity']),
                'line_product_uom_qty': line['quantity'],
                'line_product_id': product_id,
                'line_taxes': self._process_taxes(woocommerce,line.get("taxes"))
            }
            if store_variant_id != 0:
                order_line_dict["line_variant_ids"] = store_variant_id
            order_lines.append((0, 0, order_line_dict))
        if data.get('shipping_lines'):
            order_lines += self._get_woocommerce_shipping(woocommerce,data['shipping_lines'])
        if data.get("coupon_lines"):
            discount_line = self._get_woocommerce_discount_lines(woocommerce,data)
            order_lines.append((0,0,discount_line))
        return order_lines

    def _get_order_all(self, woocommerce, channel, **kwargs):
        params = {
                'page': kwargs.get('page'),
                'per_page': kwargs.get('page_size'),
                'order': 'asc' 
        }
        if self._context.get('ids_res_order'):
            params.update({'include':  kwargs.get('woocommerce_object_id')})
        orders = woocommerce.get(
            'orders',
            params=params
        ).json()
        if "message" in orders:
            raise UserError(f'Error in Getting Orders : {orders["message"]}')
        return list(map(lambda x: self._process_order(woocommerce,channel,x),orders))

    def _filter_order_using_date(self, woocommerce, channel, **kwargs):
        vals_list = []
        last_order = {}
        orders = woocommerce.get(
            'orders',
            params={
                'after': kwargs.get('woocommerce_import_date_from'),
                'page': kwargs.get('page'),
                'per_page': kwargs.get('page_size'),
                'order': 'asc' if kwargs.get("from_cron") else "desc"
            }
        ).json()
        if orders:
            last_order= orders[-1]  
        if kwargs.get("from_cron") and channel.update_order_date:
            updated_order = self.process_updated_order(woocommerce,channel,**kwargs)
            if updated_order:
                orders.extend(updated_order)
                channel.update_order_date = parse(updated_order[0].get("date_modified_gmt"))
        try:
            vals_list = list(map(lambda x: self._process_order(woocommerce,channel,x),orders))
            if kwargs.get("from_cron") and last_order:
                channel.import_order_date = parse(last_order.get("date_created_gmt"))
        except:
            message = "Error while importing orders : {}".format(orders["message"])
            _logger.info(message)
            if not kwargs.get("from_cron"):
                raise UserError(message)
        return vals_list

    def _get_woocommerce_shipping(self, woocommerce, shipping_line):
        return [(0,0,{
                'line_name': "Shipping",
                'line_price_unit': shipping["total"],
                'line_product_uom_qty': 1,
                'line_source': 'delivery',
                'line_taxes':self._process_taxes(woocommerce,shipping.get("taxes"))
        }) for shipping in shipping_line]

    def _process_order(self, woocommerce, channel, order):
        order_lines = self._get_woocommerce_order_line(
            woocommerce, channel, order)
        method_title = 'Delivery'
        if order['shipping_lines']:
            method_title = order['shipping_lines'][0]['method_title']
        store_partner_id = order['customer_id']
        order_dict = {
            'name': '#'+str(order['id']),
            'store_id': order['id'],
            'channel_id': channel.id,
            "channel": channel.channel,
            'partner_id': store_partner_id or order['billing']['email'],
            'payment_method': order['payment_method'],
            'line_type': 'multi',
            'carrier_id': method_title,
            'line_ids': order_lines,
            'currency': order['currency'],
            'customer_name': order['billing']['first_name']+" "+order['billing']['last_name'],
            'customer_email': order['billing']['email'],
            'order_state': order['status'],
            'note':order['customer_note'],
            'date_order':order['date_created_gmt'],
            'confirmation_date':order['date_created_gmt'],
            'date_shipping':order['date_completed_gmt'],
            'date_invoice':order['date_paid_gmt'],
        }
        if order['billing']:
            order_dict.update({
                'invoice_partner_id': store_partner_id and f'billing_{store_partner_id}' or order['billing']['email'],
                'invoice_name': order['billing']['first_name']+" "+order['billing']['last_name'],
                'invoice_email': order['billing']['email'],
                'invoice_phone': order['billing']['phone'],
                'invoice_street': order['billing']['address_1'],
                'invoice_street2': order['billing']['address_2'],
                'invoice_zip': order['billing']['postcode'],
                'invoice_city': order['billing']['city'],
                'invoice_state_code': order['billing']['state'],
                'invoice_country_code': order['billing']['country'],
            })
        if order['shipping']:
            order_dict['same_shipping_billing'] = False
            order_dict.update({
                'shipping_partner_id': store_partner_id and f'shipping_{store_partner_id}' or order['billing']['email'],
                'shipping_name': order['shipping']['first_name']+" "+order['shipping']['last_name'],
                'shipping_street': order['shipping']['address_1'],
                'shipping_street2': order['shipping']['address_2'],
                'shipping_email': order['billing']['email'],
                'shipping_zip': order['shipping']['postcode'],
                'shipping_city': order['shipping']['city'],
                'shipping_state_code': order['shipping']['state'],
                'shipping_country_code': order['shipping']['country'],
            })
        return order_dict

    def _process_taxes(self, woocommerce, taxes):
        tax_data = []
        for tax in taxes:
            data = woocommerce.get(f"taxes/{tax.get('id')}").json()
            if "message" in data :
                _logger.info("Error in getting Taxes  %r",data["message"])
                continue
            tax_data.append(
                {
                    'rate': data.get("rate"),
                    'name': data.get('name'),
                    'type': "percent"
                }
            )
        return tax_data
    def process_updated_order(self,woocommerce,channel,**kwargs):
        page_no =1
        filtered_order_list = []
        while(True):
            orders = woocommerce.get(
                            'orders',
                                params={
                            'page':page_no,
                            'per_page':kwargs.get('page_size'),
                            'order': 'desc',
                            'orderby':'modified'
                        }
                                ).json()
            filtered_orders = list(filter(lambda x: x.get('date_modified')>channel.update_order_date.isoformat()\
                ,orders))
            filtered_order_list.extend(filtered_orders)
            if not filtered_orders:
                break
            page_no+=1
        if not filtered_order_list:
            return []
        order_ids = list(map(lambda ordr: ordr.get('id'),filtered_order_list))

        mapped_order_ids = self.env['channel.order.mappings'].search([
            ('channel_id','=',channel.id),
            ('store_order_id','in',order_ids)]).mapped('store_order_id')

        updated_orders = list(filter(lambda x:str(x.get('id')) in mapped_order_ids \
             ,filtered_order_list))

        if not updated_orders:
            return []
        return updated_orders
