# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################

from odoo import models, _

class MultiChannelSale(models.Model):
    _inherit = 'multi.channel.sale'

    def sync_order_feeds(self, vals, **kwargs):
        """
            ==Vals is a List of dictionaries==
            vals:list(dict(),dict())
            partner_vals:list(dict(),dict())
            category_vals:list(dict(),dict())
            product_vals:list(dict(),dict())
            channel_vals: dict(channel_id=id)
        """
        self.ensure_one()
        contextualize_data = dict()
        context = dict(self._context)
        contextualize_data.update(dict(self.env['wk.feed'].contextualize_mappings('order', self.ids)._context))
        contextualize_data.update(dict(self.env['wk.feed'].contextualize_mappings('product', self.ids)._context))
        contextualize_data.update(dict(self.env['wk.feed'].contextualize_mappings('category', self.ids)._context))
        contextualize_data.update(dict(self.env['wk.feed'].contextualize_feeds('category', self.ids)._context))
        contextualize_data.update(dict(self.env['wk.feed'].contextualize_feeds('product', self.ids)._context))
        contextualize_data.update(context)
        self = self.with_context(contextualize_data)
        message = ''
        try:
            partner_vals = kwargs.get('partner_vals')
            category_vals = kwargs.get('category_vals')
            product_vals = kwargs.get('product_vals')
            channel_vals = self.get_channel_dict(kwargs)

            if partner_vals:
                message += self.sync_partner_feeds(
                    partner_vals, channel_vals=channel_vals).get('message', '')
            if kwargs.get('category_vals'):
                message += self.sync_category_feeds(
                    category_vals, channel_vals=channel_vals).get('message', '')
            if kwargs.get('product_vals'):
                message += self.sync_product_feeds(
                    product_vals, channel_vals=channel_vals).get('message', '')
            for val in vals:
                obj = self.env['order.feed'].search([('store_id', '=', val.get('store_id'))])
                obj.write(dict(line_ids=[(6, 0, [])]))
            res = self.create_model_objects(
                'order.feed', vals, extra_val=channel_vals)
            message += res.get('message', '')
            data = res.get('data')
            if data:
                for data_item in data:
                    import_res = data_item.import_order(self)
                    message += import_res.get('message', '')
        except Exception as e:
            message += '%r' % (e)
        return dict(
            kwargs=kwargs,
            message=message
        )

    def sync_partner_feeds(self, vals, **kwargs):
        self.ensure_one()
        channel_vals = self.get_channel_dict(kwargs)
        res = self.create_model_objects('partner.feed', vals, extra_val=channel_vals)
        message = res.get('message', '')
        data = res.get('data')
        if data:
            for data_item in data:
                import_res = data_item.import_partner(self)
                message += import_res.get('message', '')
        return dict(
            message=message
        )

    def sync_category_feeds(self, vals, **kwargs):
        self.ensure_one()
        channel_vals = self.get_channel_dict(kwargs)
        res = self.create_model_objects('category.feed', vals, extra_val=channel_vals)
        message = res.get('message', '')
        data = res.get('data')
        if data:
            for data_item in data:
                import_res = data_item.import_category(self)
                message += import_res.get('message', '')
        return dict(
            message=message
        )

    def sync_product_feeds(self, vals, **kwargs):
        self.ensure_one()
        channel_vals = self.get_channel_dict(kwargs)
        res = self.create_model_objects('product.feed', vals, extra_val=channel_vals)
        context = dict(self._context)
        for val in vals:
            obj = self.env['product.feed'].search([('store_id', '=', val.get('store_id'))])
            obj.write(dict(feed_variants=[(6, 0, [])]))
        res = self.with_context(context).create_model_objects('product.feed', vals, extra_val=channel_vals)
        message = res.get('message', '')
        data = res.get('data')
        if data:
            for data_item in data:
                import_res = data_item.import_product(self)
                message += import_res.get('message', '')
        return dict(
            message=message
        )

    def get_channel_dict(self, kwargs):
        channel_vals = kwargs.get('channel_vals')
        if not channel_vals:
            channel_vals = self.get_channel_vals()
            channel_vals['channel'] = channel_vals.pop('ecom_store')
        return channel_vals
