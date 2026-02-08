# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
import random
import string
import requests
from urllib.parse import urlencode
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.addons.odoo_multi_channel_sale.tools import extract_list as EL
from odoo.tools.translate import _

import logging
_logger = logging.getLogger(__name__)


class MultiChannelSale(models.Model):
    _inherit = "multi.channel.sale"

    woocommerce_url = fields.Char(string="URI", help='eg. http://xyz.com')
    woocommerce_consumer_key = fields.Char(
        string='Consumer Key',
        help='eg. ck_ccac94fc4362ba12a2045086ea9db285e8f02ac9',
    )
    woocommerce_secret_key = fields.Char(
        help='eg. cs_a4c0092684bf08cf7a83606b44c82a6e0d8a4cae')
    
    unique_code = fields.Char(default=lambda self: self._generate_unique_code())

    @api.model
    def get_channel(self):
        channel_names = super(MultiChannelSale, self).get_channel()
        channel_names.append(('woocommerce', 'WooCommerce'))
        return channel_names

    def get_core_feature_compatible_channels(self):
        vals = super().get_core_feature_compatible_channels()
        vals.append('woocommerce')
        return vals
    
    def woocommerce_available_configs(self):
        all_configs = [

            # 'webhook_available',
            # 'create_order_webhook',
            # 'update_order_webhook',

            # base
            # 'child_store_config',

            # Import Crons
            'cron_available',
            'import_order_cron',
            'order_created_after',
            'order_updated_after',
            'import_product_cron',
            'product_created_after',
            'import_partner_cron',
            'partner_created_after',
            'import_category_cron',

            # realtime export
            'sync_order_invoice',
            'sync_order_shipment',
            'sync_order_cancel',
        ]
        return all_configs

    def connect_woocommerce(self):
        message = ""
        req = self._get_woocommerce_connection()
        try:
            res = req.get('system_status')
            if res.ok:
                res = res.json()
            else:
                raise UserError(f"Error: {res.content}")
        except Exception as e:
            raise UserError(_("Error:"+str(e)))
        if 'message' in res:
            raise UserError(_('Connection Error: %s, %s',res['data']['status'],res['message']))
        else:
            self.state = 'validate'
            message = """
                        <p style="color:green;">
                            Successfully connected to Woocommerce
                        </p>
                    """
        return True, message

    def _get_woocommerce_connection(self):
        try:
            if self.woocommerce_consumer_key and self.woocommerce_secret_key:
                from woocommerce import API
                req = API(
                    url=self.woocommerce_url,
                    consumer_key=self.woocommerce_consumer_key,
                    consumer_secret=self.woocommerce_secret_key,
                    wp_api=True,
                    version="wc/v2",
                    timeout=40,
                    query_string_auth=True,
                    # verify_ssl=False,
                )
            else:
                raise UserError(f"Error: Consumer key and Secret key is required")
        except ModuleNotFoundError:
            _logger.error('**Python Package not found `woocommerce==3.0.0`')
            raise UserError('**Please Install Woocommerce Python Package=>(cmd: pip3 install woocommerce==3.0.0)')
        return req

