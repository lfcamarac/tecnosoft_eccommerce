# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################

from odoo import api, fields, models
from odoo.addons.odoo_multi_channel_sale.tools import extract_list as EL
import copy


CategoryFields = [
    'name',
    'store_id',

    'parent_id',
    'description'
]

ProductFields = [
    'name',
    'store_id',

    'extra_categ_ids',
    'list_price',
    'image_url',
    'image',
    'default_code',
    'barcode',
    'type',
    'is_storable',
    'wk_product_id_type',
    'description_sale',
    'description_purchase',
    'standard_price',
    'sale_delay',
    'qty_available',
    'weight',
    'feed_variants',
    'weight_unit',
    'length',
    'width',
    'height',
    'dimensions_unit',
    'hs_code',
    'wk_default_code',
]


class WkFeed(models.Model):
    _name = 'wk.feed'
    _description = 'Feed'

    name = fields.Char('Name')
    sequence = fields.Char('Sequence')
    store_id = fields.Char('Store ID')
    store_source = fields.Char('Store Source')
    message = fields.Html('Message', default='', copy=False)
    active = fields.Boolean('Active', default=True)

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('update', 'Update'),
            ('done', 'Done'),
            ('cancel', 'Cancel'),
            ('error', 'Error'),
        ],
        string='State',
        default='draft',
        copy=False,
    )
    channel_id = fields.Many2one(
        comodel_name='multi.channel.sale',
        string='Instance',
        domain=[('state', '=', 'validate')]
    )
    channel = fields.Selection(
        related='channel_id.channel',
        string='Channel',
    )

    def write(self, vals):
        if vals.get('message'):
            message = f"<br/><span class='text-info'>{fields.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span> {vals.get('message')}"
            vals.update({'message': message})
        return super().write(vals)

    @api.model
    def _create_feeds(self, data_list):
        success_ids, error_ids = [], []
        self = self.contextualize_feeds(self._name.split('.')[0])
        for data in data_list:
            feed = self._create_feed(data)
            if feed:
                self += feed
                success_ids.append(data.get('store_id'))
            else:
                error_ids.append(data.get('store_id'))
        return success_ids, error_ids, self

    @api.model
    def get_product_fields(self):
        return copy.deepcopy(ProductFields)

    @api.model
    def get_category_fields(self):
        return copy.deepcopy(CategoryFields)

    def open_mapping_view(self):
        self.ensure_one()
        model = self._context.get('mapping_model')
        action = {
            'name': 'Mapping',
            'type': 'ir.actions.act_window',
            'res_model': model,
            'target': 'current',
        }

        res = self.env[model].search(
            [
                ('channel_id', '=', self.channel_id.id),
                (self._context.get('store_field'), '=', self.store_id),
            ]
        )
        action.update(view_mode='form', res_id=res.id) if len(res) == 1 else action.update(view_mode='list,form', domain=[('id', 'in', res.ids)])
        return action

    def set_feed_state(self, state='done'):
        self.state = state
        return True

    def get_feed_result(self, feed_type):
        message = ""
        tot = len(self)
        if tot == 1:
            if self.state == 'done':
                message += "{_type} feed sucessfully evaluated .".format(
                    _type=feed_type
                )
            else:
                message += "{_type} feed failed to evaluate .".format(
                    _type=feed_type
                )
        else:
            done_feeds = self.filtered(lambda feed: feed.state == 'done')
            error_feed = tot - len(done_feeds)
            if not error_feed:
                message += "All ({done}) {_type} feed sucessfully evaluated .".format(
                    done=len(done_feeds), _type=feed_type
                )
            else:
                message += "<br/>{error} {_type} feed failed to evaluate".format(
                    error=error_feed, _type=feed_type
                )
                if len(done_feeds):
                    message += "<br/>{done} {_type} feed sucessfully evaluated".format(
                        done=len(done_feeds), _type=feed_type
                    )
        return message

    @api.model
    def get_channel_domain(self):
        return [('channel_id', '=', self.channel_id.id)]

    @api.model
    def get_categ_id(self, store_categ_id, channel_id):
        message = ''
        categ_id = None
        context = self._context.copy() or {}
        match = self._context.get('category_mappings').get(channel_id.id, {}).get(store_categ_id)
        if match:
            match = self.env['channel.category.mappings'].browse(match)
            categ_id = match.odoo_category_id
        else:
            match = self._context.get('category_feeds').get(channel_id.id, {}).get(store_categ_id)
            if match:
                feed = self.env['category.feed'].browse(match)
                res = feed.with_context(**context).import_category(channel_id)
                message += res.get('message', '')
                mapping_id = res.get('update_id') or res.get('create_id')
                if mapping_id:
                    categ_id = mapping_id.odoo_category_id
                    context.get('category_mappings', {}).setdefault(channel_id.id, {})[
                        mapping_id.store_category_id] = mapping_id.id
            else:
                message += '<br/>Category Feed Error: No mapping as well category feed found for %s .' % (
                    store_categ_id)
        return dict(
            categ_id=categ_id,
            message=message
        )

    @api.model
    def get_extra_categ_ids(self, store_categ_ids, channel_id):
        message = ''
        categ_ids = []
        for store_categ_id in store_categ_ids.strip(',').split(','):
            res = self.get_categ_id(store_categ_id, channel_id)
            message += res.get('message', '')
            categ_id = res.get('categ_id')
            if categ_id:
                categ_ids += [categ_id]
        return dict(
            categ_ids=categ_ids,
            message=message
        )

    @api.model
    def get_order_partner_id(self, store_partner_id, channel_id):
        partner_obj = self.env['res.partner']
        message = ''
        partner_id = None
        partner_invoice_id = None
        partner_shipping_id = None
        context = dict(self._context)
        context['no_mapping'] = self.customer_is_guest
        try:
            partner_id = self.with_context(context).create_partner_contact_id(
                partner_id, channel_id, store_partner_id)
            partner_invoice_id = self.with_context(context).create_partner_invoice_id(
                partner_id, channel_id, self.invoice_partner_id)
            if self.same_shipping_billing:
                partner_shipping_id = partner_invoice_id
            else:
                partner_shipping_id = self.with_context(context).create_partner_shipping_id(
                    partner_id, channel_id, self.shipping_partner_id)
        except Exception as e:
            message += e.args[0]
        return dict(
            partner_id=partner_id,
            partner_shipping_id=partner_shipping_id,
            partner_invoice_id=partner_invoice_id,
            message=message
        )

    @api.model
    def get_partner_id(self, store_partner_id, _type='contact', channel_id=None):
        partner_obj = self.env['res.partner']
        message = ''
        partner_id = None
        match = channel_id.match_partner_mappings(store_partner_id, _type)
        if match:
            partner_id = match.odoo_partner
        else:
            feed = channel_id.match_partner_feeds(store_partner_id, _type)
            if feed:
                res = feed.import_partner(channel_id)
                message += res.get('message', '')
                mapping_id = res.get('update_id') or res.get('create_id')
                if mapping_id:
                    partner_id = mapping_id.odoo_partner
            else:
                message += '<br/>Partner Feed Error: No mapping as well partner feed found for %s.' % (
                    store_partner_id)

        return dict(
            partner_id=partner_id,
            message=message
        )

    @api.model
    def get_product_id(self, store_product_id, line_variant_ids, channel_id, default_code=None, barcode=None):
        message = ''

        # Need to check significance of domain

        # domain = []
        # if default_code:
        #     domain += [('default_code','=',default_code)]
        # if barcode:
        #     domain += [('barcode','=',barcode)]
        product_id = None
        match = self._context.get('variant_mappings').get(channel_id.id, {}).get(store_product_id, {}).get(line_variant_ids)
        if match:
            match = self.env['channel.product.mappings'].browse(match)
            product_id = match.product_name
        else:
            feed = self._context.get('product_feeds').get(channel_id.id, {}).get(store_product_id)
            feed = self.env['product.feed'].browse(feed)
            product_variant_feed = feed.feed_variants.filtered(lambda self: self.store_id == line_variant_ids)
            if feed:
                res = feed.import_product(channel_id)
                mapping_id = res.get('update_id') or res.get('create_id')
                self = self.contextualize_mappings('product', channel_id.ids)
                match = self._context.get('variant_mappings').get(channel_id.id, {}).get(store_product_id, {}).get(line_variant_ids)
                if match:
                    match = self.env['channel.product.mappings'].browse(match)
                    product_id = match.product_name
                else:
                    message += '<br/>Product Feed Error: For product id (%s) & variant id (%s) no mapping as well feed found.' % (store_product_id, line_variant_ids)
            elif product_variant_feed and product_variant_feed.feed_templ_id:
                res = product_variant_feed.feed_templ_id.import_product(channel_id)
                message += res.get('message', '')
                match = channel_id.match_product_mappings(
                    line_variant_ids=store_product_id)
                if match:
                    product_id = match.product_name
            else:
                message += '<br/>Product Feed Error: For product id (%s) sku (%s) no mapping as well feed found.' % (
                    store_product_id, default_code)
        return dict(
            product_id=product_id,
            message=message
        )

    @api.model
    def get_carrier_id(self, carrier_id, service_id=None, channel_id=None):
        message = ''
        res_id = None
        shipping_service_name = service_id or carrier_id
        match = channel_id.match_carrier_mappings(shipping_service_name)
        if match:
            res_id = match.odoo_shipping_carrier
        else:
            res_id = channel_id.create_carrier_mapping(
                carrier_id, service_id)
        return dict(
            carrier_id=res_id,
            message=message
        )

    def get_partner_invoice_vals(self, partner_id, channel_id):
        name = self.invoice_name
        if self.invoice_last_name:
            name = '%s %s' % (name, self.invoice_last_name)
        vals = dict(
            type='invoice',
            name=name,
            street=self.invoice_street,
            street2=self.invoice_street2,
            city=self.invoice_city,
            zip=self.invoice_zip,
            email=self.invoice_email,
            phone=self.invoice_phone,
            mobile=self.invoice_mobile,
            parent_id=partner_id.id,
        )
        country_id = self.invoice_country_id and channel_id.get_country_id(
            self.invoice_country_id)
        if country_id:
            vals['country_id'] = country_id.id
        state_id = (self.invoice_state_id or self.invoice_state_name) and country_id and channel_id.get_state_id(
            self.invoice_state_id, country_id, self.invoice_state_name
        )
        if state_id:
            vals['state_id'] = state_id.id
        return vals

    @api.model
    def create_partner_invoice_id(self, partner_id, channel_id, invoice_partner_id=None):
        partner_obj = self.env['res.partner']
        vals = self.get_partner_invoice_vals(partner_id, channel_id)
        match = None
        if invoice_partner_id:
            match = channel_id.match_partner_mappings(
                invoice_partner_id, 'invoice')
        if match:
            match.odoo_partner.write(vals)
            erp_id = match.odoo_partner
        else:
            erp_id = partner_obj.create(vals)
            if (not self._context.get('no_mapping') and invoice_partner_id):
                channel_id.create_partner_mapping(erp_id, invoice_partner_id, 'invoice')
        return erp_id

    def get_partner_shipping_vals(self, partner_id, channel_id):

        name = self.shipping_name
        if self.shipping_last_name:
            name = '%s %s' % (name, self.shipping_last_name)
        vals = dict(
            type='delivery',
            name=name,
            street=self.shipping_street,
            street2=self.shipping_street2,
            city=self.shipping_city,
            zip=self.shipping_zip,
            email=self.shipping_email,
            phone=self.shipping_phone,
            mobile=self.shipping_mobile,
            parent_id=partner_id.id,
        )
        country_id = self.shipping_country_id and channel_id.get_country_id(
            self.shipping_country_id)
        if country_id:
            vals['country_id'] = country_id.id
        state_id = (self.shipping_state_id or self.shipping_state_name) and country_id and channel_id.get_state_id(
            self.shipping_state_id, country_id, self.shipping_state_name
        )
        if state_id:
            vals['state_id'] = state_id.id
        return vals

    @api.model
    def create_partner_shipping_id(self, partner_id, channel_id, shipping_partner_id=None):
        partner_obj = self.env['res.partner']
        match = None
        vals = self.get_partner_shipping_vals(partner_id, channel_id)
        if shipping_partner_id:
            match = channel_id.match_partner_mappings(
                shipping_partner_id, 'delivery')
        if match:
            match.odoo_partner.write(vals)
            erp_id = match.odoo_partner
        else:
            erp_id = partner_obj.create(vals)
            if (not self._context.get('no_mapping') and shipping_partner_id):
                channel_id.create_partner_mapping(erp_id, shipping_partner_id, 'delivery')
        return erp_id

    def get_partner_contact_vals(self, partner_id, channel_id):
        _type = 'contact'
        name = self.customer_name
        if self.customer_last_name:
            name = '%s %s' % (name, self.customer_last_name)
        vals = dict(
            type=_type,
            name=name,
            email=self.customer_email,
            phone=self.customer_phone,
            mobile=self.customer_mobile,
            vat=self.customer_vat,
        )
        if channel_id.sync_customer_company:
            vals['company_name'] = self.customer_company
        if not self.customer_vat:
            vals.pop("vat")
        return vals

    @api.model
    def create_partner_contact_id(self, partner_id, channel_id, store_partner_id=None):
        partner_obj = self.env['res.partner']
        vals = self.get_partner_contact_vals(partner_id, channel_id)
        match = None
        if store_partner_id:
            match = channel_id.match_partner_mappings(
                store_partner_id, 'contact')
        if match:
            vals.pop('company_name', False)
            match.odoo_partner.write(vals)
            erp_id = match.odoo_partner
        else:
            erp_id = partner_obj.create(vals)
            if not self._context.get('no_mapping') and store_partner_id:
                channel_id.create_partner_mapping(erp_id, store_partner_id, 'contact')
        return erp_id

    def contextualize_feeds(self, type, channel_ids=False):
        if not channel_ids and 'channel_id' in self._context:
            channel_ids = self._context.get('channel_id').ids
        if not channel_ids:
            raise Exception('No channel_ids available to contextualize feeds.')
        if type == 'category':
            feeds = {}
            for rec in self.env['category.feed'].search_read(
                [('channel_id', 'in', channel_ids)],
                ['id', 'store_id', 'channel_id'],
            ):
                feeds.setdefault(rec.get('channel_id')[0], {})[rec.get('store_id')] = rec.get('id')
            return self.with_context(category_feeds=feeds)
        elif type == 'product':
            product_feeds = {}
            for rec in self.env['product.feed'].search_read(
                [('channel_id', 'in', channel_ids)],
                ['id', 'store_id', 'channel_id'],
            ):
                product_feeds.setdefault(rec.get('channel_id')[0], {})[rec.get('store_id')] = rec.get('id')
            return self.with_context(product_feeds=product_feeds)
        elif type == 'partner':
            contact_feeds, address_feeds = {}, {}
            for rec in self.env['partner.feed'].search_read(
                [('channel_id', 'in', channel_ids)],
                ['id', 'store_id', 'channel_id', 'type'],
            ):
                if rec.get('type') == "contact":
                    contact_feeds.setdefault(rec.get('channel_id')[0], {})[rec.get('store_id')] = rec.get('id')
                else:
                    address_feeds.setdefault(rec.get('channel_id')[0], {})[rec.get('store_id')] = rec.get('id')
            return self.with_context(partner_feeds=contact_feeds, address_feeds=address_feeds)
        elif type == 'order':
            feeds = {}
            for rec in self.env['order.feed'].search_read(
                [('channel_id', 'in', channel_ids)],
                ['id', 'store_id', 'channel_id'],
            ):
                feeds.setdefault(rec.get('channel_id')[0], {})[rec.get('store_id')] = rec.get('id')
            return self.with_context(order_feeds=feeds)
        elif type == 'shipping':
            feeds = {}
            for rec in self.env['shipping.feed'].search_read(
                    [('channel_id', 'in', channel_ids)],
                    ['id', 'store_id', 'channel_id'],
            ):
                feeds.setdefault(rec.get('channel_id')[0], {})[
                    rec.get('store_id')] = rec.get('id')
            return self.with_context(shipping_feeds=feeds)
        else:
            raise Exception('Wrong type for feeds to be contextualized.')

    def contextualize_mappings(self, type, channel_ids=False):
        if not channel_ids and 'channel_id' in self._context:
            channel_ids = self._context.get('channel_id').ids
        if not channel_ids:
            raise Exception('No channel_ids available to contextualize mappings.')
        if type == 'category':
            mappings = {}
            for rec in self.env['channel.category.mappings'].search_read(
                [('channel_id', 'in', channel_ids)],
                ['id', 'store_category_id', 'channel_id'],
            ):
                mappings.setdefault(rec.get('channel_id')[0], {})[rec.get('store_category_id')] = rec.get('id')
            return self.with_context(category_mappings=mappings)
        elif type == 'product':
            product_mappings, variant_mappings = {}, {}
            for rec in self.env['channel.template.mappings'].search_read(
                [('channel_id', 'in', channel_ids)],
                ['id', 'store_product_id', 'channel_id'],
            ):
                product_mappings.setdefault(rec.get('channel_id')[0], {})[rec.get('store_product_id')] = rec.get('id')
            for rec in self.env['channel.product.mappings'].search_read(
                [('channel_id', 'in', channel_ids)],
                ['id', 'store_product_id', 'store_variant_id', 'channel_id'],
            ):
                variant_mappings.setdefault(
                    rec.get('channel_id')[0], {}
                ).setdefault(
                    rec.get('store_product_id'), {}
                )[rec.get('store_variant_id')] = rec.get('id')
            return self.with_context(product_mappings=product_mappings, variant_mappings=variant_mappings)
        elif type == 'partner':
            mappings = {}
            for rec in self.env['channel.partner.mappings'].search_read(
                [('channel_id', 'in', channel_ids)],
                ['id', 'store_customer_id', 'channel_id'],
            ):
                mappings.setdefault(rec.get('channel_id')[0], {})[rec.get('store_customer_id')] = rec.get('id')
            return self.with_context(partner_mappings=mappings)
        elif type == 'order':
            mappings = {}
            for rec in self.env['channel.order.mappings'].search_read(
                [('channel_id', 'in', channel_ids)],
                ['id', 'store_order_id', 'channel_id'],
            ):
                mappings.setdefault(rec.get('channel_id')[0], {})[rec.get('store_order_id')] = rec.get('id')
            return self.with_context(order_mappings=mappings)
        else:
            raise Exception('Wrong type for mappings to be contextualized.')

    def get_required_feed_fields(self):
        required_fields = {
            'products': ['type', 'store_id', 'name', 'channel_id'],
            'product_variant': ['name_value'],
            'customers': ['store_id', 'name', 'channel_id'],
            'orders': ['store_id', 'partner_id', 'customer_name', 'customer_email', 'channel_id', 'line_type', 'invoice_partner_id'],
            'order_lines': ['line_source', 'line_name', 'line_product_uom_qty'],
            'categories': ['name', 'store_id', 'channel_id'],
            'shipping': ['shipping_carrier', 'store_id', 'channel_id'],
        }
        return required_fields

    def required_field_not_filled(self, fields, vals):
        res = []
        for field in fields:
            if not vals.get(field, False):
                res.append(field)
        return res

    def verify_required_fields(self, obj, feed):
        resObj = self.env[obj._name]
        required_fields = self.get_required_feed_fields()
        for rec in obj:
            vals = EL(rec.read(required_fields[feed]))
            # fields_not_entered = self.required_field_not_filled(required_fields[feed], vals)
            fields_not_entered = self.with_context(channel_id=rec.channel_id).required_field_not_filled(required_fields[feed], vals)

            if vals.get('line_type', False) and feed == 'orders':  # checking order_line type
                # getting order_line required fields on the basis of order_line type i.e.(single or multi)
                line_fields = self.get_order_line_fields(rec, vals.get('line_type'), required_fields['order_lines'])
                if line_fields:
                    fields_not_entered.extend([{'line_fields': line_fields, 'line_type': vals.get('line_type')}])
            elif feed == 'products':
                # getting product variants required fields
                variant_fields = self.get_product_varient_fields(rec, required_fields['product_variant'])
                if variant_fields:
                    fields_not_entered.extend([{'variants': variant_fields}])
            if fields_not_entered:
                message = f"Required fields {fields_not_entered} are missing "
                rec.message = "%s <br/> %s" % (message, rec.message)
                sync_vals = dict(
                    status='error',
                    action_on='template',
                    action_type='import',
                    summary=message,
                )
                if rec.channel_id:
                    rec.channel_id._create_sync(sync_vals)
                rec.state = 'error'
                continue
            resObj += rec

        return resObj

    def get_order_line_fields(self, obj, line_type, order_line_fields):
        res = []

        if line_type == 'single':
            vals = EL(obj.read(order_line_fields))
            for field in order_line_fields:
                if not vals.get(field, False):
                    res.append(field)
        else:
            vals = EL(obj.read(['line_ids']))

            if vals.get('line_ids', False):
                lineObj1 = self.env['order.line.feed'].browse(vals['line_ids'])

                for lineObj in lineObj1:
                    line_vals = EL(lineObj.read(order_line_fields))

                    for field in order_line_fields:
                        if not line_vals.get(field, False):
                            empty_field = (lineObj.id, field)
                            res.append(str(empty_field))

        return res

    def get_product_varient_fields(self, obj, variant_fields):
        res = []
        vals = EL(obj.read(['feed_variants']))
        if vals.get('feed_variants', False):
            variantObj = self.env['product.variant.feed'].browse(vals['feed_variants'])
            for variant in variantObj:
                line_vals = EL(variant.read(variant_fields))
                # for field in variant_fields:
                # for now, only one field is in variant_fields that's why not iterated, uncomment this line if number of variant_fields increases
                if 'name_value' in variant_fields and not line_vals.get('name_value', False):
                    empty_field = (variant.id, 'name_value')
                    res.append(str(empty_field))
        return res
