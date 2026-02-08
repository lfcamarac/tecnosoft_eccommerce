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
    "name": "Odoo Multi-Channel Sale",
    "summary": """Connect and manage multiple e-commerce platforms in Odoo.""",
    "category": "eCommerce",
    "version": "2.8.19",
    "sequence": 1,
    "author": "TecnoSoft",
    "license": "Other proprietary",
    "website": "https://tecnosoft.dev",
    "description": """Multi-channel connector for Odoo""",
    "live_test_url": "https://apps.odoo.com/apps/modules/browse?repo_maintainer_id=120854&search=extensions%20for%20multichannel",
    "depends": [
        'stock_delivery',
        'wk_wizard_messages',
    ],
    "data": [
        'security/security.xml',
        'security/ir.model.access.csv',

        'wizard/wizard_message_view.xml',
        'wizard/imports/import_operation.xml',
        'wizard/exports/export_operation.xml',

        'views/core/res_config.xml',
        'views/base/multi_channel_sale.xml',
        'views/menus.xml',
        'views/base/channel_order_states.xml',
        'views/core/product_category.xml',
        'views/core/product_template.xml',
        'views/core/product_product.xml',
        'views/core/product_pricelist.xml',
        'views/core/res_partner.xml',
        'views/core/sale_order.xml',
        'views/feeds/category_feed.xml',
        'views/feeds/order_feed.xml',
        'views/feeds/order_line_feed.xml',
        'views/feeds/partner_feed.xml',
        'views/feeds/product_feed.xml',
        'views/feeds/variant_feed.xml',
        'views/feeds/shipping_feed.xml',
        'views/mappings/channel_synchronization.xml',
        'views/mappings/account_journal_mapping.xml',
        'views/mappings/account_mapping.xml',
        'views/mappings/attribute_mapping.xml',
        'views/mappings/attribute_value_mapping.xml',
        'views/mappings/category_mapping.xml',
        'views/mappings/order_mapping.xml',
        'views/mappings/partner_mapping.xml',
        'views/mappings/pricelist_mapping.xml',
        'views/mappings/product_template_mapping.xml',
        'views/mappings/product_variant_mapping.xml',
        'views/mappings/shipping_mapping.xml',
        #  'views/template.xml',
        'wizard/exports/export_category.xml',
        'wizard/exports/export_product.xml',
        'wizard/exports/export_template.xml',
        'wizard/update_mapping_wizard.xml',
        'wizard/feed_wizard.xml',
        'data/evaluation_action.xml',
        'data/export_action.xml',
        'data/update_mapping_action.xml',
        'data/cron.xml',
        'data/data.xml'
    ],
    'assets': {
        'web.assets_backend': [
             'web/static/lib/jquery/jquery.js',
            'odoo_multi_channel_sale/static/src/components/xml/multichannel_dashboard.xml',
            'odoo_multi_channel_sale/static/src/components/xml/instance_dashboard.xml',
            'odoo_multi_channel_sale/static/src/css/custom_ribbons.css',
            'odoo_multi_channel_sale/static/src/css/dashboard.css',
            'odoo_multi_channel_sale/static/src/js/dashboard.js',
        ],
        # 'web.assets_qweb': [
        #   'odoo_multi_channel_sale/static/src/xml/multichannel_dashboard.xml',
        #   'odoo_multi_channel_sale/static/src/xml/instance_dashboard.xml',
        # ],

    },
    "images": ['static/description/banner.png'],
    "application": True,
    "installable": True,
    "auto_install": False,
    "price": 29,
    "currency": "USD",
    "pre_init_hook": "pre_init_check",
}
