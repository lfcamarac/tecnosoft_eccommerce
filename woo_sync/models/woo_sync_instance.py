import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WooSyncInstance(models.Model):
    _name = 'woo.sync.instance'
    _description = 'WooCommerce Sync Instance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('connected', 'Connected'),
        ('error', 'Error'),
    ], default='draft', tracking=True, copy=False)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True)

    # WooCommerce credentials
    woo_url = fields.Char(
        "WooCommerce URL", required=True,
        help="URL de tu tienda WooCommerce, ej: https://mitienda.com")
    woo_consumer_key = fields.Char("Consumer Key", required=True)
    woo_consumer_secret = fields.Char("Consumer Secret", required=True)
    woo_timeout = fields.Integer("API Timeout (seg)", default=40)
    woo_verify_ssl = fields.Boolean("Verificar SSL", default=True)

    # Sync configuration
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Lista de precios',
        default=lambda self: self.env['product.pricelist'].search(
            [('company_id', 'in', [self.env.company.id, False])], limit=1),
        help="Lista de precios para calcular el precio de exportación")
    stock_source = fields.Selection([
        ('global', 'Todas las bodegas (General)'),
        ('specific', 'Bodegas específicas'),
    ], default='global', string="Fuente de Stock", required=True)
    
    warehouse_ids = fields.Many2many(
        'stock.warehouse', string='Bodegas',
        help="Bodegas a considerar para el stock. Si se deja vacío en modo 'Específico', se asume 0.")
    
    # Deprecated single warehouse field
    warehouse_id = fields.Many2one('stock.warehouse', string='Almacén (Obsoleto)')
    stock_type = fields.Selection([
        ('qty_available', 'Cantidad disponible'),
        ('free_qty', 'Cantidad libre'),
        ('virtual_available', 'Cantidad pronosticada'),
    ], default='qty_available', string='Tipo de stock', required=True)

    # Sync scope
    product_domain = fields.Char(
        "Filtro de productos", default="[('sale_ok','=',True)]",
        help="Dominio para filtrar qué productos sincronizar (sobre product.template)")
    sync_archived_as_draft = fields.Boolean(
        "Archivar como borrador", default=True,
        help="Cuando un producto se archiva en Odoo, ponerlo como borrador en WooCommerce")
    default_woo_status = fields.Selection([
        ('publish', 'Publicado'),
        ('draft', 'Borrador'),
        ('private', 'Privado'),
    ], default='publish', string="Estado por defecto en WooCommerce")

    # Batch settings
    batch_size = fields.Integer(
        "Tamaño de lote", default=100,
        help="Máximo de productos por llamada batch a WooCommerce (máx 100)")

    # Relational
    template_mapping_ids = fields.One2many(
        'woo.sync.template.mapping', 'instance_id', string='Mapeos de productos')
    variant_mapping_ids = fields.One2many(
        'woo.sync.variant.mapping', 'instance_id', string='Mapeos de variantes')
    category_mapping_ids = fields.One2many(
        'woo.sync.category.mapping', 'instance_id', string='Mapeos de categorías')
    attribute_mapping_ids = fields.One2many(
        'woo.sync.attribute.mapping', 'instance_id', string='Mapeos de atributos')
    log_ids = fields.One2many(
        'woo.sync.log', 'instance_id', string='Logs de sincronización')

    # Computed
    template_mapping_count = fields.Integer(
        compute='_compute_counts', string='Productos mapeados')
    log_count = fields.Integer(
        compute='_compute_counts', string='Logs')

    @api.depends('template_mapping_ids', 'log_ids')
    def _compute_counts(self):
        for rec in self:
            rec.template_mapping_count = len(rec.template_mapping_ids)
            rec.log_count = len(rec.log_ids)

    def _get_woo_api(self):
        """Return a woocommerce.API connection object."""
        self.ensure_one()
        try:
            from woocommerce import API
        except ImportError:
            raise UserError(
                "La librería 'woocommerce' no está instalada. "
                "Ejecuta: pip install woocommerce")
        return API(
            url=self.woo_url,
            consumer_key=self.woo_consumer_key,
            consumer_secret=self.woo_consumer_secret,
            wp_api=True,
            version="wc/v3",
            timeout=self.woo_timeout,
            query_string_auth=True,
            verify_ssl=self.woo_verify_ssl,
            user_agent="Odoo WooSync/1.0",
        )

    def action_test_connection(self):
        """Test the WooCommerce connection."""
        self.ensure_one()
        try:
            api = self._get_woo_api()
            res = api.get('system_status')
            if res.status_code == 200:
                self.state = 'connected'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Conexión exitosa con WooCommerce',
                        'type': 'success',
                        'sticky': False,
                    },
                }
            else:
                self.state = 'error'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': f'Error {res.status_code}: {res.text[:200]}',
                        'type': 'danger',
                        'sticky': True,
                    },
                }
        except Exception as e:
            self.state = 'error'
            raise UserError(f'Error de conexión: {str(e)}')

    def action_sync_now(self):
        """Manually trigger a full sync."""
        self.ensure_one()
        if self.state != 'connected':
            raise UserError('Primero debes conectar la instancia.')
        self.env['woo.sync.cron']._run_full_sync(self)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Sincronización completada. Revisa los logs para más detalles.',
                'type': 'success',
                'sticky': False,
            },
        }

    def action_sync_stock_price(self):
        """Manually trigger stock & price sync."""
        self.ensure_one()
        if self.state != 'connected':
            raise UserError('Primero debes conectar la instancia.')
        self.env['woo.sync.cron']._run_stock_price_sync(self)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Sincronización de stock y precios completada.',
                'type': 'success',
                'sticky': False,
            },
        }

    def _get_product_qty(self, product):
        """Get stock quantity for a product.product based on config."""
        self.ensure_one()
        if self.stock_source == 'global':
            # Global stock (all warehouses)
            product = product.with_context(warehouse=False, location=False)
            return int(getattr(product, self.stock_type, 0))
        
        # Specific warehouses
        if not self.warehouse_ids:
            return 0
            
        total_qty = 0
        for wh in self.warehouse_ids:
             p_ctx = product.with_context(
                 warehouse=wh.id,
                 location=wh.lot_stock_id.id
             )
             total_qty += int(getattr(p_ctx, self.stock_type, 0))
        return total_qty

    def _get_product_price(self, product):
        """Get price from the configured pricelist for a product.product."""
        self.ensure_one()
        if self.pricelist_id:
            return self.pricelist_id._get_product_price(product, quantity=1.0)
        return product.list_price

    def action_view_mappings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Mapeos de productos',
            'res_model': 'woo.sync.template.mapping',
            'view_mode': 'list,form',
            'domain': [('instance_id', '=', self.id)],
            'context': {'default_instance_id': self.id},
        }

    def action_view_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Logs de sincronización',
            'res_model': 'woo.sync.log',
            'view_mode': 'list,form',
            'domain': [('instance_id', '=', self.id)],
            'context': {'default_instance_id': self.id},
        }