#---------------------------------------Import Process ---------------------------------------------------------

    def import_woocommerce(self, object, **kwargs):
        woocommerce = self._get_woocommerce_connection()
        data_list = []
        if object == 'product.category':
            data_list = self._import_woocommerce_categories(
                woocommerce, **kwargs)
        elif object == 'res.partner':
            data_list = self._import_woocommerce_customers(
                woocommerce, **kwargs)
        elif object == 'product.template':
            data_list = self._import_woocommerce_products(
                woocommerce, **kwargs)
        elif object == 'sale.order':
            data_list = self._import_woocommerce_orders(
                woocommerce, **kwargs)
        elif object == "delivery.carrier":
            data_list = self._import_woocommerce_shipping(
                woocommerce, **kwargs)
        kwargs["page"] += 1
        return data_list, kwargs

    def _import_woocommerce_shipping(self, woocommerce, **kwargs):
        obj = self.env["import.woocommerce.shipping"].create(
            {
                'channel_id': self.id,
                'operation': 'import',
            }
        )
        return obj.with_context({
            "woocommerce":woocommerce,
            "channel_id":self,
        }).import_now(**kwargs)

    def _import_woocommerce_categories(self, woocommerce, **kwargs):
        obj = self.env['import.woocommerce.categories'].create(
            {
                'channel_id': self.id,
                'operation': 'import',
            }
        )
        return obj.with_context({
            "woocommerce": woocommerce,
            "channel_id": self,
        }).import_now(**kwargs)

    def _import_woocommerce_customers(self, woocommerce, **kwargs):
        obj = self.env['import.woocommerce.partners'].create(
            {
                'channel_id': self.id,
                'operation': 'import',
            }
        )
        return obj.with_context({
            "woocommerce": woocommerce,
            "channel_id": self,
        }).import_now(**kwargs)

    def _import_woocommerce_products(self, woocommerce, **kwargs):
        obj = self.env['import.woocommerce.products'].create(
            {
                'channel_id': self.id,
                'operation': 'import',
            }
        )
        return obj.with_context({
            "woocommerce": woocommerce,
            'channel_id': self,
        }).import_now(**kwargs)

    def _import_woocommerce_orders(self, woocommerce, **kwargs):
        obj = self.env['import.woocommerce.orders'].create(
            {
                'channel_id': self.id,
                'operation': 'import',
            }
        )
        return obj.with_context({
            'woocommerce': woocommerce,
            'channel_id': self,
        }).import_now(**kwargs)

# ----------------------------------------------Export Process -------------------------------------------

    def export_woocommerce(self, record):
        woocommerce = self._get_woocommerce_connection()
        data_list = []
        if woocommerce:
            if record._name == 'product.category':
                initial_record_id = record.id
                data_list = self._export_woocommerce_categories(
                    woocommerce, record, initial_record_id)
            elif record._name == 'product.template':
                data_list = self._export_woocommerce_product(
                    woocommerce, record)
            return data_list

    def _export_woocommerce_categories(self, woocommerce, record, initial_record_id):
        obj = self.env['export.categories'].create(
            {
                'channel_id': self.id,
                'operation': 'export',
            }
        )
        return obj.with_context({
            'woocommerce': woocommerce,
            'channel_id': self,
        }).woocommerce_export_now(record, initial_record_id)

    def _export_woocommerce_product(self, woocommerce, record):
        obj = self.env['export.templates'].create(
            {
                'channel_id': self.id,
                'operation': 'export',
            }
        )
        return obj.with_context({
            'woocommerce': woocommerce,
            'channel_id': self,
        }).woocommerce_export_now(record)

#---------------------------------------Update Process -------------------------------------------

    def update_woocommerce(self, record, get_remote_id):
        woocommerce = self._get_woocommerce_connection()
        data_list = []
        if woocommerce:
            remote_id = get_remote_id(record)
            if record._name == 'product.category':
                initial_record_id = record.id
                data_list = self._update_woocommerce_categories(
                    woocommerce, record, initial_record_id, remote_id)
            elif record._name == 'product.template':
                data_list = self._update_woocommerce_product(
                    woocommerce, record, remote_id)
            return data_list

    def _update_woocommerce_categories(self, woocommerce, record, initial_record_id, remote_id):
        obj = self.env['export.categories'].create(
            {
                'channel_id': self.id,
                'operation': 'export',
            }
        )
        return obj.with_context({
            'woocommerce': woocommerce,
            'channel_id': self,
        }).woocommerce_update_now(record, initial_record_id, remote_id)

    def _update_woocommerce_product(self, woocommerce, record, remote_id):
        obj = self.env['export.templates'].create(
            {
                'channel_id': self.id,
                'operation': 'export',
            }
        )
        return obj.with_context({
            'woocommerce': woocommerce,
            'channel_id': self,
        }).woocommerce_update_now(record, remote_id)

