# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################

from odoo import models, api, _

class MultiChannelSale(models.Model):
    _inherit = 'multi.channel.sale'

    @api.model
    def _create_obj(self, obj, vals):
        channel_vals = self.get_channel_vals()
        if self._context.get('obj_type') == 'feed':
            channel_vals.pop('ecom_store')
        vals.update(channel_vals)
        obj_id = obj.create(vals)
        return obj_id

    @api.model
    def _create_mapping(self, mapping_obj, vals):
        return self._create_obj(mapping_obj, vals)

    @api.model
    def _create_feed(self, mapping_obj, vals):
        return self.with_context(obj_type='feed')._create_obj(mapping_obj, vals)

    @api.model
    def create_attribute_mapping(self, erp_id, store_id, store_attribute_name=''):
        self.ensure_one()
        if store_id and store_id not in ['0', -1]:
            vals = dict(
                store_attribute_id=store_id,
                store_attribute_name=store_attribute_name,
                odoo_attribute_id=erp_id.id,
                attribute_name=erp_id.id,
            )
            return self.create_channel_mapping('channel.attribute.mappings', vals)
        return self.env['channel.attribute.mappings']

    @api.model
    def create_attribute_value_mapping(self, erp_id, store_id, store_attribute_value_name=''):
        self.ensure_one()
        if store_id and store_id not in ['0', ' ', -1]:
            vals = dict(
                store_attribute_value_id=store_id,
                store_attribute_value_name=store_attribute_value_name,
                attribute_value_name=erp_id.id,
                odoo_attribute_value_id=erp_id.id,
            )
            return self.create_channel_mapping('channel.attribute.value.mappings', vals)
        return self.env['channel.attribute.value.mappings']

    @api.model
    def create_partner_mapping(self, erp_id, store_id, _type):
        self.ensure_one()
        if store_id and store_id not in ['0', -1]:
            vals = dict(
                store_customer_id=store_id,
                odoo_partner_id=erp_id.id,
                odoo_partner=erp_id.id,
                type=_type,
            )
            return self.create_channel_mapping('channel.partner.mappings', vals)
        return self.env['channel.partner.mappings']

    @api.model
    def create_carrier_mapping(self, name, service_id=None):
        carrier_obj = self.env['delivery.carrier']
        partner_id = self.env.user.company_id.partner_id
        carrier_vals = dict(
            product_id=self.delivery_product_id.id,
            name=name,
            fixed_price=0,
        )
        carrier_id = carrier_obj.sudo().create(carrier_vals)
        service_id = service_id or name
        vals = dict(
            shipping_service=name,
            shipping_service_id=service_id,
            odoo_carrier_id=carrier_id.id,
            odoo_shipping_carrier=carrier_id.id,
        )
        self.create_channel_mapping('channel.shipping.mappings', vals)
        return carrier_id

    @api.model
    def create_template_mapping(self, erp_id, store_id, vals=None):
        self.ensure_one()
        vals = vals or dict()
        vals.update(dict(
            store_product_id=store_id,
            odoo_template_id=erp_id.id,
            template_name=erp_id.id,
            # default_code=vals.get('default_code'),
            # barcode=vals.get('barcode'),
        ))
        return self.create_channel_mapping('channel.template.mappings', vals)

    @api.model
    def create_product_mapping(self, odoo_template_id, odoo_product_id,
                               store_id, store_variant_id, vals=None):
        self.ensure_one()
        vals = dict(vals or dict())
        vals.update(dict(
            store_product_id=store_id,
            store_variant_id=store_variant_id,
            erp_product_id=odoo_product_id.id,
            product_name=odoo_product_id.id,
            odoo_template_id=odoo_template_id.id,
            # default_code=vals.get('default_code'),
            # barcode=vals.get('barcode'),
        ))
        return self.create_channel_mapping('channel.product.mappings', vals)

    @api.model
    def create_category_mapping(self, erp_id, store_id, leaf_category=True):
        self.ensure_one()
        vals = dict(
            store_category_id=store_id,
            odoo_category_id=erp_id.id,
            category_name=erp_id.id,
            leaf_category=leaf_category,
        )
        return self.create_channel_mapping('channel.category.mappings', vals)

    @api.model
    def create_order_mapping(self, erp_id, store_id, store_source=None, store_order_status=None):
        self.ensure_one()
        vals = dict(
            odoo_partner_id=erp_id.partner_id,
            store_order_id=store_id,
            store_id=store_source,
            odoo_order_id=erp_id.id,
            order_name=erp_id.id,
            store_order_status=store_order_status,
        )
        return self.create_channel_mapping('channel.order.mappings', vals)

    def create_channel_mapping(self, model, vals):
        channel_vals = self.get_channel_vals()
        vals.update(channel_vals)
        channel_id=self.env['multi.channel.sale'].browse(channel_vals.get('channel_id'))
        self=self.with_context(channel_id=channel_id)
        return self.env[model].create(vals)
