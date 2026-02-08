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
from datetime import datetime
# from odoo.addons.odoo_multi_channel_sale.tests.test_connections import TestConnectionMultichannel


# This test should only be executed after all modules have been installed.
@tagged('post_install', '-at_install')
class TestFeedMultichannel(TestMultiChannelCommon):

    def test_category_feed(self):

        # To check whether After creating  Category feed right parant_id is linked or not.
        self.assertEqual(int(self.category_feed_B.parent_id), int(self.category_feed_A.store_id), msg="Category Parent_id Not Matched")

        # To check whether state of category feed before evalaution.
        self.assertEqual(self.category_feed_A.state, 'draft', msg="category feed should be in Draft state utill it is not evalaued")

        # evaluating feed
        response_A = self.category_feed_A.with_context(get_mapping_ids=True, test_channel=True).import_items()
        response_B = self.category_feed_B.with_context(get_mapping_ids=True, test_channel=True).import_items()

        # To check whether state of category feed after evalaution.
        self.assertEqual(self.category_feed_A.state, 'done', msg="category feed should be in Done state  After evaluation")
        self.assertEqual(self.category_feed_B.state, 'done', msg="category feed should be in Done state  After evaluation")

        # getting mapping from response from  feed evalaution
        catgory_mapping_A = (response_A.get('update_ids') + response_A.get('create_ids'))[0]
        catgory_mapping_B = (response_B.get('update_ids') + response_B.get('create_ids'))[0]

        product_category_A = catgory_mapping_A.category_name
        product_category_B = catgory_mapping_B.category_name

        # To check whether name of created category at odoo have same name as categrory feed
        self.assertEqual(product_category_A.name, self.category_feed_A.name, msg="Name of Imported Category is not same as imported in feed")
        self.assertEqual(product_category_B.name, self.category_feed_B.name, msg="Name of Imported Category is not same as imported in feed")

        # To check whether a category is linked with with right parant or not after evalaution
        self.assertEqual(product_category_B.parent_id.id, product_category_A.id, msg="After Category evalaution Category is not created with right parent at Odoo end")

    def test_product_feeds(self):

        # To check whether state of product feed before evalaution.
        self.assertEqual(self.product_feed_A.state, 'draft', msg="product feed should be in Draft state utill it is not evalaued")
        self.assertEqual(self.product_feed_B.state, 'draft', msg="product feed should be in Draft state utill it is not evalaued")

        # evaluating product feed
        product_template_response_A = self.product_feed_A.with_context(get_mapping_ids=True, test_channel=True).import_items()
        product_template_response_B = self.product_feed_B.with_context(get_mapping_ids=True, test_channel=True).import_items()

        # To check whether state of category feed after evalaution.
        self.assertEqual(self.product_feed_A.state, 'done', msg="Product feed should be in Done state  After evaluation")
        self.assertEqual(self.product_feed_B.state, 'done', msg="Product feed should be in Done state  After evaluation")

        # getting product template mapping from response from  feed evalaution
        product_template_mapping_A = (product_template_response_A.get('update_ids') + product_template_response_A.get('create_ids'))[0]
        product_template_mapping_B = (product_template_response_B.get('update_ids') + product_template_response_B.get('create_ids'))[0]

        # -- Variable Product --###########################
        # product template  and  product variant
        product_template_A = product_template_mapping_A.template_name
        product_product_A_A = product_template_A.product_variant_ids[0]
        product_product_A_B = product_template_A.product_variant_ids[1]

        # To check whether product created at odoo end have same name as product feed.
        self.assertEqual(product_template_A.name, self.product_feed_A.name, msg="Name of product created at odoo end and product feed must be same")

        # product feed varinats
        product_feed_variant_A = self.product_feed_A.feed_variants[0]
        product_feed_variant_B = self.product_feed_A.feed_variants[1]

        # To check whether same number of variants are created after product is created.
        self.assertEqual(len(product_template_A.product_variant_ids), len(self.product_feed_A.feed_variants), msg="Variants should be same as import in product feed")

        # To check whether product_variant created at odoo end  and product variant feed  have same Internal Referenece or not .
        self.assertEqual(product_product_A_A.default_code, product_feed_variant_A.default_code, msg="Default code should be same as import in product feed variant")
        self.assertEqual(product_product_A_B.default_code, product_feed_variant_B.default_code, msg="Default code should be same as import in product feed variant")

        # To check whether product_variant created at odoo end and  product variant feed  have same Barcode or not .
        self.assertEqual(product_product_A_A.barcode, product_feed_variant_A.barcode, msg="Barcode should be same as import in product feed variant")
        self.assertEqual(product_product_A_B.barcode, product_feed_variant_B.barcode, msg="Barcode should be same as import in product feed variant")

        # To check whether product created at odoo end have attribute_line_ids persent in template or not .
        self.assertTrue(product_template_A.attribute_line_ids, msg="Attribute_line_ids should be present in product template if in Product feed product have variants")

        # -- Simple Product ---#################
        product_template_B = product_template_mapping_B.template_name

        # To check whether product created at odoo end have same name as product feed.
        self.assertEqual(product_template_B.name, self.product_feed_B.name, msg="Name of product created at odoo end and product feed must be same")

        # To check whether product template created at odoo end  and product feed  have same Internal Referenece or not .
        self.assertEqual(product_template_B.default_code, self.product_feed_B.default_code, msg="Default code should be same as import in product feed")

        # To check whether product template created at odoo end  and product feed  have same Internal Referenece or not .
        self.assertEqual(product_template_B.barcode, self.product_feed_B.barcode, msg="Barcode code should be same as import in product feed")

        # To check whether product created at odoo end have attribute_line_ids persent in template or not .
        self.assertFalse(product_template_B.attribute_line_ids, msg="Attribute_line_ids should be present in product template if in Product feed product have variants")

        # To check whether created product have channel_category_ids or not.
        self.assertTrue(product_template_B.channel_category_ids, msg="product should have extra_category_ids if extra_category_ids is present in feeds")

    def test_partner_feeds(self):

        # To check whether state of created feed is in darft or not .
        self.assertEqual(self.partner_feed_record_contact.state, 'draft', msg="state of conatct feed should be in draft before evaluation")
        self.assertEqual(self.partner_feed_record_invoice.state, 'draft', msg="state of invoice feed should be in draft before evaluation")
        self.assertEqual(self.partner_feed_record_shipping.state, 'draft', msg="state of shipping feed should be in draft before evaluation")

        # To check whether parent of invoice,shipping linked with right parent or not .
        self.assertEqual(self.partner_feed_record_invoice.parent_id, self.partner_feed_record_contact.store_id, msg="Parent of Invoice feed not matched")
        self.assertEqual(self.partner_feed_record_shipping.parent_id, self.partner_feed_record_contact.store_id, msg="Parent of Shippinf feed not matched")

        # evaluating partner feeds(contact,invoice,delivery)
        partner_contact_response = self.partner_feed_record_contact.with_context(get_mapping_ids=True, test_channel=True).import_items()
        partner_invoice_response = self.partner_feed_record_invoice.with_context(get_mapping_ids=True, test_channel=True).import_items()
        partner_shpping_response = self.partner_feed_record_shipping.with_context(get_mapping_ids=True, test_channel=True).import_items()

        # getting partner record mapping from response from  feed evalaution
        partner_contact = (partner_contact_response.get('update_ids') + partner_contact_response.get('create_ids'))[0].odoo_partner
        partner_invoice = (partner_invoice_response.get('update_ids') + partner_invoice_response.get('create_ids'))[0].odoo_partner
        partner_shpping = (partner_shpping_response.get('update_ids') + partner_shpping_response.get('create_ids'))[0].odoo_partner

        # To check whether state of partner feed after evalaution.
        self.assertEqual(self.partner_feed_record_contact.state, 'done', msg="partner contact feed should be in Done state  After evaluation")
        self.assertEqual(self.partner_feed_record_invoice.state, 'done', msg="partner invoice feed should be in Done state  After evaluation")
        self.assertEqual(self.partner_feed_record_shipping.state, 'done', msg="partner shipping feed should be in Done state  After evaluation")

        # To check whether name of partner_records and partner_feed records are same or not.
        self.assertEqual(partner_contact.name, self.partner_feed_record_contact.name + " " + self.partner_feed_record_contact.last_name, msg="name of partner_contact_feed and created partner should be same")
        self.assertEqual(partner_invoice.name, self.partner_feed_record_invoice.name + " " + self.partner_feed_record_invoice.last_name, msg="name of partner_invoice_feed and created partner should be same")
        self.assertEqual(partner_shpping.name, self.partner_feed_record_shipping.name + " " + self.partner_feed_record_shipping.last_name, msg="name of partner_shipping_feed and created partner should be same")

        # To check whether type of partner_records and partner_feed records are same or not.
        self.assertEqual(partner_contact.type, self.partner_feed_record_contact.type, msg="type of partner_contact_feed and created partner should be same")
        self.assertEqual(partner_invoice.type, self.partner_feed_record_invoice.type, msg="type of partner_invoice_feed and created partner should be same")
        self.assertEqual(partner_shpping.type, self.partner_feed_record_shipping.type, msg="type of partner_shipping_feed and created partner should be same")

        # To check whether created partners(invoice,delivery) is linked with right conatct or not.
        self.assertEqual(partner_invoice.parent_id.id, partner_contact.id, msg="created contact partner should be parant of invoice partner")
        self.assertEqual(partner_shpping.parent_id.id, partner_contact.id, msg="created contact partner should be parant of delivery partner")

    def test_order_feed(self):

        # To check whether state of order feed before evalaution.
        self.assertEqual(self.test_order_feed_A.state, 'draft', msg="order feed should be in Draft state utill it is not evalaued")

        # evaluating order feed
        order_response_A = self.test_order_feed_A.with_context(get_mapping_ids=True, test_channel=True).import_items()

        # To check whether state of order feed after evalaution.
        self.assertEqual(self.test_order_feed_A.state, 'done', msg="order feed should be in Done state  After evaluation")

        order_mapping = (order_response_A.get('update_ids') + order_response_A.get('create_ids'))[0]
        odoo_order_A = order_mapping.order_name

        # To check whether state of creted order at odoo end.
        self.assertEqual(odoo_order_A.state, 'draft', msg="odoo order should be draft state")

        # To check that order_line is created In odoo order
        self.assertTrue(odoo_order_A.order_line, msg="If product is present in order_line then it should be created at odoo end")

        # To check whether product created in order line it same as imported order_line_feed or not.
        feed_order_product_store_id = self.test_order_feed_A.line_ids.line_product_id
        created_order_product_store_id = self.env['channel.product.mappings'].search([
            ('product_name', '=', odoo_order_A.order_line.product_id.id),
            ('channel_id', '=', self.channel.id),
        ]).store_product_id
        self.assertEqual(created_order_product_store_id, feed_order_product_store_id, msg="same product should be presant in orderline of created order as present in feed")

        # To check whether product created in order line it same qty as imported order_line_feed or not.
        feed_order_product_quantity = self.test_order_feed_A.line_ids.line_product_uom_qty
        created_ordered_product_quantity = odoo_order_A.order_line.product_uom_qty
        self.assertEqual(feed_order_product_quantity, str(int(created_ordered_product_quantity)), msg="same product qunatity should be presant in orderline of created order as present in feed")

        # To test whether price of item present in line item is same as price of line_item in feed
        self.assertEqual(odoo_order_A.order_line.price_unit,
                         float(self.test_order_feed_A.line_ids.line_price_unit), msg="unit price of  line_item should be same as quantity present in order_feed")

        # To check whether date of order is same as present at feed or not
        self.assertEqual(odoo_order_A.date_order,
                         datetime.strptime(self.test_order_feed_A.confirmation_date, '%Y-%m-%d %H:%M:%S'), msg="order date in order should be same as order_feed order date")

        # To check whether amount in tax of line_item is same as tax ratepresent in line_item of  feed or not
        self.assertEqual(odoo_order_A.order_line.tax_id.amount,
                         eval(self.test_order_feed_A.line_ids.line_taxes)[0].get('rate'), msg="tax rate should be same in line_item as imported in order feed")

        # confirm Order ##################################
        order_confirm = self.env['multi.channel.skeleton']._ConfirmOdooOrder(odoo_order_A, date_invoice=self.test_order_feed_A.date_invoice, confirmation_date=self.test_order_feed_A.confirmation_date)
        # To check that confirmation of order is successful or not
        self.assertTrue(order_confirm.get('status'), msg="order confirmation should be sucessful....")

        # Invoice ########################################

        odoo_journal = self.env['multi.channel.skeleton'].with_context(test_channel=True).CreatePaymentMethod(self.channel, self.test_order_feed_A.payment_method)

        # To check whether odoo_jaurnal  is created/present  after CreatePaymentMethod beiing called
        self.assertTrue(odoo_journal.get('journal_id'), msg="journal_id should be created after calling CreatePaymentMethod   ....")

        # Creating Draft invoice#########
        order_invoice = self.env['multi.channel.skeleton'].create_order_invoice(odoo_order_A)

        # To check whether invoice is created or not
        self.assertTrue(order_invoice.get('invoice_id'), msg="Invoice should be created after create_order_invoice() being called ....")

        # To check whether status of creation of invoice is True or not
        self.assertTrue(order_invoice.get('status'), msg="status should be True after creation of invoice ....")

        # To check whether state of invoice is Draft or not>>>>>>
        self.assertEqual(order_invoice.get('invoice_id').state, 'draft', msg="Invoice should be draft state ....")

        # Paid Invoice ##########
        data = {
            'order_id': odoo_order_A.id,
            'journal_id': odoo_journal.get('journal_id'),
            'channel_id': self.channel,
            'order_state': 'sale',
            'invoice_state': 'paid',
            'date_invoice': self.test_order_feed_A.date_invoice
        }
        paid_invoice = self.env['multi.channel.skeleton'].SetOrderPaid(data)

        # To check whether status of paid invoice is True or not
        self.assertTrue(paid_invoice.get('status'), msg="status should be True after invoice is paid ....")

        # To check whether state of invoice is Draft or not>>>>>>
        self.assertEqual(order_invoice.get('invoice_id').state, 'posted', msg="Invoice should be Paid state ....")

        # To check whether quantity of product is same as present in order feed or not
        self.assertEqual(int(odoo_order_A.order_line.qty_invoiced),
                         int(self.test_order_feed_A.line_ids.line_product_uom_qty), msg="qunatity of invoice line should be same as quantity present in order_feed")

        # Shipment ########################################
        ship_result = self.env['multi.channel.skeleton'].with_context(test_channel=True).set_order_shipped(odoo_order_A.id, date_invoice=self.test_order_feed_A.date_invoice, confirmation_date=self.test_order_feed_A.confirmation_date)

        # To check that shipment of order is successful or not
        self.assertTrue(ship_result.get('status'), msg="shipment should be sucessful....")

        # To check whether generated pricking have same qunatity in qty_done in product as orderline in feed or not after shipment
        self.assertEqual(int(odoo_order_A.order_line.qty_delivered), int(self.test_order_feed_A.line_ids.line_product_uom_qty), msg="shippied qunatity of order product should be same after shipment of order")

        # To check whether partner with order , imported or not
        self.assertTrue(odoo_order_A.partner_id.channel_mapping_ids, msg="parner should be imported with order")

    def test_shpping_feeds(self):

        # To check whether state of shippig feed before evalaution.
        self.assertEqual(self.shipping_feeds_A.state, 'draft', msg="shipping feed should be in Draft state utill it is not evalaued")

        # evaluating shipping feed
        shipping_response_A = self.shipping_feeds_A.with_context(get_mapping_ids=True, test_channel=True).import_items()

        # To check whether state of shipping feed after evalaution.
        self.assertEqual(self.shipping_feeds_A.state, 'done', msg="shipping feed should be in Done state  After evaluation")

        shipping_mapping = (shipping_response_A.get('update_ids') + shipping_response_A.get('create_ids'))[0]
        odoo_shipping_carrier_A = shipping_mapping.odoo_shipping_carrier

        # To check whether created odoo shipping carrier have same name as shipping feed.
        self.assertEqual(self.shipping_feeds_A.name, odoo_shipping_carrier_A.name, msg="name of created shipping carrier should be same as shpping feed name")

        # To check whether created odoo shipping carrier same deivery product as configured in channel or not.
        self.assertEqual(odoo_shipping_carrier_A.product_id.id, self.channel.delivery_product_id.id, msg="delivery product of created shipping carrier should be same as configured in channel confiuration")

        # To check whether created odoo shipping carrier same deivery product with service type or not.
        self.assertEqual(odoo_shipping_carrier_A.product_id.type, 'service', msg="In created shipping carrier delivery product should be service type product")