#----------------------------------- Core Methods -----------------------------------------------
    def woocommerce_post_do_transfer(self, stock_picking, mapping_ids, result):
        self._woocommerce_set_order_status(order_id=mapping_ids.store_order_id, status='done')

    def woocommerce_post_confirm_paid(self, invoice, mapping_ids, result):
        self._woocommerce_set_order_status(order_id=mapping_ids.store_order_id, status='paid')

    def woocommerce_post_cancel_order(self, sale_order, mapping_ids, result):
        self._woocommerce_set_order_status(order_id=mapping_ids.store_order_id, status='cancelled')

    def _woocommerce_set_order_status(self, order_id, status):
        order_status = self.order_state_ids.filtered(
            lambda order_state_id: order_state_id.odoo_order_state == status
        )
        if order_status:
            self._get_woocommerce_connection().put(f'orders/{order_id}', {'status': order_status[0].channel_state})

    def sync_quantity_woocommerce(self, mapping, qty):
        url = f'products/{mapping.store_product_id}'
        if mapping.store_variant_id != 'No Variants':
            url = f'{url}/variations/{mapping.store_variant_id}'
        res = self._get_woocommerce_connection().put(
            url,
            {"stock_quantity" : int(qty), "manage_stock" : True}
        )
        if not res.ok:
            res = res.json()
            if self.debug == "enable":
                raise UserError(_("Can't update product stock , "+str(res['message'])))
            _logger.info("Error in updating Product Stock: %r", str(res["message"]))

# ---------------------------CRON OPERATIONS ---------------------------------------

    def woocommerce_import_order_cron(self):
        _logger.info("+++++++++++Import Order Cron Started++++++++++++")
        kw = dict(
            object = "sale.order",
            page = 1,
            woocommerce_import_date_from=self.import_order_date,
            from_cron = True
        )
        self.env["import.operation"].create({
            "channel_id":self.id ,
        }).import_with_filter(**kw)

    def woocommerce_import_product_cron(self):
        _logger.info("+++++++++++Import Product Cron Started++++++++++++")
        kw = dict(
            object = "product.template",
            page = 1,
            woocommerce_import_date_from=self.import_product_date,
            from_cron = True
        )
        self.env["import.operation"].create({
            "channel_id":self.id ,
        }).import_with_filter(**kw)

    def woocommerce_import_partner_cron(self):
        _logger.info("+++++++++++Import Partner Cron Started++++++++++++")
        kw = dict(
            object = "res.partner",
            page= 1,
            woocommerce_import_date_from=self.import_customer_date,
            from_cron = True,
        )
        self.env["import.operation"].create({
            "channel_id":self.id ,
        }).import_with_filter(**kw)

    def woocommerce_import_category_cron(self):
        _logger.info("+++++++++++Import Category Cron Started++++++++++++")
        kw = dict(
            object = "product.category",
            page = 1,
            from_cron = True,
        )
        self.env["import.operation"].create({
            "channel_id":self.id ,
        }).import_with_filter(**kw)

#----------------------------------- OAuth Methods -----------------------------------------------
    def _generate_unique_code(self):
        return ''.join(random.choices(string.ascii_letters,k=5))

    def generate_api_keys(self):
        store_url = self.woocommerce_url
        endpoint = '/wc-auth/v1/authorize'
        odoo_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if not odoo_url.startswith('https'):
            odoo_url = odoo_url.replace('http', 'https')
        params = {
            'app_name':'Odoo WooCommerce Connector',
            'scope':'read_write',
            'user_id':self.unique_code,
            'return_url':odoo_url+"/woocommerce_odoo_connector/redirect/"+str(self.id),
            'callback_url':odoo_url+"/woocommerce_odoo_connector/callback/"+str(self.id),
        }
        query_string = urlencode(params)
        url = f'{store_url}{endpoint}?{query_string}'
        try:
            res = requests.get(url)
            if res.ok:
                return {
                    'type': 'ir.actions.act_url',
                    'url':url,
                    'target':'self'
                }
            else:
                msg = 'WooCommerce URL not correct'
        except Exception as e:
            msg = e
        return self.display_message(msg)
