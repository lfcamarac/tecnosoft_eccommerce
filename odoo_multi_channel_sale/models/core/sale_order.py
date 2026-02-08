# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    channel_mapping_ids = fields.One2many(
        string='Mappings',
        comodel_name='channel.order.mappings',
        inverse_name='order_name',
        copy=False
    )

    def action_cancel(self):
        self.ensure_one()
        from_webhook = self._context.get('from_webhook')
        if not from_webhook:
            self.wk_pre_cancel()
        result = super(SaleOrder, self).action_cancel()
        if not from_webhook:
            self.wk_post_cancel(result)
        return result

    def wk_pre_cancel(self):
        for order_id in self:
            mapping_ids = order_id.channel_mapping_ids
            if mapping_ids and mapping_ids[0].channel_id.state == 'validate' and mapping_ids[0].channel_id.active:
                channel_id = mapping_ids[0].channel_id
                if hasattr(channel_id, '%s_pre_cancel_order' % channel_id.channel) and channel_id.sync_cancel and channel_id.state == 'validate':
                    getattr(channel_id, '%s_pre_cancel_order' % channel_id.channel)(self, mapping_ids)

    def wk_post_cancel(self, result):
        for order_id in self:
            mapping_ids = order_id.channel_mapping_ids
            if mapping_ids and mapping_ids[0].channel_id.state == 'validate' and mapping_ids[0].channel_id.active:
                channel_id = mapping_ids[0].channel_id
                if hasattr(channel_id, '%s_post_cancel_order' % channel_id.channel) and channel_id.sync_cancel and channel_id.state == 'validate':
                    res = getattr(channel_id, '%s_post_cancel_order' % channel_id.channel)(self, mapping_ids, result)
                    sync_vals = dict(
                        action_on='order_status',
                        ecomstore_refrence=mapping_ids[0].store_order_id,
                        odoo_id=mapping_ids[0].odoo_order_id,
                        action_type='export',
                    )
                    if res:
                        sync_vals['status'] = 'success'
                        sync_vals['summary'] = 'RealTime Order Status -> Cancelled.'
                    else:
                        sync_vals['status'] = 'error'
                        sync_vals['summary'] = 'Order cancellation failed at the ecommerce end.'
                    channel_id._create_sync(sync_vals)
