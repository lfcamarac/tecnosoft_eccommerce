# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    See LICENSE file for full copyright and licensing details.
##########H#########Y#########P#########N#########O#########S###################
import logging
_logger = logging.getLogger(__name__)
from odoo import api, fields, models
from odoo.exceptions import UserError


class UpdateWoocommerceCategories(models.TransientModel):
    _inherit = "export.categories"

    def woocommerce_update_now(self, record, initial_record_id, remoteid):
        return_list = [False, '']
        channel = self._context.get('channel_id')
        woocommerce = self._context.get('woocommerce')
        response = self._woocommerce_sync_categories_update(
            channel, woocommerce, record, initial_record_id, remoteid)
        if response:
            return_list = [True, {"id" : response}]
        return return_list

    def _woocommerce_sync_categories_update(self, channel, woocommerce, record, initial_record_id, remote_id, ):
        p_cat_id = 0
        if record.parent_id.id:
            is_parent_mapped = self.env['channel.category.mappings'].search([
                ("channel_id", '=', channel.id),
                ('odoo_category_id', '=', record.parent_id.id)])
            if is_parent_mapped:
                p_cat_id = self.with_context({
                    'channel_id': channel,
                    'woocommerce': woocommerce,
                }).woocommerce_update_now(record.parent_id, initial_record_id, is_parent_mapped.store_category_id)
            else:
                p_cat_id = self.env['export.categories'].create({
                    "channel_id": channel.id,
                    "operation": "export"
                }).with_context({
                    'channel_id': channel,
                    'woocommerce': woocommerce,
                }).woocommerce_export_now(record.parent_id, initial_record_id)
            if isinstance(p_cat_id, list):
                p_cat_id = p_cat_id[1].get("id")
        return self._woocommerce_update_category(
            woocommerce, channel, record, initial_record_id, p_cat_id, remote_id)

    def _woocommerce_update_category(self, woocommerce, channel, record, initial_record_id, p_cat_id, remote_id):
        return_dict = woocommerce.put(
            'products/categories/%s' % remote_id,
            {
                'name': record.name,
                'parent': p_cat_id,
            }
        ).json()
        if 'message' in return_dict:
            raise UserError(f"Error in Updating Categories : {return_dict['message']}")
        return return_dict.get("id") 
