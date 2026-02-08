# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    See LICENSE file for full copyright and licensing details.
##########H#########Y#########P#########N#########O#########S###################

from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError
from odoo import api, fields, models
from odoo.tools.translate import _

class ImportWoocommerceCategories(models.TransientModel):
    _name = "import.woocommerce.categories"
    _inherit = 'import.categories'
    _description = "Import Woocommerce Categories"

    def get_category_all(self, woocommerce, **kwargs):
        params={
                'page': kwargs.get('page'),
                'per_page': kwargs.get('page_size'),
                'order': 'asc'
            }
        if self._context.get('ids_res'):
            params.update({'include':  kwargs.get('woocommerce_object_id')})
        category_data = woocommerce.get(
            'products/categories',
            params=params
        ).json()
        if "message" in category_data:
            raise UserError(f'Error in getting Category data : {category_data["message"]}')
        return list(map(lambda x: self._get_category_vals(x),category_data))

    def _get_category_by_id(self, woocommerce, category_id):
        vals_list = []
        parent_data  = None
        category_data = woocommerce.get(f'products/categories/{category_id}').json()
        if "message" in category_data:
            raise UserError(f'Error in getting Category Data : {category_data["message"]}')
        parent_id = category_data.get("parent")
        if parent_id:
            parent_data = self._get_category_by_id(woocommerce, parent_id)
            vals_list += parent_data
        data = self._get_category_vals(category_data)
        vals_list.append(data)
        return vals_list

    def _get_category_vals(self, category_data):
        return {
                    "channel_id"   : self.channel_id.id,
                    "channel"      : self.channel_id.channel,
                    "leaf_category": True if category_data.get("parent") else False,
                    "parent_id"    : category_data.get("parent") or "",
                    "store_id"     : category_data.get("id"),
                    "name"         : category_data.get("name"),
                }

    def import_now(self,**kwargs):
        woocommerce = self._context.get('woocommerce')
        category_id = kwargs.get('woocommerce_object_id')
        if category_id:
            ids_res = str(category_id).split(',')
            ids_len = len(ids_res)
            if 1<ids_len<=100:
                data_list = self.with_context(ids_res=True).get_category_all(woocommerce, **kwargs)
            elif ids_len>100:
                raise UserError('Number of ids must be less than or equal to 100')
            else:
                data_list = self._get_category_by_id(woocommerce, category_id)
        else:
            data_list = self.get_category_all(woocommerce, **kwargs)
        return data_list
