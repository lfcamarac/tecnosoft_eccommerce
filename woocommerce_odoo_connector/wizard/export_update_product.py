# -*- coding: utf-8 -*-
#################################################################################
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    See LICENSE file for full copyright and licensing details.
##########H#########Y#########P#########N#########O#########S###################
from urllib import parse as urlparse
from itertools import zip_longest
import logging
_logger = logging.getLogger(__name__)
from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import UserError


class UpdateWoocommerceProducts(models.TransientModel):
    _inherit = "export.templates"

    def woocommerce_update_now(self, record, remoteId):
        channel = self._context.get('channel_id')
        woocommerce = self._context.get('woocommerce')
        response = self.with_context({
            'update':True,
            'remoteId':remoteId
        })._woocommerce_export_update_template(
            woocommerce, channel, record)
        return [True, response]

    def _update_woocommerce_variation(self, woocommerce, channel, store_template_id, template, image_ids=False):
        count=0
        updateList, createList, delList, createProductIds, createMessage, updateMessage = [],[],[],[],[],[]
        product_variant_ids = template.product_variant_ids
        ProductMappingIds = self.env["channel.product.mappings"].search([
            ("channel_id", "=", channel.id),
            ("odoo_template_id", "=", template.id)
        ])
        if len(ProductMappingIds) >= len(product_variant_ids):
            inactive_product_mapping_ids = ProductMappingIds.filtered(lambda map:map.product_name not in product_variant_ids)
            delList = inactive_product_mapping_ids.mapped('store_variant_id')
            inactive_product_mapping_ids.unlink()
            ProductMappingIds = ProductMappingIds - inactive_product_mapping_ids
        for variant_id in product_variant_ids: 
            matchRecord = ProductMappingIds.filtered(lambda x: x.product_name == variant_id)
            variantData = {
                'regular_price'	: str(channel.pricelist_name._get_product_price(variant_id, quantity=1)) or "",
                'visible'		: True,
                'sku'			: variant_id.default_code or "",
                'stock_quantity': channel.get_quantity(variant_id),
                'description'	: variant_id.description or "",
                'manage_stock'	: True,
                'in_stock'		: True,
                'attributes'	: self._get_woocommerce_attribute_dict(woocommerce, channel, variant_id),
                'weight': variant_id.weight
            }
            if image_ids:
                variantData.update(
                    {'image': {'id': image_ids[count]}})
            count += 1
            if matchRecord:
                variantData['id'] = matchRecord.store_variant_id
                updateList.append(variantData)
            else:
                createList.append(variantData)
                createProductIds.append(variant_id)
        returnDict = woocommerce.post(f"products/{store_template_id}/variations/batch", {
            'update':updateList,
            'create':createList,
            'delete': delList if delList else []
        }).json()
        for key in zip_longest(returnDict.get('create', []), returnDict.get('update',[]), fillvalue=''):
            if 'message' in key[0]:
                createMessage.append(key[0]['message'])
            if 'error' in key[1]:
                updateMessage.append(key[1]['error']['message'])
        if createMessage or updateMessage:
            raise UserError(f'Error in updating Variants : {",".join(createMessage)} , {",".join(updateMessage)}')
        if createList:
            for createDict, variant_id in zip(returnDict.get("create", []), createProductIds):
                channel.create_product_mapping(template, variant_id,
                    store_template_id, createDict.get("id"),vals = dict(default_code=variant_id.default_code,barcode = variant_id.barcode,operation='export'))
        return [updateDict.get("id") for updateDict in returnDict.get("update", [])]
