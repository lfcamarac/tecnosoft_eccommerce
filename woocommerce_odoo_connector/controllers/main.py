# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
import json
import werkzeug
from odoo import http
from odoo.http import request
import logging
_logger = logging.getLogger(__name__)

class WoocommerceAuthentication(http.Controller):

    @http.route(["/woocommerce_odoo_connector/callback/<string:id>"], type='json', auth="public", csrf=False)
    def get_api_keys(self,id):
        channel_id = request.env['multi.channel.sale'].sudo().search([
            ('id','=',id),
        ])
        data = request.httprequest.get_data()
        data = json.loads(data)
        if data.get('user_id') == channel_id.unique_code:
            c_key = data.get('consumer_key')
            c_secret = data.get('consumer_secret')
            res = channel_id.sudo().write({'woocommerce_consumer_key':c_key,'woocommerce_secret_key':c_secret})

    @http.route(["/woocommerce_odoo_connector/redirect/<string:id>"], type='http', auth="user",csrf=False)
    def return_to_odoo(self,id,*args,**kwargs):
        channel_id = request.env['multi.channel.sale'].search([
            ('id','=',id),
        ])
        if channel_id:
            if kwargs.get('user_id') != channel_id.unique_code:
                channel_id.sudo().write({'state':'error'})
                channel_id.message_post(body="While generating the credentials with OAuth feature, the request user id does not match with response user id")
        url = request.env['multi.channel.sale'].redirect_to_channel(channel_id.id)
        return werkzeug.utils.redirect(url)
