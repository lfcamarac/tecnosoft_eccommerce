# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import http, SUPERUSER_ID, api
from odoo.http import request
import json
from logging import getLogger
_logger = getLogger(__name__)

# Webhook Implementation
class ChannelWebhook(http.Controller):

    def get_super_env(self):
        return api.Environment(request.cr, SUPERUSER_ID, request.context)

    # Extra Webhook can be used from extension, for other webhooks
    @http.route('/multichannel/<string:object>/webhook/<string:channel_id>', type="http", auth="public", csrf=False)
    def import_common_webhook(self, channel_id, object, **kwargs):
        status_code, message, text = 200, "success", "Success : Webhook processed successfully"
        if channel_id:
            try:
                channel_id = int(channel_id)
            except:
                _logger.error(f'Multi Channel Channel ID [{channel_id}] Can not be identified!')
                return
            env = self.get_super_env()
            channel = env['multi.channel.sale'].browse(channel_id)
            if channel and channel.state == 'validate' and channel.active:
                try:
                    event_data = request.httprequest.data
                    event_headers = request.httprequest.headers
                    if hasattr(channel, f'{channel.channel}_webhook_{object}_data'):
                        getattr(channel, f'{channel.channel}_webhook_{object}_data')(event_data, event_headers, **kwargs)
                except Exception as e:
                    status_code, message, text = 500, "error", "Internal Server Error : An Error while processing webhook"
                    _logger.error(f'Webhook Error: Can not import the Webhook data from {channel.channel} to Odoo.')
            else:
                status_code, message, text = 404, "error", "Error : The requested URL was not found."
        error_data = {
			'status_code': status_code,
			'message': message,
            'text': text
		}
        return request.make_response(
					json.dumps(error_data),
					[('Content-Type', 'application/json')]
					)      

    # Order Create and Update Webhook
    @http.route('/multichannel/<string:type>/order/webhook/<string:channel_id>', type="http", auth="public", csrf=False)
    def import_order_webhook(self, channel_id, type, **kwargs):
        """
            It will get the orders webhook data and pass to extensions method to
            process it and returned order data will be created/updated in Odoo.
            params:
                channel_id(str): Channel Odoo ID
                type(str): 'create' or 'update'
        """
        status_code, message, text = 200, "success", "Success : Webhook processed successfully"
        if channel_id:
            request.update_context = dict(request.context)
            try:
                channel_id = int(channel_id)
            except:
                _logger.error(f'Multi Channel Channel ID [{channel_id}] Can not be identified!')
                return
            env = self.get_super_env()
            request.update_context['super_env'] = env
            channel = env['multi.channel.sale'].browse(channel_id)
            _logger.info(f'Calling {channel.channel} Realtime Webhook')
            if channel and channel.state == 'validate' and channel.active and (channel.is_create_order_webhook or channel.is_update_order_webhook):
                if channel.debug == 'enable':
                    _logger.info(f'RealTime Order {type} is Running for {channel.channel}: {channel.name}')
                try:
                    event_data = request.httprequest.data
                    event_headers = request.httprequest.headers
                    if type == 'create' and channel.is_create_order_webhook and hasattr(channel, f'{channel.channel}_order_webhook_data'):
                        response_data = getattr(channel, f'{channel.channel}_order_webhook_data')(event_data, event_headers, type, **kwargs)
                        message = self.create_order_data(channel, response_data)
                    elif type == 'update' and channel.is_update_order_webhook and hasattr(channel, f'{channel.channel}_order_webhook_data'):
                        response_data = getattr(channel, f'{channel.channel}_order_webhook_data')(event_data, event_headers, type, **kwargs)
                        message = self.update_order_data(channel, response_data)
                    else:
                        status_code, message, text = 400, "error", "Bad Request : No PushData Supplied"
                        message = f'Webhook {type} Order is Not Active or Nothing to Import in RealTime from {channel.channel} To Odoo'
                    _logger.info(message)
                except Exception as e:
                    status_code, message, text = 500, "error", "Internal Server Error : An Error while processing webhook"
                    _logger.error('Error in RealTime Order Import: %r', e)
                    if channel.debug == 'enable':
                        _logger.error('Error: %r', e, exc_info=True)
            else:
                status_code, message, text = 404, "error", "Error : The requested URL was not found."
            
        error_data = {
			'status_code': status_code,
			'message': message,
            'text': text
		}
        return request.make_response(
					json.dumps(error_data),
					[('Content-Type', 'application/json')]
					)

    def create_order_data(self, channel, response_data):
        env = request.update_context.get('super_env') or self.get_super_env()
        message = 'Something Went Wrong: Error in Creating Order in Realtime'
        if response_data and response_data.get('store_id'):
            store_id = response_data.get('store_id')
            data = response_data.get('data')
            data = data if isinstance(data, list) else [data]
            if not channel.match_order_mappings(store_id):
                s_id, e_id, feed_id = env['order.feed'].with_context(
                    channel_id=channel)._create_feeds(data)
                if feed_id:
                    feed_id.message = "<br/><span class='text-info'>Realtime Order Imported Successfully</span>"
                    message = self.evaluate_order_webhook(channel, feed_id)
            else:
                message = 'Realtime Order Create: Nothing to Create, Order is Already Created in Odoo.'
        return message

    def update_order_data(self, channel, return_data):
        """
            It will decide what kind of update to perform according to
            the response of extension.(Status update or Complete Update)
        """
        env = request.update_context.get('super_env') or self.get_super_env()
        message = f'Nothing to Update in RealTime from {channel.channel} To Odoo'
        if return_data:
            store_id = return_data.get('store_id')
            data = return_data.get('data')
            if store_id and data:
                order_mapping = channel.match_order_mappings(store_id)
                feed = env['order.feed'].search([
                    ('channel_id','=', channel.id),
                    ('store_id','=', store_id)
                    ], limit=1)
                initial_feed_state = feed.state
                if not order_mapping and not feed:
                    return f"Error Update Order Webhook, Mapping and Feed is not exists for {channel.channel} Order, [StoreID: {store_id}]"
                data = data[0] if isinstance(data, list) else data
                if return_data.get('update_case') == 'status_update' and data.get('order_state'):
                    if feed:
                        # Update Order Status With Feed
                        if not feed.order_state == data.get('order_state'):
                            write_data = {'order_state': data.get('order_state')}
                            if data.get('payment_method'):
                                write_data.update({'payment_method': data.get('payment_method')})
                            feed.write(write_data)
                            message = "Order Feed Status Updated Successfully in RealTime"
                            if initial_feed_state == 'done':
                                return self.evaluate_order_webhook(channel, feed)
                        else:
                            message = f"Order State [{feed.name}] is Already Updated in Feeds"
                    else:
                        # Update Order Status Without Feed
                        if not order_mapping.store_order_status == data.get('order_state'):
                            order = order_mapping.order_name
                            if order:
                                message = env['multi.channel.skeleton']._SetOdooOrderState(order, channel, data.get('order_status'), data.get('payment_method', False))
                        else:
                            message = "Order state is already Updated in Odoo"
                elif return_data.get('update_case') == 'complete_update':
                    # Order Complete Update or Create Feed
                    data = data if isinstance(data, list) else [data]
                    s_id, e_id, feed_id = env['order.feed'].with_context(
                    channel_id=channel)._create_feeds(data)
                    if feed_id and initial_feed_state == 'done':
                        return self.evaluate_order_webhook(channel, feed)
                    message = "Order Feed Created/Updated Successfully in RealTime"
                
                message += f' [StoreID: {store_id}]'
        return message

    def evaluate_order_webhook(self, channel, feed_id):
        message = "RealTime Order Feed Created/Updated Successfully, "
        if channel.auto_evaluate_feed:
            feed_id.with_context(from_webhook=True).import_items()
            if feed_id.state == 'done':
                message = "RealTime Order Evaluated Successfully, "
        return message + f'[Order Ref: {feed_id.name}, StoreID: {feed_id.store_id}]'
