# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import models, fields, api
from odoo.exceptions import UserError

from urllib.parse import urljoin
from logging import getLogger
_logger = getLogger(__name__)


class MultiChannelWebhook(models.Model):
    _inherit = "multi.channel.sale"

    # New Order Webhook
    is_create_order_webhook = fields.Boolean(string="Activate Webhook")
    order_webhook_url = fields.Char(string="New Created Order Webhook-Url", compute="_order_webhook_url")
    order_webhook_id = fields.Char(help="Store the New Created Order Webhook ID of the Ecomm end if supported!")

    # Order Update webhook
    is_update_order_webhook = fields.Boolean(string="Activate Update Webhook")
    order_update_webhook_url = fields.Char(string="Update Order Webhook-Url", compute="_order_update_webhook_url")
    order_update_webhook_id = fields.Char(help="Store the Update order Webhook ID if Supported!")
    create_order_webhook_status = fields.Selection([
        ('connected', 'Connected'),
        ('not_connected', 'Not Connected')
    ], string="Create Order Webhook Status", default='not_connected')

    def _order_webhook_url(self):
        """
            Computed Webhook URL for Created Order
        """
        url = urljoin(self.get_base_url(), f'multichannel/create/order/webhook/{self.id}')
        self.order_webhook_url = url

    def _order_update_webhook_url(self):
        """
            Computed Webhook URL for Updated Order
        """
        url = urljoin(self.get_base_url(), f'multichannel/update/order/webhook/{self.id}')
        self.order_update_webhook_url = url

    # @api.constrains('is_create_order_webhook')
    def change_order_webhook(self):
        """
            Create following method in extension only if it's webhook enables
            using API Call.
            Eg. method=>: activate_salla_order_webhook, deactivate_salla_order_webhook
            or
            When no need to add url manually to ecomm end. Otherwise extension will
            provide the required information regarding how to enable webhook.
        """
        if self.state == 'validate':
            method, webhook_type = False, 'Active/Inactive'
            webhook_url = self.order_webhook_url
            message = f'Error in {webhook_type} Order Webhook: '
            if not self.is_create_order_webhook and hasattr(self, f'activate_{self.channel}_order_webhook'):
                webhook_type = 'Activating'
                method = getattr(self, f'activate_{self.channel}_order_webhook', False)
                self.is_create_order_webhook = True
            elif self.is_create_order_webhook and hasattr(self, f'deactivate_{self.channel}_order_webhook'):
                webhook_type = 'Deactivating'
                method = getattr(self, f'deactivate_{self.channel}_order_webhook', False)
                self.is_create_order_webhook = False
            if method:
                try:
                    method(webhook_url, 'create')
                except Exception as e:
                    message += str(e)
                    if self.is_create_order_webhook:
                        raise UserError(message)
                    _logger.error(message)


    # @api.constrains('is_update_order_webhook')
    def change_update_order_webhook(self):
        """
            Create following method in extension only if
            it's webhook enables/disable using API Calls.
            Eg. method=>: activate_salla_order_webhook, deactivate_salla_order_webhook
            or
            When no need to add url manually to ecomm end. Otherwise extension will
            provide the required information regarding how to enable webhook.
        """
        if self.state == 'validate':
            method, webhook_type = False, 'Active/Inactive'
            webhook_url = self.order_update_webhook_url
            message = f'Error in {webhook_type} Update Order Webhook: '
            if not self.is_update_order_webhook and hasattr(self, f'activate_{self.channel}_order_webhook'):
                method = getattr(self, f'activate_{self.channel}_order_webhook', False)
                self.is_update_order_webhook = True
            elif self.is_update_order_webhook and hasattr(self, f'deactivate_{self.channel}_order_webhook'):
                method = getattr(self, f'deactivate_{self.channel}_order_webhook', False)
                self.is_update_order_webhook = False
            if method:
                try:
                    method(webhook_url, 'update')
                except Exception as e:
                    message += str(e)
                    if self.is_update_order_webhook:
                        raise UserError(message)
                    _logger.error(message)
