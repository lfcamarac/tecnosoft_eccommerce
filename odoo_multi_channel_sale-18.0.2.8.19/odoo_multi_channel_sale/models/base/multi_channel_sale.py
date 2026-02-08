# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
import binascii
from logging import getLogger
import requests
import pytz
from dateutil import parser
from datetime import datetime, timedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from ...tools import ReverseDict
_logger = getLogger(__name__)



class MultiChannelSale(models.Model):
    _name = 'multi.channel.sale'
    _description = 'Multi Channel Sale'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    import_order_cron = fields.Boolean("Import Orders")
    import_product_cron = fields.Boolean("Import Products")
    import_partner_cron = fields.Boolean("Import Customers")
    import_category_cron = fields.Boolean("Import Categories")

    channel_stock_action = fields.Selection([
        ('qoh', 'Quantity on hand'),
        ('free_qty', 'Free Quantity'),
        ('fq', 'Forecast Quantity')
    ],
        default='qoh',
        string='Stock Management',
        help="Manage Stock")
    order_ecomm_sequence = fields.Boolean(help="If enabled, the orders will get created with E-commerce Sequnence at the Odoo end")
    
    sync_customer_company = fields.Boolean('Customer Company')

    clear_sync_history = fields.Boolean('Clear Sync History')
    clear_done_feed = fields.Boolean('Clear Done Feed')

    # @api.model
    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if 'install_mode' in self._context or 'create_order_states' in self._context:
            res._on_change_channel()
        channels = self.get_core_feature_compatible_channels()
        return res

    url = fields.Char("URL", tracking=True)
    email = fields.Char(string='Api User', tracking=True)
    api_key = fields.Char("Password")

    def test_connection(self):
        self.ensure_one()
        if hasattr(self, 'connect_%s' % self.channel):
            res, msg = getattr(self, 'connect_%s' % self.channel)()
            self.state = 'validate' if res else 'error'
            return self.display_message(msg)
        elif hasattr(self, 'test_%s_connection' % self.channel):
            _logger.warning(
                'Error in use of MultiChannelSale class: '
                'use of test_connection function to establish connection to Channel.'
            )
            return getattr(self, 'test_%s_connection' % self.channel)()
        else:
            return self.display_message('Connection protocol missing.')

    @api.onchange('channel')
    def _on_change_channel(self):
        if self.channel:
            if self.order_state_ids:
                rec = self.env['channel.order.states'].search([('channel_id', '=', self._origin.id), ('channel_name', '=', self.channel)])

                if rec:
                    self.order_state_ids = [(6, 0, rec.ids)]
                else:
                    self.order_state_ids = [(5, 0, 0)]
                    if hasattr(self, '%s_default_order_state' % self.channel):
                        """
                        Add default values to order state ids
                        @field channel_state: state of the channel
                        @field default_order_state: True or False
                        @field odoo_create_invoice: True or False
                        @field odoo_ship_order: True or False
                        @field odoo_order_state: draft or shipped or done etc.
                        @field odoo_set_invoice_state: paid or open
                        @return: A list dictionarys of the default values
                        """
                        values = getattr(self, '%s_default_order_state' % self.channel)()
                        rec_val = []
                        for rec in values:
                            rec_val.append((0, 0, rec))
                        self.order_state_ids = rec_val
            else:
                if hasattr(self, '%s_default_order_state' % self.channel):
                    """
                    Add default values to order state ids
                    @field channel_state: state of the channel
                    @field default_order_state: True or False
                    @field odoo_create_invoice: True or False
                    @field odoo_ship_order: True or False
                    @field odoo_order_state: draft or shipped or done etc.
                    @field odoo_set_invoice_state: paid or open
                    @return: A list dictionarys of the default values
                    """
                    values = getattr(self, '%s_default_order_state' % self.channel)()
                    rec_val = []
                    for rec in values:
                        rec_val.append((0, 0, rec))
                    self.order_state_ids = rec_val

    def set_to_draft(self):
        self.state = 'draft'

    def open_mapping_view(self):
        self.ensure_one()
        res_model = self._context.get('mapping_model')
        mapping_ids = self.env[res_model].search([('channel_id', '=', self.id)]).ids
        return {
            'name': ('Mapping'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': res_model,
            'view_id': False,
            'domain': [('id', 'in', mapping_ids)],
            'target': 'current',
        }

    def open_record_view(self):
        self.ensure_one()
        res_model = self._context.get('mapping_model')
        domain = [('channel_id', '=', self.id)]
        erp_ids = self.env[res_model].search(domain).mapped(self._context.get('odoo_mapping_field'))
        MAPPINGMODEL = {
            'product.product': 'channel.product.mappings',
            'product.template': 'channel.template.mappings',
            'res.partner': 'channel.partner.mappings',
            'product.category': 'channel.category.mappings',
            'sale.order': 'channel.order.mappings',
        }
        erp_model = ReverseDict(MAPPINGMODEL).get(res_model)
        domain = [('id', 'in', erp_ids)]
        if erp_model == 'res.partner':
            domain.append(('parent_id', '=', False))
        return {
            'name': ('Record'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': erp_model,
            'view_id': False,
            'domain': domain,
            'target': 'current',
        }

    def open_cron_views(self):
        cron_view_id = self._context.get('cron_view_id')
        view_id = self.env.ref(f'odoo_multi_channel_sale.{cron_view_id}').id
        return {
			'name': 'Open Cron View',
			'type': 'ir.actions.act_window',
			'view_mode': 'form',
			'res_model': 'ir.cron',
			'res_id': view_id,
			'target': 'current',
        }

    def open_clear_data_views(self):
        cron_view_id = self.env.context.get('cron_view_id')
        view_id = self.env.ref(f'odoo_multi_channel_sale.{cron_view_id}').id
        return {
			'name': 'Open Cron View',
			'type': 'ir.actions.act_window',
			'view_mode': 'form',
			'res_model': 'ir.cron',
			'res_id': view_id,
			'target': 'current',
        }

    def _get_count(self):
        for rec in self:
            rec.write({
                'channel_products': len(self.env['channel.template.mappings']._search([('channel_id', '=', rec.id)])),
                'channel_categories': len(self.env['channel.category.mappings']._search([('channel_id', '=', rec.id)])),
                'channel_orders': len(self.env['channel.order.mappings']._search([('channel_id', '=', rec.id)])),
                'channel_customers': len(self.env['channel.partner.mappings']._search([('channel_id', '=', rec.id), ('odoo_partner.parent_id', '=', False)])),
            })

    active = fields.Boolean(default=True)
    color_index = fields.Integer(string='Color Index')

    def set_info_urls(self):
        for instance in self:
            url_info = self.get_info_urls().get(instance.channel, {})
            instance.write({
                'blog_url': url_info.get('blog', 'https://webkul.com/blog/odoo-multi-channel-sale/'),
                'store_url': url_info.get('store', 'https://store.webkul.com/Odoo-Multi-Channel-Sale.html')
            })

    @api.model
    def get_channel_time_zone(self):
        return [(time_zone, time_zone) for time_zone in pytz.all_timezones]

    channel = fields.Selection(selection='get_channel', required=True, inverse=set_info_urls, tracking=True)
    name = fields.Char('Name', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validate', 'Validate'),
        ('error', 'Error')
    ], default='draft', tracking=True)
    color = fields.Char(default='#000000')
    image = fields.Image(max_width=256, max_height=256)
    blog_url = fields.Char()
    store_url = fields.Char()
    debug = fields.Selection([
        ('enable', 'Enable'),
        ('disable', 'Disable')
    ], default='enable', required=True)
    wk_time_zone = fields.Selection('get_channel_time_zone', string='Time Zone', required=True, default='UTC')

    environment = fields.Selection(
        selection=[
            ('production', 'Production Server'),
            ('sandbox', 'Testing(Sandbox) Server')
        ],
        string='Environment',
        default='sandbox',
        help="""Set environment to  production while using live credentials."""
    )
    is_child_store = fields.Boolean(string='Is Child-Store')
    default_store_id = fields.Many2one(
        comodel_name='multi.channel.sale',
        string='Parent Store',
        help=("""***While using multi store***\n
            Select the default store/parent store
            from where the order and partner will imported for this child store.
            """),
    )
    sku_sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        string='Sequence For SKU',
        check_company=True,
        help="""Default sequence used as sku/default code for product(in case product not have sku/default code).""",
    )
    language_id = fields.Many2one(
        comodel_name='res.lang',
        default=lambda self: self.env['res.lang'].search([], limit=1),
        help="""The language used over e-commerce store/marketplace.""",
    )

    pricelist_id = fields.Many2one('channel.pricelist.mappings', 'Pricelist Mapping', tracking=True)

    pricelist_name = fields.Many2one(
        comodel_name='product.pricelist',
        string='Default Pricelist',
        check_company=True,
        default=lambda self: self.env['product.pricelist'].search([('company_id', '=', self.env.company.id)], limit=1),
        help="""Select the same currency of pricelist used  over e-commerce store/marketplace.""",
    )
    default_category_id = fields.Many2one(
        comodel_name='product.category',
        string='Category',
        default=lambda self: self.env['product.category'].search([], limit=1),
        help="""Default category used as product internal category for imported products.""",
        tracking=True
    )
    channel_default_product_categ_id = fields.Many2one(
        comodel_name='channel.category.mappings',
        string='Channel Category'
    )
    default_tax_type = fields.Selection(
        selection=[
            ('include', 'Include In Price'),
            ('exclude', 'Exclude In Price')
        ],
        string='Tax Type',
        default='exclude',
        required=True
    )
    delivery_product_id = fields.Many2one(
        comodel_name='product.product',
        string='Delivery Product',
        domain="[('type', '=', 'service')]",
        check_company=True,
        default=lambda self: self.env.ref('odoo_multi_channel_sale.delivery_product').id,
        help="""Delivery product used in sale order line.""",
    )
    discount_product_id = fields.Many2one(
        comodel_name='product.product',
        string='Discount Product',
        domain="[('type', '=', 'service')]",
        check_company=True,
        default=lambda self: self.env.ref('odoo_multi_channel_sale.discount_product').id,
        help="""Discount product used in sale order line.""",
    )
    other_charge_product_id = fields.Many2one(
        comodel_name='product.product',
        string='Other Charge Product',
        # default=lambda self: self.env.ref('odoo_multi_channel_sale.other_charge_product').id,
        domain=[('type', '=', 'service')],
        help="""Other charge product used in sale order line.""",
    )
    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Warehouse',
        default=lambda self: self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1),
        help='Warehouse used for imported product.',
        check_company=True,
        tracking=True
    )
    location_id = fields.Many2one(
        related='warehouse_id.lot_stock_id',
        string='Stock Location',
        domain = "[('company_id', '=?', company_id)]",
        help='Stock Location used for imported product.',
        readonly= True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.company.id,
        string='Company Id',
        tracking=True
    )
    crm_team_id = fields.Many2one(
        comodel_name='crm.team',
        string='Sales Team',
        check_company=True,
        default=lambda self: self.env['crm.team'].search([('company_id', '=', self.env.company.id)], limit=1),
        help='Sales Team used for imported order.',
    )
    payment_term_id = fields.Many2one(
        'account.payment.term',
        string="Ecommerce Payment Term",
        check_company=True,
        help="""Default Payment Term Used In Sale Order.""")
    sales_person_id = fields.Many2one(
        'res.users',
        string="Sales Person",
        check_company=True,
        help="""Default Sales Person Used In Sale Order.""")

    utm_campaign_id = fields.Many2one(
        'utm.campaign',
        string="UTM Campaign",
        check_company=True,
        help="""Default UTM Campaign Used In Sale Order.""")
    utm_medium_id = fields.Many2one(
        'utm.medium',
        string="UTM Medium",
        help="""Default UTM Medium Used In Sale Order.""")
    utm_source_id = fields.Many2one(
        'utm.source',
        string="UTM Source",
        help="""Default UTM Source Used In Sale Order.""")

    order_state_ids = fields.One2many(
        comodel_name='channel.order.states',
        inverse_name='channel_id',
        string='Default Odoo Order States',
        help='Imported order will process in odoo on basis of these state mappings.',
        copy=True,
    )

    feed = fields.Selection([
        ('all', 'For All Models'),
        ('order', 'For Order Only'),
    ], default='all', required=True)

    auto_evaluate_feed = fields.Boolean(
        string='Auto Evaluate Feed',
        default=1,
        help='Auto Evaluate Feed Just After Import.',
    )
    auto_sync_stock = fields.Boolean(
        string='Auto Sync Stock',
        help='Enable this for real time stock sync over channel.',
        tracking=True
    )

    sync_cancel = fields.Boolean(
        string='Cancel Status',
        help='Enable for cancel status at E-commerce',
        tracking=True
    )
    sync_invoice = fields.Boolean(
        string='Invoice Status',
        help='Enable for update invoice status at E-commerce',
        tracking=True
    )
    sync_shipment = fields.Boolean(
        string='Shipment Status',
        help='Enable for update shipment status at E-commerce',
        tracking=True
    )

    import_order_date = fields.Datetime(
        string='Order Imported',
        help=("""A date used for selecting orders created after (or at) a specified time.""")
    )

    update_order_date = fields.Datetime(
        string='Order Updated',
        help=("""A date used for selecting orders that were last updated after (or at) a specified time.
            An update is defined as any change in order status,includes updates made by the seller.""")
    )

    import_product_date = fields.Datetime(string='Product Imported', help="A date used for selecting products created after (or at) a specified time.")
    update_product_date = fields.Datetime(string='Product Updated', help="A date used for selecting products updated after (or at) a specified time.")
    update_product_price = fields.Boolean(string='Update Price')
    update_product_stock = fields.Boolean(string='Update Stock')
    update_product_image = fields.Boolean(string='Update Image')

    import_customer_date = fields.Datetime(string='Customer Imported', help="A date used for selecting customers created after (or at) a specified time.")
    update_customer_date = fields.Datetime(string='Customer Updated', help="A date used for selecting customer updated after (or at) a specified time.")
    use_api_limit = fields.Boolean(string='Use API Limit', default=True)
    api_record_limit = fields.Integer(string='API Record Limit', default=100)
    total_record_limit = fields.Integer(string='Total Record Limit', default=0)

    channel_products = fields.Integer(compute='_get_count')
    channel_categories = fields.Integer(compute='_get_count')
    channel_orders = fields.Integer(compute='_get_count')
    channel_customers = fields.Integer(compute='_get_count')

    tax_on_discount_line = fields.Boolean(string='Tax on Discount Line')
    
    avoid_duplicity_global = fields.Boolean(compute="_compute_avoid_duplicity")
    
    def _compute_avoid_duplicity(self):
        self.avoid_duplicity_global = self.default_multi_channel_values().get('avoid_duplicity')
        
    @api.constrains('api_record_limit')
    def check_api_record_limit(self):
        if self.api_record_limit <= 0:
            raise Warning("""The api record limit should be postive.""")

    @api.model
    def set_channel_date(self, operation='import', record='product'):
        current_date = fields.Datetime.now()
        if operation == 'import':
            if record == 'order':
                self.import_order_date = current_date
            elif record == 'product':
                self.import_product_date = current_date
            elif record == 'customer':
                self.import_customer_date = current_date
        else:
            if record == 'order':
                self.update_order_date = current_date
            elif record == 'product':
                self.update_product_date = current_date
            elif record == 'customer':
                self.update_customer_date = current_date
        return True

    def toggle_enviroment_value(self):
        production = self.filtered(
            lambda channel: channel.environment == 'production')
        production.write({'environment': 'sandbox'})
        (self - production).write({'environment': 'production'})
        return True

    def toggle_debug_value(self):
        enable = self.filtered(lambda channel: channel.debug == 'enable')
        enable.write({'debug': 'disable'})
        (self - enable).write({'debug': 'enable'})
        return True

    def toggle_active_value(self):
        for record in self:
            record.write({'active': not record.active})
        return True

    @api.model
    def om_format_date(self, date_string):
        timezone = self.wk_time_zone
        om_date_time = None
        message = ''
        try:
            if date_string:
                om_date_time = pytz.timezone(timezone).localize(parser.parse(date_string, ignoretz=True)).astimezone(pytz.utc).replace(tzinfo=None)
        except Exception as e:
            message += '%r' % e
        return dict(
            message=message,
            om_date_time=om_date_time
        )

    @api.model
    def create_model_objects(self, model_name, vals, **kwargs):
        """
            model_name:'res.partner'
            vals:[{'name':'demo','type':'customer'},{'name':'portal':'type':'contact'}]
        """
        message = ''
        data = None
        try:
            ObjModel = self.env[model_name]
            data = self.env[model_name]
            for val in vals:
                if kwargs.get('extra_val'):
                    val.update(kwargs.get('extra_val'))
                match = False
                if val.get('store_id'):
                    obj = ObjModel.search([('store_id', '=', val.get('store_id'))], limit=1)
                    if obj:
                        obj.write(val)
                        data += obj
                        match = True
                if not match:
                    data += ObjModel.create(val)
        except Exception as e:
            _logger.error("#1CreateModelObject Error  \n %r" % (e))
            message += "%r" % (e)
        return dict(
            data=data,
            message=message,
        )

    @api.model
    def create_product(self, name, _type='service', vals=None):
        vals = vals or {}
        vals['name'] = name
        vals['type'] = _type
        return self.env['product.product'].create(vals)

    @api.model
    def create_tax(self, name, amount, amount_type='percent', price_include=False):
        raise NotImplementedError

    @api.model
    def _create_sync(self, vals):
        if self.debug == 'enable':
            nvals = vals.copy()
            channel_vals = self.get_channel_vals()
            nvals.update(channel_vals)
            return self.env['channel.synchronization'].create(nvals)
        return self.env['channel.synchronization']

    @api.model
    def default_multi_channel_values(self):
        return self.env['res.config.settings'].sudo().get_values()

    def open_website_url(self, url, name='Open Website URL'):
        self.ensure_one()
        return {
            'name': name,
            'url': url,
            'type': 'ir.actions.act_url',
            'target': 'new',
        }

    @staticmethod
    def read_website_image_url(image_url):
        data = None
        try:
            res = requests.get(image_url)
            if res.status_code == 200:
                data = binascii.b2a_base64((res.content))
        except Exception as e:
            _logger.error("#1ReadImageUrlError  \n %r" % (e))
        return data

    @api.model
    def set_order_by_status(self, channel_id, store_id,
                            status, order_state_ids, default_order_state,
                            payment_method=None):
        result = dict(
            order_match=None,
            message=''
        )
        order_match = channel_id.match_order_mappings(store_id)
        order_state_ids = order_state_ids.filtered(
            lambda state: state.channel_state == status)
        state = order_state_ids[0] if order_state_ids else default_order_state
        if order_match and order_match.order_name.state == 'draft' and (
                state.odoo_create_invoice or state.odoo_ship_order):
            result['message'] += self.env['multi.channel.skeleton']._SetOdooOrderState(
                order_match.order_name, channel_id, status, payment_method
            )
            result['order_match'] = order_match
        return result

    def unlink_feeds_mapping(self, channel_mapping_objs, model_obj):
        model = model_obj._name
        model_dict = {
            'product.category': {
                'mapping': 'channel.category.mappings',
                'local_field': 'odoo_category_id',
                'channel_field': 'store_category_id',
                'feed': 'category.feed'
            },
            'product.template': {
                'mapping': 'channel.template.mappings',
                'local_field': 'odoo_template_id',
                'channel_field': 'store_product_id',
                'feed': 'product.feed'
            },
            'product.product': {
                'mapping': 'channel.product.mappings',
                'local_field': 'erp_product_id',
                'channel_field': 'store_variant_id'
            }
        }.get(model)
        mapping_model = model_dict.get('mapping')
        feed_model = model_dict.get('feed')
        for channel_mapping_obj in channel_mapping_objs:
            channel_store_id = eval('channel_mapping_obj.{}'.format(model_dict.get('channel_field')))
            feed_objs = self.env[feed_model].search([
                ('store_id', '=', channel_store_id)
            ])
            for feed_obj in feed_objs:
                feed_obj.unlink()

    def _core_pre_post_write(self, obj, opr, core_model, mapping_objs, vals):
        _channel_ids = self.env['multi.channel.sale']

        for mapping_obj in mapping_objs:
            channel_id = mapping_obj.channel_id
            _channel_ids |= channel_id
            if hasattr(channel_id, '%s_mapped_%s_%s_write' % (channel_id.channel, opr, core_model)):
                vals.update(getattr(
                    channel_id, '%s_mapped_%s_%s_write' % (channel_id.channel, opr, core_model)
                )(obj, mapping_obj, vals) or vals)

        channel_ids = self.search([
            ('state', '=', 'validate'),
            ('id', 'not in', _channel_ids.ids)
        ])
        for channel_id in channel_ids:
            if hasattr(channel_id, '%s_%s_%s_write' % (channel_id.channel, opr, core_model)):
                vals.update(getattr(
                    channel_id, '%s_%s_%s_write' % (channel_id.channel, opr, core_model)
                )(obj, vals) or vals)
        return vals

    def connect_ecommerce(self):
        return True, 'Successfully connected to Ecommerce'

    def get_order_extra_vals(self, vals, from_create=True):
        """
            Add extra values directly to the sale order in Odoo.
        """
        if from_create:
            vals['team_id'] = self.crm_team_id.id
            vals['warehouse_id'] = self.warehouse_id.id
            if self.utm_campaign_id:
                vals['campaign_id'] = self.utm_campaign_id.id
            if self.sales_person_id:
                vals['user_id']=self.sales_person_id.id
            if self.utm_medium_id:
                vals['medium_id'] = self.utm_medium_id.id
            if self.utm_source_id:
                vals['source_id'] = self.utm_source_id.id
            if self.payment_term_id:
                vals['payment_term_id'] = self.payment_term_id.id
        return vals

    # Activate Developer Mode
    def channel_activate_developer_mode(self):
        """Activate the Developer mode
        """
        url = self.redirect_to_channel(self.id)
        append_url = '/web?debug=0'
        if self._context.get('debug_activate'):
            append_url = '/web?debug=1'
        url = url.replace('/web', append_url)
        return {
                'type': 'ir.actions.act_url',
                'target': 'self',
                'url': url
            }

    def redirect_to_channel(self, instance_id=False):
        """Method to get the channel's form view URL
        """
        action_id = self.env.ref('odoo_multi_channel_sale.action_multi_channel_view').id
        url = "/web#action={}&model=multi.channel.sale".format(action_id)
        if instance_id:
            url = "/web#id={}&action={}&model=multi.channel.sale&view_type=form".format(instance_id, action_id)
        return url

    channel_configs = fields.Char(compute="_channel_available_configs")

    def available_configs_to_show(self):
        """inside "_channel_available_configs" method "{channel}_available_config" 
            method will return features(fields) to show on the channel's view.
        all supported configs:
                # === Webhook Related Config keys ===
                # 'webhook_available', 
                # 'create_order_webhook',
                # 'update_order_webhook',

                # === base related configs keys ===
                'child_store_config', # Child for existing channel

                # === Import Crons keys===
                'cron_available',
                'import_order_cron',
                'order_created_after',
                'order_updated_after',
                'import_product_cron',
                'product_created_after',
                'product_updated_after',
                'import_partner_cron',
                'partner_created_after',
                'partner_updated_after',
                'import_category_cron',

                # === realtime export keys ===
                'sync_order_invoice',
                'sync_order_shipment',
                'sync_order_cancel',
        """
        return [
                'child_store_config',

                'cron_available',
                'import_order_cron',
                'order_created_after',
                'order_updated_after',
                'import_product_cron',
                'product_created_after',
                'product_updated_after',
                'import_partner_cron',
                'partner_created_after',
                'partner_updated_after',
                'import_category_cron',

                'sync_order_invoice',
                'sync_order_shipment',
                'sync_order_cancel',
            ]
    
    def available_configs_to_hide(self):
        """
            inside "_channel_available_configs" method the channel's "{channel_name}_available_configs" 
            method will return features(fields) to hide on the channel's view.
        """
        return [
            'api_record_limit',
            'total_record_limit',
            'order_state_mapping',
        ]

    def _channel_available_configs(self):
        """Get all the available features per channel
        return from channel: list of configs 
                                    or 
                            {'to_show': [], 'to_hide'=[]}
        """
        configs_to_show = self.available_configs_to_show()
        configs_to_hide = self.available_configs_to_hide()
        method = f'{self.channel}_available_configs'
        if hasattr(self, method):
            try:
                channel_configs = getattr(self, method, False)
                if channel_configs:
                    configs_to_show = channel_configs()
                    if isinstance(configs_to_show, dict):
                        to_show, to_hide = configs_to_show.get('to_show'), configs_to_show.get('to_hide')
                        if to_hide:
                            configs_to_hide = list(set(configs_to_hide) - set(to_hide))
                        configs_to_show = to_show
            except:
                pass
        configs_to_show.extend(configs_to_hide)
        self.write({'channel_configs': ','.join(set(configs_to_show))})
    
    @api.ondelete(at_uninstall=False)
    def _unlink_if_not_validate(self):
        if 'validate' in self.mapped('state'):
            raise UserError(_('You cannot delete connected instance.'))
        
    def refresh_order_webhook_status(self):
        context = self._context
        if not context.get('object_type'):
            return False
        field = f"is_{context['object_type']}_order_webhook"
        return self.write({field:False})

    @api.model    
    def _upgrade_hook(self):
        """
        Upgrade hook to set the company ID for active sales channels.
        
        This method is executed during a module upgrade.
        This ensures proper company association for active channels after the upgrade.
        """
        channel_obj = self.env['multi.channel.sale']
        channel= channel_obj.search([('active', '=', True)])
        for rec in channel:
            if not rec.company_id and rec.warehouse_id:
                rec.write({'company_id' : rec.warehouse_id.company_id.id})

    def get_feed_models(self):
        return ['category.feed','partner.feed','product.feed','order.feed','shipping.feed']


    def cron_clear_data(self, no_of_days=15):
        """Cron to Clear Successfull Data
        """
        channels = self.search([])
        for channel in channels:
            days_ago = datetime.now() - timedelta(days=no_of_days)
            domain = [
                ('channel_id', '=', channel.id),
                ('create_date', '<=', days_ago)
            ]
            if channel.clear_sync_history:
                history_domain = domain + [('status', '=', 'success')]
                sync_history = self.env['channel.synchronization'].search(history_domain)
                sync_history.unlink()
            if channel.clear_done_feed:
                feed_domain = domain + [('state', '=', 'done')]
                for model in self.get_feed_models():
                    feeds = self.env[model].search(feed_domain)
                    feeds.unlink()
