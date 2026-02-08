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
    def _match_feed(self, mapping_obj, domain, limit=None):
        return self._match_obj(mapping_obj, domain, limit)

    @api.model
    def _match_obj(self, obj, domain=None, limit=None):
        channel_domain = self.get_channel_domain(domain)
        new_domain = channel_domain
        if limit:
            return obj.search(new_domain, limit=limit)
        return obj.search(new_domain)

    @api.model
    def _match_mapping(self, mapping_obj, domain, limit=None):
        return self._match_obj(mapping_obj, domain, limit)

    @api.model
    def get_channel_domain(self, pre_domain=None):
        domain = []
        if type(self.id) == int:
            domain += [('channel_id', '=', self.id)]
        if pre_domain:
            domain += pre_domain
        return domain

    @api.model
    def match_create_pricelist_id(self, currency_id):
        map_obj = self.env['channel.pricelist.mappings']
        channel_domain = self.get_channel_domain()
        domain = [
            ('store_currency_code', '=', currency_id.name),
        ]
        match = self._match_mapping(map_obj, domain)
        if match:
            return match.odoo_pricelist_id
        else:
            pricelist_id = self.env['product.pricelist'].create(
                dict(
                    currency_id=currency_id.id,
                    name=self.name
                )
            )
            vals = dict(
                store_currency=currency_id.id,
                store_currency_code=currency_id.name,
                odoo_pricelist_id=pricelist_id.id,
                odoo_currency_id=currency_id.id,
            )
            return self._create_mapping(map_obj, vals).odoo_pricelist_id

    @api.model
    def match_attribute_mappings(self, store_attribute_id=None,
                                 odoo_attribute_id=None, domain=None, limit=1):

        map_domain = self.get_channel_domain(domain)

        if store_attribute_id:
            map_domain += [('store_attribute_id', '=', store_attribute_id)]
        if odoo_attribute_id:
            map_domain += [('odoo_attribute_id', '=', odoo_attribute_id)]

        return self.env['channel.attribute.mappings'].search(map_domain, limit=limit)

    @api.model
    def match_attribute_value_mappings(self, store_attribute_value_id=None,
                                       attribute_value_id=None, domain=None, limit=1):

        map_domain = self.get_channel_domain(domain)
        if store_attribute_value_id:
            map_domain += [('store_attribute_value_id', '=', store_attribute_value_id)]
        if attribute_value_id:
            map_domain += [('odoo_attribute_value_id', '=', attribute_value_id)]
        return self.env['channel.attribute.value.mappings'].search(map_domain, limit=limit)

    @api.model
    def match_product_mappings(self, store_product_id=None, line_variant_ids=None,
                               domain=None, limit=1, **kwargs):
        map_domain = self.get_channel_domain(domain)
        if store_product_id:
            map_domain += [('store_product_id', '=', store_product_id), ]
        if line_variant_ids:
            map_domain += [('store_variant_id', '=', line_variant_ids)]
        if kwargs.get('default_code'):
            map_domain += [('default_code', '=', kwargs.get('default_code'))]
        if kwargs.get('barcode'):
            map_domain += [('barcode', '=', kwargs.get('barcode'))]
        return self.env['channel.product.mappings'].search(map_domain, limit=limit)

    @api.model
    def match_template_mappings(self, store_product_id=None, domain=None, limit=1, **kwargs):
        map_domain = self.get_channel_domain(domain)
        if store_product_id:
            map_domain += [('store_product_id', '=', store_product_id)]
        if kwargs.get('default_code'):
            map_domain += [('default_code', '=', kwargs.get('default_code'))]
        if kwargs.get('barcode'):
            map_domain += [('barcode', '=', kwargs.get('barcode'))]
        return self.env['channel.template.mappings'].search(map_domain, limit=limit)

    @api.model
    def match_partner_mappings(self, store_id=None, _type='contact', domain=None, limit=1):
        map_domain = self.get_channel_domain(domain) + [('type', '=', _type)]
        if store_id:
            map_domain += [('store_customer_id', '=', store_id)]
        return self.env['channel.partner.mappings'].search(map_domain, limit=limit)

    @api.model
    def match_order_mappings(self, store_order_id=None, domain=None, limit=1):
        map_domain = self.get_channel_domain(domain)
        if store_order_id:
            map_domain += [('store_order_id', '=', store_order_id)]
        return self.env['channel.order.mappings'].search(map_domain, limit=limit)

    @api.model
    def match_carrier_mappings(self, shipping_service_name=None, domain=None, limit=1):
        map_domain = self.get_channel_domain(domain)
        if shipping_service_name:
            map_domain += [('shipping_service', '=', shipping_service_name)]
        return self.env['channel.shipping.mappings'].search(map_domain, limit=limit)

    @api.model
    def match_category_mappings(self, store_category_id=None, odoo_category_id=None, domain=None, limit=1):
        map_domain = self.get_channel_domain(domain)
        if store_category_id:
            map_domain += [('store_category_id', '=', store_category_id)]
        if odoo_category_id:
            map_domain += [('odoo_category_id', '=', odoo_category_id)]
        return self.env['channel.category.mappings'].search(map_domain, limit=limit)

    @api.model
    def match_category_feeds(self, store_id=None, domain=None, limit=1):
        map_domain = self.get_channel_domain(domain)
        if store_id:
            map_domain += [('store_id', '=', store_id)]
        return self.env['category.feed'].search(map_domain, limit=limit)

    @api.model
    def match_product_feeds(self, store_id=None, domain=None, limit=1):
        map_domain = self.get_channel_domain(domain)
        if store_id:
            map_domain += [('store_id', '=', store_id)]

        return self.env['product.feed'].search(map_domain, limit=limit)

    @api.model
    def match_product_variant_feeds(self, store_id=None, domain=None, limit=1):
        map_domain = self.get_channel_domain(domain)
        if store_id:
            map_domain += [('store_id', '=', store_id)]
        map_domain += [('feed_templ_id', '!=', False)]
        return self.env['product.variant.feed'].search(map_domain, limit=limit)

    @api.model
    def match_partner_feeds(self, store_id=None, _type='contact', domain=None, limit=1):
        map_domain = self.get_channel_domain(domain) + [('type', '=', _type)]
        if store_id:
            map_domain += [('store_id', '=', store_id)]
        return self.env['partner.feed'].search(map_domain, limit=limit)

    @api.model
    def match_order_feeds(self, store_id=None, domain=None, limit=1):
        map_domain = self.get_channel_domain(domain)
        if store_id:
            map_domain += [('store_id', '=', store_id)]

        return self.env['order.feed'].search(map_domain, limit=limit)

    @api.model
    def match_odoo_template(self, vals, variant_lines):
        Template = self.env['product.template']
        record = self.env['product.template']
        # Ensure barcode constraints first
        barcode = vals.get('barcode')
        if barcode:
            record = Template.search([('barcode', '=', barcode)], limit=1)
        if not record:
            # Now check avoid_duplicity using default_code
            ir_values = self.default_multi_channel_values()
            default_code = vals.get('default_code')
            #  and (not len(variant_lines))
            if ir_values.get('avoid_duplicity') and default_code:
                record = Template.search([('default_code', '=', default_code)], limit=1)
            if not record:
                # It's time to check the child
                if variant_lines:
                    barcode_list = variant_lines.filtered(lambda x: x.barcode ).mapped('barcode')
                    if barcode_list:
                        record = self.env['product.product'].search([('barcode', 'in', barcode_list)], limit=1)
                        if record:
                            return record.product_tmpl_id
                if ir_values.get('avoid_duplicity') and variant_lines:
                    default_code_list = variant_lines.filtered(lambda x: x.default_code).mapped('default_code')
                    if default_code_list:
                        record = self.env['product.product'].search([('default_code', 'in', default_code_list)], limit=1)
                        if record:
                            return record.product_tmpl_id
                for var in variant_lines:
                    match = self.match_odoo_product(var.read([])[0])
                    if match:
                        record = match.product_tmpl_id
                        break
        return record

    @api.model
    def match_odoo_product(self, vals, obj='product.product'):
        oe_env = self.env[obj]
        record = False
        # check avoid_duplicity using default_code
        barcode = vals.get('barcode')
        if barcode:
            record = oe_env.search([('barcode', '=', barcode)], limit=1)
        if not record:
            default_code = vals.get('default_code')
            ir_values = self.default_multi_channel_values()
            if ir_values.get('avoid_duplicity') and default_code:
                record = oe_env.search([('default_code', '=', default_code)], limit=1)
            if not record:
                if 'product_template_attribute_value_ids' in vals and 'product_tmpl_id' in vals:
                    _ids = vals['product_template_attribute_value_ids'][0][2]
                    ids = ','.join([str(i) for i in sorted(_ids)])
                    domain = [('product_tmpl_id', '=', vals['product_tmpl_id'])]
                    if ids:
                        domain += [('product_template_attribute_value_ids', 'in', _ids)]
                    record = oe_env.search(domain) \
                        .filtered(lambda prod: prod.product_template_attribute_value_ids._ids2str() == ids)
        return record

    @api.model
    def _match_create_product_categ(self, vals):
        match = self.match_category_feeds(store_id=vals.get('store_id'))
        feed_obj = self.env['category.feed']
        update = False
        if match:
            vals['state'] = 'update'
            vals.pop('store_id', '')
            update = match.write(vals)
            data = match
        else:
            data = self._create_feed(feed_obj, vals)
        return dict(
            data=data,
            update=update
        )
