# # -*- coding: utf-8 -*-
# ##############################################################################
# # Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# # See LICENSE file for full copyright and licensing details.
# # License URL : <https://store.webkul.com/license.html/>
# ##############################################################################
from odoo.tests import tagged
from odoo.tests import common
# from odoo.addons.account.tests.common import AccountTestInvoicingCommon
# from odoo.addons.stock.tests.common2 import TestStockCommon
# from odoo.addons.base_setup.tests.common im
from odoo.addons.base_setup.tests.test_res_config import TestResConfig
from odoo import _

@tagged('post_install', '-at_install')
class TestMultiChannelCommon(common.TransactionCase):

    def setUp(self):
        super(TestMultiChannelCommon, self).setUp()
        self.category_obj_M = self.env['product.category']
        user = self.env['res.users'].search([], limit=1)[0]
        self.channel_obj = self.env['multi.channel.sale']
        self.ModelDataObj = self.env['ir.model.data']
        self.product_category_A = self.category_obj_M.create({'name': 'All_A'})
        self.channel = self.channel_obj.with_context(test_channel=True).create(
            {
                'state': 'draft',
                'environment': 'sandbox',
                'active': True,
                'debug': 'enable',
                'image': False,
                'name': 'ChannelA',
                'channel': 'ecommerce',
                'url': False,
                'email': False,
                'api_key': False,
                'auto_evaluate_feed': True,
                'company_id': self.env['stock.warehouse'].search([], limit=1)[0].company_id.id,
                'use_api_limit': True,
                'api_record_limit': 100,
                'total_record_limit': 0,
                'is_child_store': False,
                'default_store_id': False,
                'color': '#000000',
                'color_index': 0,
                'blog_url': False,
                'store_url': False,
                'payment_term_id': False,
                'crm_team_id': self.env['crm.team'].search([], limit=1)[0].id,
                'sales_person_id': False,
                'default_tax_type': 'exclude',
                'discount_product_id': self.ModelDataObj._xmlid_to_res_id('odoo_multi_channel_sale.discount_product_id'),
                'delivery_product_id': self.ModelDataObj._xmlid_to_res_id('odoo_multi_channel_sale.delivery_product_id'),
                'sync_invoice': False,
                'sync_shipment': False,
                'sync_cancel': False,
                'default_category_id': self.product_category_A.id,
                'pricelist_name': self.env['product.pricelist'].with_context(active_test=False).search([], limit=1)[0].id,
                'sku_sequence_id': False,
                'language_id': self.env['res.lang'].search([('code', '=', user.lang)]).id,
                'channel_default_product_categ_id': False,
                'auto_sync_stock': False,
                'channel_stock_action': 'qoh',
                'warehouse_id': self.env['stock.warehouse'].search([], limit=1)[0].id,
                'location_id': self.env['stock.warehouse'].search([], limit=1)[0].lot_stock_id.id,
                'order_state_ids': [],
                'import_order_date': False,
                'import_product_date': False,
                'import_customer_date': False,
                'update_order_date': False,
                'update_product_date': False,
                'update_customer_date': False,
                'import_category_cron': False,
                'import_partner_cron': False,
                'import_product_cron': False,
                'import_order_cron': False,
                'message_follower_ids': [],
                'activity_ids': [],
                'message_ids': []}
        )
        # category_feed##########################################################################
        self.category_feed_obj = self.env['category.feed']
        self.category_feed_A = self.category_feed_obj.create({
            'channel_id': self.channel.id,
            'name': 'Root',
            'store_id': '1',
            'active': True,
            'parent_id': '',
            'leaf_category': False,
        })
        self.category_feed_B = self.category_feed_obj.create({
            'channel_id': self.channel.id,
            'name': 'Home',
            'store_id': '2',
            'active': True,
            'parent_id': 1,
            'leaf_category': True,
        })

        # product_feed############################################################################
        self.product_feed_obj = self.env['product.feed']
        variants = [(0, 0, dict(
            store_id='1',
            name_value=[{'name': 'Size', 'value': 'S', 'attrib_name_id': 1, 'attrib_value_id': 1},
                    {'name': 'Color', 'value': 'White', 'attrib_name_id': 2, 'attrib_value_id': 8}],
            extra_categ_ids='',
            type='consu',
            is_storable=True,
            list_price='12',
            default_code='demo_sku123',
            barcode='ABCD123',
            description_sale='variant desc',
            description_purchase='',
            standard_price='14',
            sale_delay='',
            qty_available='12',
            weight='10',
            weight_unit='10',
            length='10',
            width='10',
            height='10',
            dimensions_unit='',
            wk_product_id_type='',
            image_url='',
            hs_code='',
            wk_default_code='',
        )),
            (0, 0, dict(
                store_id='2',
                name_value=[{'name': 'Size', 'value': 'M', 'attrib_name_id': 1, 'attrib_value_id': 2},
                            {'name': 'Color', 'value': 'Black', 'attrib_name_id': 2, 'attrib_value_id': 7}],
                extra_categ_ids='',
                type='consu',
                is_storable=True,
                list_price='12',
                default_code='demo_sku1235',
                barcode='ABCD1235',
                description_sale='variant desc12',
                description_purchase='',
                standard_price='14',
                sale_delay='',
                qty_available='12',
                weight='10',
                weight_unit='10',
                length='10',
                width='10',
                height='10',
                dimensions_unit='',
                wk_product_id_type='',
                image_url='',
                hs_code='',
                wk_default_code='',
            ))
        ]

        self.product_feed_A = self.product_feed_obj.create(
            {
                'active': True,
                'channel_id': self.channel.id,
                'name': 'A test Product',
                'store_id': '1',
                'extra_categ_ids': '',
                'list_price': '170',
                'image_url': '',
                'image': False,
                'default_code': '1234567',
                'barcode': '9876543',
                'type':'consu',
                'is_storable':True,
                'wk_product_id_type': False,
                'description_sale': 'Product_description',
                'description_purchase': 'discription_purchase',
                'standard_price': False,
                'sale_delay': False,
                'qty_available': '12',
                'weight': '0.0024',
                'feed_variants': variants,
                'weight_unit': False,
                'length': False,
                'width': False,
                'height': False,
                'dimensions_unit': False,
                'hs_code': False,
                'wk_default_code': False}
        )
        self.product_feed_B = self.product_feed_obj.create(
            {
                'active': True,
                'channel_id': self.channel.id,
                'name': 'A test Product B',
                'store_id': '2',
                'extra_categ_ids': '1,2',
                'list_price': '171',
                'image_url': '',
                'image': False,
                'default_code': '123456798',
                'barcode': '987654312',
                'type': 'consu',
               
                'is_storable':True,
                'wk_product_id_type': False,
                'description_sale': 'Product_description1',
                'description_purchase': 'discription_purchase2',
                'standard_price': False,
                'sale_delay': False,
                'qty_available': '121',
                'weight': '0.1034',
                'feed_variants': [],
                'weight_unit': False,
                'length': False,
                'width': False,
                'height': False,
                'dimensions_unit': False,
                'hs_code': False,
                'wk_default_code': False}
        )

        # partner feed ########################################################################
        self.partner_feed = {
            'active': True,
            'channel_id': self.channel.id,
            'name': 'Test_Partner_A_contact',
            'last_name': 'Test',
            'email': 'test@testexmaple.com',
            'store_id': '1',
            'type': 'contact',
            'parent_id': False,
            'contacts': [
                {
                    'id': 2,
                    'active': True,
                    'channel_id': self.channel.id,
                    'name': 'Test_Partner_A_invoice',
                    'store_id': '1',
                    'email': 'test@invoicetestexmaple.com',
                    'phone': '(000)-000-000',
                    'mobile': '0000000000',
                    'website': '',
                    'last_name': 'Test_invoice',
                    'street': 'First Street_invoice',
                    'street2': 'Second Street_invoice',
                    'city': 'Test City Invoice',
                    'zip': '000 000',
                    'state_id': '1',
                    'state_name': 'test',
                    'country_id': 'IN',
                    'type': 'invoice',
                    'parent_id': '1',
                    'vat': '0000000'},
                {
                    'id': 3,
                    'active': True,
                    'channel_id': self.channel.id,
                    'name': 'Test_Partner_A_shipping',
                    'store_id': '1',
                    'email': 'test@shippingtestexmaple.com',
                    'phone': '(000)-000-000',
                    'mobile': '0000000000',
                    'website': '',
                    'last_name': 'Test shipping',
                    'street': 'First Street shipping',
                    'street2': 'Second Street shipping',
                    'city': 'Test City shipping',
                    'zip': '000 000',
                    'state_id': '1',
                    'state_name': 'test',
                    'country_id': 'IN',
                    'type': 'delivery',
                    'parent_id': '1',
                    'vat': '0000000'}
            ]}
        self.partner_feed_record = self.env['partner.feed'].with_context(channel_id=self.channel)._create_feeds([self.partner_feed])
        # self.assertTrue(self.partner_feed_record[2],msg="partner feed should be created")

        # getting feed object
        self.partner_feed_record_contact = self.partner_feed_record[2][0]
        self.partner_feed_record_invoice = self.partner_feed_record[2][1]
        self.partner_feed_record_shipping = self.partner_feed_record[2][2]

        # order_feed###################################################################################
        order_feed_obj = self.env['order.feed']
        self.test_order_feed_A = order_feed_obj.create({
            'name': "TestOrder0000",
            'channel_id': self.channel.id,
            'store_id': '1',
            'store_source': False,
            'partner_id': '5',
            'order_state': 'sale',
            'carrier_id': 'Delivery',
            'payment_method': 'cheque',
            'currency': 'USD',
            'line_type': 'multi',
            'customer_name': 'test_customer_name',
            'customer_email': 'testcustomer@testexmaple.com',
            'date_invoice': '2022-02-15 17:10:31',
            'date_shipping': '2022-02-15 17:10:31',
            'date_order': '2022-02-15 15:10:31',
            'confirmation_date': '2022-02-15 17:10:31',
            'customer_vat': '000000000',
            'line_ids': [(0, 0, {'line_name': 'A test Product B',
                                 'line_price_unit': 171,
                                 'line_product_uom_qty': 2,
                                 'line_product_id': 2,
                                 'line_taxes': [{'rate': 5.0, 'name': 'GST 5%', 'include_in_price': False, 'tax_type': 'percent'}],
                                 })],

            'same_shipping_billing': False,
            'shipping_partner_id': 'shipping_1',
            'shipping_name': ' ',
            'shipping_street': '',
            'shipping_street2': '',
            'shipping_email': 'akash.gaur305@webkul.com',
            'shipping_zip': '000000',
            'shipping_city': 'TestCity',
            'shipping_state_id': 'UP',
            'shipping_country_id': 'IN',

            'invoice_partner_id': 'billing_1',
            'invoice_name': 'test_customer_name',
            'invoice_email': 'test@invoicetestexmaple.com',
            'invoice_phone': '',
            'invoice_street': 'Demo Address',
            'invoice_street2': '',
            'invoice_zip': '000000',
            'invoice_city': 'TestCity',
            'invoice_state_id': 'UP',
            'invoice_country_id': 'IN',
        })
        # shipping_feeds#####################################################
        shipping_feed_obj = self.env['shipping.feed']
        self.shipping_feeds_A = shipping_feed_obj.create({
            'name': 'Flat rate',
            'active': True,
            'channel_id': self.channel.id,
            'store_id': 'flat_rate',
            'shipping_carrier': 'Flat rate',
            'is_international': False,
            'description': 'Lets you charge a fixed rate for shipping.',
            'store_id': 'flat_rate'})
