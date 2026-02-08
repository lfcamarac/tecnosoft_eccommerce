# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################

from logging import getLogger

from odoo import _, api, models

_logger = getLogger(__name__)
from odoo.addons.odoo_multi_channel_sale.tools import chunks

class MultiChannelSale(models.Model):
    _inherit = 'multi.channel.sale'

    @api.model
    def cron_feed_evaluation(self):
        for object_model in ["product.feed", "order.feed", "category.feed", "partner.feed"]:
            for channel_id in self.search([('state','=','validate'),('active','=', True)]):
                records = self.env[object_model].search([
                    ("state", "!=", "done"),
                    ("channel_id", "=", channel_id.id)
                ])
                if records:
                    list_chunks = chunks(records, size=100)
                    for rec in list_chunks:
                        rec.with_context(channel_id=channel_id).import_items()
                        self._cr.commit()
        return True

    def get_cron_fields_map(self):
        """Extend this method to add more crons in extensions.
        method for cron in extension should be the conbination of channel(wix, salla, etc) and cron field name.
        method: '{channel}_{cron_field_name}' => salla_import_shipping_cron or wix_import_product_cron
        Returns dict: mapped dictionary of importing object and cron field name.
        """
        return {
                'order': 'import_order_cron',
                'product': 'import_product_cron',
                'partner': 'import_partner_cron',
                'category': 'import_category_cron'
            }

    @api.model
    def cron_import_all(self, model):
       
        for config_id in self.env['multi.channel.sale'].search([("state", "=", "validate"), ("active", "=", True)]):
            for cron_object, cron_field in self.get_cron_fields_map().items():
                read_field = config_id.read([cron_field])
                if model == cron_object and read_field and read_field[0].get(cron_field):
                    if hasattr(config_id, "{}_{}".format(config_id.channel, cron_field)):
                        getattr(config_id, "{}_{}".format(config_id.channel, cron_field))()
                    else:
                        _logger.warning(f"Error in MultichannelSale cron: {cron_object} import cron feature is not supported in channel {config_id.channel}")
        return True

    @api.model
    def set_channel_cron(self, ref_name='', active=False):
        try:
            cron_obj = self.env.ref(ref_name, False)
            if cron_obj:
                cron_obj.sudo().write(dict(active=active))
        except Exception as e:
            _logger.error("#1SetCronError  \n %r" % (e))
            raise Warning(e)
