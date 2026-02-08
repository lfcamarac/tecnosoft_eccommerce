# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    See LICENSE file for full copyright and licensing details.
##########H#########Y#########P#########N#########O#########S###################
from odoo import api, fields, models, exceptions
import logging
_logger = logging.getLogger(__name__)

class WoocommerceImportOperation(models.TransientModel):
    _inherit = "import.operation"

    woocommerce_object_id = fields.Char()
    woocommerce_import_date_from = fields.Datetime()
    woocommerce_filter_type = fields.Selection(
        selection=[
            ('all', 'All'),
            ('by_id', 'By Id(s)'),
            ('by_date', 'By Date')]
        ,
        default='all'
    )

    def woocommerce_get_filter(self):
        return dict(
            woocommerce_filter_type = self.woocommerce_filter_type,
            woocommerce_object_id=self.woocommerce_object_id,
            woocommerce_import_date_from=self.woocommerce_import_date_from,
            page = 1
        )
