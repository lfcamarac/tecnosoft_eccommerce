# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo.addons.odoo_multi_channel_sale.tests.common import TestMultiChannelCommon
from odoo.tests import common
# from odoo.exceptions import Warning
# coding: utf-8
from odoo.tests import tagged
# from odoo.addons.odoo_multi_channel_sale.tests.test_connections import TestConnectionMultichannel
# from odoo.addons.odoo_multi_channel_sale.tests.test_connections import TestMultichannelConnection


# This test should only be executed after all modules have been installed.

@tagged('post_install', '-at_install')
class TestMappingMultichannel(TestMultiChannelCommon):

    def test_category_mappings(self):

        categ_response_A = self.category_feed_A.with_context(get_mapping_ids=True, test_channel=True).import_items()

        # getting category mapping from response of  feed evalaution
        categ_mapping_A = (categ_response_A.get('update_ids') + categ_response_A.get('create_ids'))[0]

        # To check whether product mapping is created or not
        self.assertTrue(categ_mapping_A, msg="Catgeory mapping should be created at odoo after evaluation of feed")

        # To check whether category_mapping created with same store_id as present in feed , or not.
        self.assertEqual(self.category_feed_A.store_id, categ_mapping_A.store_category_id, msg="store_id of category_feed  and category_mapping should be same")

        # To check whether category_mapping and category_feed  have same leaf_structure, or not.
        self.assertEqual(self.category_feed_A.leaf_category, categ_mapping_A.leaf_category, msg="category_feed  and category_mapping should have same leaf structure")

        # To check whether category_mapping and category_feed  have same leaf_structure, or not.
        self.assertEqual(categ_mapping_A.odoo_category_id, categ_mapping_A.category_name.id, msg="Id of created_category  and odoo_ccategory_id of mapping should be same")

        # To check whether category_mapping and category_feed  have same leaf_structure, or not.
        self.assertEqual(categ_mapping_A.channel_id.id, categ_mapping_A.channel_id.id, msg="Id of created_category  and odoo_ccategory_id of mapping should be same")

    def test_product_mappings(self):
        product_template_response_A = self.product_feed_A.with_context(get_mapping_ids=True, test_channel=True).import_items()
        if (product_template_response_A.get('update_ids') + product_template_response_A.get('create_ids')):
            product_template_mapping_A = (product_template_response_A.get('update_ids') + product_template_response_A.get('create_ids'))[0]

        # To check whether product mapping is created or not
        self.assertTrue(product_template_mapping_A, msg="Product template mapping should be created at odoo after evaluation of feed")

        product_template_response_B = self.product_feed_B.with_context(get_mapping_ids=True, test_channel=True).import_items()
        product_template_mapping_B = (product_template_response_B.get('update_ids') + product_template_response_B.get('create_ids'))[0]

        # product template test cases ###################################################
        # To check whether product_template_mapping created with same store_id as present in feed , or not.
        self.assertEqual(self.product_feed_A.store_id, product_template_mapping_A.store_product_id, msg="store_id of product_feed  and product_template_mapping should be same")

        # To check whether product_template_mapping mapping created with same default_code as present in feed , or not.
        self.assertEqual(self.product_feed_A.default_code, product_template_mapping_A.default_code, msg="default_code of product_feed  and product_template_mapping should be same")

        # To check whether product_template_mapping mapping created with same barcode as present in feed , or not.
        self.assertEqual(self.product_feed_A.barcode, product_template_mapping_A.barcode, msg="barcode of product_feed  and product_template_mapping should be same")

        # To check whether product_template_mapping mapping created with same channel_id as present in feed , or not.
        self.assertEqual(self.product_feed_A.channel_id.id, product_template_mapping_A.channel_id.id, msg="channel of product_feed  and product_template_mapping should be same")

        # To check whether in  product_template_mapping , odoo_product_id is same as  id of product created.
        self.assertEqual(int(product_template_mapping_A.odoo_template_id), product_template_mapping_A.template_name.id, msg="channel of product_feed  and product_template_mapping should be same")

        mapping_view_result = self.product_feed_A.with_context({
            'mapping_model': 'channel.template.mappings',
            'store_field': 'store_product_id',
        }).open_mapping_view()

        # To check whether in product_feed linked with right product template mapping .
        self.assertEqual(mapping_view_result.get('res_id'), product_template_mapping_A.id, msg="product feed should be linked with right product_template_mappings")

        # product test cases ###################################################
        # variable product###################
        product_mappings_A = self.env['channel.product.mappings'].search([
            ('channel_id', '=', self.channel.id),
            ('store_product_id', '=', self.product_feed_A.store_id)
        ])

        # To check whether product mapping is created or not
        self.assertTrue(product_mappings_A, msg="Product mapping should be created at odoo after evaluation of feed")

        # To check  whether store_product_id is same  as in product_template_mappings and product_mapping
        self.assertEqual(product_template_mapping_A.store_product_id, product_mappings_A[0].store_product_id, msg="store_product_id should be same in product_template and product_mappings")

        # To check In case of variable product length of feed_varinats in feeds and number of product mappings is same or not.
        self.assertEqual(len(self.product_feed_A.feed_variants), len(product_mappings_A), msg="length of feed_variant and length of product_mappings_A should be same")

        # To check whether product_mapping created with same store_id as present in product_feed_variant,or not.
        self.assertEqual(self.product_feed_A.feed_variants[0].store_id, product_mappings_A[0].store_variant_id, msg="store id of product varinant in product feed  and store_variant_id in product mapping should be same")
        # self.assertEqual(self.product_feed_A.feed_variants[1].store_id, product_mappings_A[1].store_variant_id, msg="store variant id of product varinant in product feed  and store_variant_id in product mapping should be same")

        # To check whether product_mapping created with same default_code as present in product_feed_variant,or not.
        self.assertEqual(self.product_feed_A.feed_variants[0].default_code, product_mappings_A[0].default_code, msg="default_code of product varinant in product feed  and default_code in product mapping should be same")

        # To check whether product_mapping created with same barcode as present in product_feed_variant,or not.
        self.assertEqual(self.product_feed_A.feed_variants[0].barcode, product_mappings_A[0].barcode, msg="barcode of product varinant in product feed  and barcode in product mapping should be same")

        # To check In case of valiable product length of feed_varinats in feeds and number of product mappings is same or not.
        self.assertEqual(len(self.product_feed_A.feed_variants), len(product_mappings_A), msg="length of feed_variant and length of product_mappings_A should be same")

        # test cases for attributes of products ########################################

        attribute_value_mapping = self.env['channel.attribute.value.mappings'].search([
            ('channel_id', '=', self.channel.id),
            ('store_attribute_value_id', '=', '2'),
            ('store_attribute_value_name', '=', 'M')
        ])

        odoo_attribute_value = attribute_value_mapping.attribute_value_name

        # To check Odoo_attibute_value_id of mapping and id of created atttibute value is same or not.
        self.assertEqual(odoo_attribute_value.id, attribute_value_mapping.odoo_attribute_value_id, msg="odoo_attribute_value_id of mapping and id of created odoo_attribute_value should be same")

        # To check attribute value mappings
        self.assertTrue(attribute_value_mapping, msg="attribute  value mappings should be created in case of variable product")

        attribute_mapping = self.env['channel.attribute.mappings'].search([
            ('channel_id', '=', self.channel.id),
            ('store_attribute_id', '=', '1'),
            ('store_attribute_name', '=', 'Size')
        ])
        odoo_attribute = attribute_mapping.attribute_name

        # To check attribute mappings
        self.assertTrue(attribute_mapping, msg="attribute mappings should be created in case of variable product")

        # To check Odoo_attibute and attribute_value is linked together or not
        self.assertEqual(odoo_attribute.id, attribute_mapping.odoo_attribute_id, msg="odoo_attribute_id of mapping and id of created odoo_attribute_value should be same")

        # To check  created Odoo_attibute and atttibute value is same or not.
        self.assertEqual(odoo_attribute.id, odoo_attribute_value.attribute_id.id, msg=" created odoo_attribute should be realeted to attribute value")

        # simple product###################
        product_mappings_B = self.env['channel.product.mappings'].search([
            ('channel_id', '=', self.channel.id),
            ('store_product_id', '=', self.product_feed_B.store_id)
        ])

        # To check In case of simple product length of feed_varinats in feeds is one less than number of mappings of product.
        self.assertEqual(len(product_mappings_B), 1, msg="length product mappings should be 1 in case of simple product")

        # To check whether in case of simple product_mapping store varinat id is right or not.
        self.assertEqual(product_mappings_B.store_variant_id, 'No Variants', msg="store variant id of product should be 'No Variants' in case of simple product")

    def test_order_mappings(self):

        order_response_A = self.test_order_feed_A.with_context(get_mapping_ids=True, test_channel=True).import_items()
        if (order_response_A.get('update_ids') + order_response_A.get('create_ids')):
            order_mapping = (order_response_A.get('update_ids') + order_response_A.get('create_ids'))[0]

        # To check whether order mapping is created or not
        self.assertTrue(order_mapping, msg="Order mapping should be created at odoo after evaluation of feed")

        # To check whether store_order_id is same  as store_id of order_feed
        self.assertEqual(order_mapping.store_order_id, self.test_order_feed_A.store_id, msg="store_order_id should bhi same as store_id of order feed")

        order_customer_mapping = self.env['channel.partner.mappings'].search([
            ('channel_id', '=', self.channel.id),
            ('store_customer_id', '=', self.test_order_feed_A.partner_id)
        ])
        # To check whether cusomer_mapping is created with order or not
        self.assertEqual(len(order_customer_mapping), 1, msg="customer mapping should be created")

        # To check whether order mapping created with same channel_id as present in feed or not.
        self.assertEqual(self.test_order_feed_A.channel_id.id, order_mapping.channel_id.id, msg="channel of order_feed  and order_mapping should be same")

        # test cases for taxes in order########################################
        tax_rate = eval(self.test_order_feed_A.line_ids.line_taxes)[0]['rate']
        tax_mappings = self.env['channel.account.mappings'].search(
            [
                ('channel_id', '=', self.channel.id),
                ('store_tax_value_id', '=', tax_rate)
            ])

        # To check whether tax mapping is created or not
        self.assertTrue(tax_mappings, msg="Mapping should be created if tax is present in order")

        # test cases for payment_method in order########################################
        odoo_journal = self.env['multi.channel.skeleton'].with_context(test_channel=True).CreatePaymentMethod(self.channel, self.test_order_feed_A.payment_method)
        payment_method = self.test_order_feed_A.payment_method
        payment_method_mappings = self.env['channel.account.journal.mappings'].search(
            [
                ('store_journal_name', '=', payment_method),
            ])

        # To check whether payment_method mapping is created or not
        self.assertTrue(payment_method_mappings, msg="Mapping of payment method should be created if payment_method  is present in order feed")

        # To check whether right short code of journal is mapped in mapping or not
        self.assertEqual(payment_method_mappings.journal_code, payment_method_mappings.odoo_journal.code, msg="journal code should be same as short code of created odoo journal")

        # test cases for currency mapping in order########################################
        currency_mapping = self.env['channel.pricelist.mappings'].search([
            ('store_currency_code', '=', self.test_order_feed_A.currency),
            ('channel_id', '=', self.channel.id),
        ])

        # To check whether currency mapping is created or not
        self.assertTrue(currency_mapping, msg="Mapping of currency should be created if currency is present in order feed")

        # To check whether currency mapping is created or not
        self.assertEqual(currency_mapping.odoo_pricelist_id.currency_id.id, currency_mapping.odoo_currency.id, msg="Mapping of currency should be created if currency is present in order feed")

        shipping_mapping_match = self.env['channel.shipping.mappings'].search([
            ('shipping_service', '=', self.test_order_feed_A.carrier_id),
            ('channel_id', '=', self.channel.id),
        ])
        # To check whether currency mapping is created or not
        self.assertTrue(shipping_mapping_match, msg="Mapping of shipping should be created if shipping is present in order feed")

    def test_shipping_mappings(self):
        shipping_response_A = self.shipping_feeds_A.with_context(get_mapping_ids=True, test_channel=True).import_items()
        shipping_mapping = (shipping_response_A.get('update_ids') + shipping_response_A.get('create_ids'))[0]

        # To check whether shipping_mehothod mapping is created or not
        self.assertTrue(shipping_mapping, msg="Mapping of shipping should be created after evaluation of feed")

        # To check check whether is_international field in feed and mapping is same or not
        self.assertEqual(self.shipping_feeds_A.is_international, shipping_mapping.international_shipping, msg="value of is_international should be same as feed")

        # To check check whether store_id of feed in feed and  shipping_service_id of mapping is same or not
        self.assertEqual(self.shipping_feeds_A.store_id, shipping_mapping.shipping_service_id, msg="store_id in feed and shipping_service_id of mapping should be same ")

    def test_partner_mappings(self):
        partner_contact_response = self.partner_feed_record_contact.with_context(get_mapping_ids=True, test_channel=True).import_items()
        partner_invoice_response = self.partner_feed_record_invoice.with_context(get_mapping_ids=True, test_channel=True).import_items()
        partner_shpping_response = self.partner_feed_record_shipping.with_context(get_mapping_ids=True, test_channel=True).import_items()

        partner_contact_c = (partner_contact_response.get('update_ids') + partner_contact_response.get('create_ids'))[0]
        partner_invoice_i = (partner_invoice_response.get('update_ids') + partner_invoice_response.get('create_ids'))[0]
        partner_shpping_s = (partner_shpping_response.get('update_ids') + partner_shpping_response.get('create_ids'))[0]

        # To check whether created mapping have store_id as feed of partner
        self.assertEqual(self.partner_feed_record_contact.store_id, partner_contact_c.store_customer_id, msg="store_id of contact partner should be same in  feed and mapping")
        self.assertEqual(self.partner_feed_record_invoice.store_id, partner_invoice_i.store_customer_id, msg="store_id of invoice partner should be same in  feed and mapping")
        self.assertEqual(self.partner_feed_record_shipping.store_id, partner_shpping_s.store_customer_id, msg="store_id of shipping partner should be same in  feed and mapping")

        # To check whether created mapping have same type as feed of partner
        self.assertEqual(self.partner_feed_record_contact.type, partner_contact_c.type, msg="store_id of contact partner should be same in  feed and mapping")
        self.assertEqual(self.partner_feed_record_invoice.type, partner_invoice_i.type, msg="store_id of invoice partner should be same in  feed and mapping")
        self.assertEqual(self.partner_feed_record_shipping.type, partner_shpping_s.type, msg="store_id of shipping partner should be same in  feed and mapping")
