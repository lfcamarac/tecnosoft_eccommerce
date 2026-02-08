# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################

from odoo import models, api, _, fields
from io import BytesIO
import codecs
from PIL import Image
from ...tools import DomainVals
from logging import getLogger
_logger = getLogger(__name__)

class MultiChannelSale(models.Model):
    _inherit = 'multi.channel.sale'

    @api.model
    def get_quantity(self, obj_pro):
        """
            to get quantity of product or product template
            @params : product template obj or product obj
            @return : quantity in hand or quantity forecasted
        """
        quantity = 0.0
        ctx = self._context.copy() or {}
        if 'location' not in ctx:
            ctx.update({
                'location': self.location_id.id
            })
        product = obj_pro.with_context(ctx)
        quantity = product.qty_available if self.channel_stock_action == 'qoh' else product.free_qty if self.channel_stock_action == 'free_qty' else product.virtual_available
        quantity = quantity.split('.')[0] if type(quantity) == str else quantity.as_integer_ratio()[0] if type(quantity) == float else quantity
        return quantity

    def get_core_feature_compatible_channels(self):
        '''
            Channels supporting core features such as import/export
            operation wizard to be appended by bridges.

            Returns:
                list -- names of channels
        '''
        return []

    @api.model
    def get_channel(self):
        if self._context.get('test_channel'):
            return [('ecommerce', 'Ecommerce')]
        channel_list = []
        return channel_list

    @api.model
    def get_info_urls(self):
        return {}

    @api.model
    def get_data_isoformat(self, date_time):
        try:
            return date_time and fields.Datetime.from_string(date_time).isoformat()
        except Exception as e:
            _logger.exception("==%r=" % (e))

    @api.model
    def get_state_id(self, state_code, country_id, state_name=None):
        if (not state_code) and state_name:
            state_code = state_name[:2]
        state_name = state_name or ''
        domain = [
            ('code', '=', state_code),
            ('name', '=', state_name),
            ('country_id', '=', country_id.id)
        ]
        state_id = country_id.state_ids.filtered(
            lambda st: (st.code in [state_code, state_name[:3], state_name]) or (st.name == state_name)
        )
        if not state_id:
            vals = DomainVals(domain)
            vals['name'] = state_name and state_name or state_code
            if (not vals['code']) and state_name:
                vals['code'] = state_name[:2]
            state_id = self.env['res.country.state'].create(vals)
        else:
            state_id = state_id[0]
        return state_id

    @api.model
    def get_country_id(self, country_code):
        domain = [
            ('code', '=', country_code),
        ]
        return self.env['res.country'].search(domain, limit=1)

    @api.model
    def get_currency_id(self, name):
        domain = [
            ('name', '=', name),
        ]
        return self.env['res.currency'].with_context(active_test = False).search(domain, limit=1)

    @api.model
    def get_uom_id(self, name):
        domain = [
            ('name', '=', name),
        ]
        return self.env['uom.uom'].search(domain)

    @api.model
    def get_store_attribute_id(self, name, create_obj=False):
        domain = [
            ('name', '=', name),
        ]
        match = self.env['product.attribute'].search(domain)
        if (not match) and create_obj:
            match = self.env['product.attribute'].create(DomainVals(domain))
        return match

    @api.model
    def get_store_attribute_value_id(self, name, attribute_id, create_obj=False):
        domain = [
            ('name', '=', name),
            ('attribute_id', '=', attribute_id),
        ]
        match = self.env['product.attribute.value'].search(domain)
        if (not match) and create_obj:
            match = self.env['product.attribute.value'].create(DomainVals(domain))
        return match

    @api.model
    def get_channel_vals(self):
        return dict(
            channel_id=self.id,
            ecom_store=self.channel
        )

    @api.model
    def get_channel_category_id(self, template_id, channel_id, limit=1):
        mapping_obj = self.env['channel.category.mappings']
        channel_category_ids = (template_id.channel_category_ids or template_id.categ_id.channel_category_ids)
        channel_categ = channel_category_ids.filtered(
            lambda cat: cat.instance_id == channel_id
        )
        extra_category_ids = channel_categ.mapped('extra_category_ids')
        domain = [('odoo_category_id', 'in', extra_category_ids.ids)] if extra_category_ids else []
        return channel_id.match_category_mappings(domain=domain, limit=limit).mapped('store_category_id')

    @staticmethod
    def get_image_type(image_data):
        image_stream = BytesIO(codecs.decode(image_data, 'base64'))
        image = Image.open(image_stream)
        image_type = image.format.lower()
        if not image_type:
            image_type = 'jpg'
        return image_type

    # @api.model
    # def get_channel(self):
    #     return self.fields_get(allfields=['channel'])['channel']['selection']
