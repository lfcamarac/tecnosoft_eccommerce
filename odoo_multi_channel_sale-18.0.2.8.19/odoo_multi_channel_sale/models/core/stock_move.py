# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import models
from logging import getLogger

_logger = getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, **kwargs):
        """
            Makes the move done and if all moves are done,it will finish the picking.
            @return:
        """
        res = super()._action_done(**kwargs)
        res.post_operation(stock_operation='_action_done')
        return res

    def _action_confirm(self, *args, **kwargs):
        """ Confirms stock move or put it in waiting if it's linked to another move.
        """
        res = super()._action_confirm(*args, **kwargs)
        res.post_operation(stock_operation='_action_confirm')
        return res

    def _action_cancel(self, *args, **kwargs):
        cancelled = self.filtered(lambda self: self.state == 'cancel')
        res = super()._action_cancel(*args, **kwargs)
        if not cancelled:
            self.post_operation(stock_operation='_action_cancel')
        return res

    def post_operation(self, stock_operation):
        initial_channel_ids = self.env['multi.channel.sale'].search([]).ids
        for move in self:
            channel_ids = set(initial_channel_ids.copy())

            product_id = move.product_id
            if move.origin and move.picking_type_id.code == 'outgoing':
                sale_id = self.env['sale.order'].search([('name', '=', move.origin)])
                if sale_id:
                    channel_id = sale_id.channel_mapping_ids.channel_id
                    if channel_id:
                        channel_ids -= set(channel_id.ids)

            if channel_ids:
                source_location_id = move.location_id
                dest_location_id = move.location_dest_id
                for mapping in product_id.channel_mapping_ids.filtered(lambda mapping: mapping.channel_id.id in channel_ids):
                    channel_id = mapping.channel_id
                    if not channel_id.auto_sync_stock or not channel_id.active or not channel_id.state == 'validate':
                        if channel_id.debug == 'enable':
                            message = "Channel Not Active" if not channel_id.active else "Channel Not Connected" if not channel_id.state == 'validate' else "Channel Stock Sync Not Enabled"
                            _logger.debug(f'Stock Can not be synced: Channel: [ID: {channel_id.id}] {channel_id.name}, Reason: {message}, Product: [ID: {product_id.id}] {product_id.display_name}')
                        continue
                    if channel_id.channel_stock_action == 'qoh':
                        if stock_operation == '_action_confirm':
                            continue
                    elif channel_id.channel_stock_action =="fq":
                        if stock_operation == '_action_done' and move.location_usage != 'inventory':
                            continue                  
                    location_ids = channel_id.location_id + channel_id.location_id.child_ids
                    if source_location_id in location_ids or dest_location_id in location_ids:
                        qty = channel_id.get_quantity(product_id)
                        sync_quantity_channel = getattr(channel_id, 'sync_quantity_%s' % channel_id.channel, None)
                        sync_vals = dict(
                                action_on='stock',
                                ecomstore_refrence=mapping.store_product_id,
                                odoo_id=product_id.id,
                                action_type='export',
                            )
                        if sync_quantity_channel:
                            sync_quantity_channel(mapping, qty)
                            sync_vals['status'] = 'success'
                            sync_vals['summary'] = f"""RealTime Product Stock Sync Successful from odoo to ecommerce.<br>
                            Product: {product_id.name}<br>
                            Stock Update: {qty}"""
                        else:
                            _logger.error('Auto Sync Quantity method not found for %s', channel_id.channel)
                            sync_vals['status'] = 'error'
                            sync_vals['summary'] = 'The product stock update was unsuccessful at the ecommerce end.'
                        channel_id._create_sync(sync_vals)
                            

    def multichannel_sync_quantity(self, pick_details):
        """
            : Deprecated
            Method to be overridden by the multichannel modules to provide real time stock update feature
        """
        pass
