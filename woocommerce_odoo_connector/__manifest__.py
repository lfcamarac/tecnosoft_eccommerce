# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
    "name":  "WooCommerce Odoo Connector",
    "summary":  """Integrates Odoo with WooCommerce for seamless e-commerce management.""",
    "category":  "eCommerce",
    "version":  "2.4.0",
    "sequence":  1,
    "author":  "TecnoSoft",
    "license":  "Other proprietary",
    "website":  "https://tecnosoft.dev",
    "description":  """WooCommerce integration for Odoo""",
    "live_test_url":  "https://multichannel.odoo-apps-demo.webkul.in/multi-channel?channel=woocommerce",
    "depends":  ['odoo_multi_channel_sale'],
    "data":  [
        'security/ir.model.access.csv',

        'views/woc_config_views.xml',
        'views/inherited_woocommerce_dashboard_view.xml',

        'wizard/export_category_view.xml',
        'wizard/export_template_view.xml',
        'wizard/import_operation.xml',

        'data/demo.xml',
    ],
    'assets': {
    'web.assets_backend': [
      'woocommerce_odoo_connector/static/src/xml/inherit_multi_channel_template.xml',
    ],
    },
    "images":  ['static/description/banner.gif'],
    "application":  True,
    "installable":  True,
    "auto_install": False,
    "price":  220,
    "currency":  "USD",
    "external_dependencies":  {'python': ['woocommerce']},
    "pre_init_hook"        :  "pre_init_check",
}
