import logging
_logger = logging.getLogger(__name__)
from odoo import models, fields, api
from odoo.exceptions import UserError

class ImportWoocommerceShipping(models.TransientModel):
    _name = "import.woocommerce.shipping"
    _inherit = "import.operation"
    _description = "Import Woocommerce Shipping"

    def import_now(self, **kwargs):
        woocommerce = self._context.get("woocommerce")
        channel_id = self._context.get("channel_id")
        if kwargs.get("woocommerce_object_id"):
            datalist = self._get_shipping_by_id(woocommerce, channel_id, **kwargs)
        else:
            datalist = self._get_shipping_all(woocommerce, channel_id,**kwargs)
        return datalist

    def _get_shipping_by_id(self,woocommerce,channel_id,**kwargs):
        shipping_data = woocommerce.get("shipping_methods/{}".format(kwargs.get("woocommerce_object_id"))).json()
        if "message" in shipping_data:
            raise UserError(f"Error in importing shipping {shipping_data['message']}")
        return [self._get_shipping_vals(channel_id,shipping_data)]

    def _get_shipping_all(self,woocommerce ,channel_id, **kwargs):
        params = {
                'page': kwargs.get('page'),
                'per_page': kwargs.get('page_size'),
                'order': 'asc' 
        }
        shipping_data = woocommerce.get(
            'shipping_methods',
            params=params,
        ).json()
        if "message" in shipping_data:
            raise UserError(f"Error in importing shipping : {shipping_data['message']}")
        return list(map(lambda x: self._get_shipping_vals(channel_id,x),shipping_data))

    def _get_shipping_vals(self, channel_id, shipping_data):
        return {
            "name": shipping_data.get("title"),
            "store_id": shipping_data.get("id"),
            "shipping_carrier": shipping_data.get("title"),
            "channel_id": channel_id.id,
            "channel": channel_id.channel,
            "description": shipping_data.get("description",False)
        }
