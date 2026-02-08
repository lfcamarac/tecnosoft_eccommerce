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

# This test should only be executed after all modules have been installed.
@tagged('post_install', '-at_install')
class TestMultichannelConnection(TestMultiChannelCommon):

    def test_connections(self):

        # To test state of channel if connection of channel not configured
        self.assertEqual(self.channel.state, 'draft', 'state of channel should be in draft if connnetion is not configured')

        # test connection
        self.channel.test_connection()

        # To test if connection of channel not configured correctly then state should be in 'error' state
        self.assertNotEqual(self.channel.state, 'error', msg="Connection with channel is not successul")

        # To test if connection of channel configured correctly then state should be in 'validate' state
        self.assertEqual(self.channel.state, 'validate', msg="Channel State should be validated after connection if succeessful")
