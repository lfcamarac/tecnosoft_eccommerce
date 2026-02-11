from odoo import fields, models


class WooSyncLog(models.Model):
    _name = 'woo.sync.log'
    _description = 'WooSync Log Entry'
    _order = 'create_date desc'

    instance_id = fields.Many2one(
        'woo.sync.instance', required=True, ondelete='cascade', index=True)
    sync_type = fields.Selection([
        ('product', 'Producto'),
        ('stock', 'Stock'),
        ('price', 'Precio'),
        ('category', 'Categoría'),
        ('attribute', 'Atributo'),
        ('full', 'Sync completo'),
    ], required=True)
    status = fields.Selection([
        ('success', 'Exitoso'),
        ('error', 'Error'),
        ('warning', 'Advertencia'),
    ], required=True)
    product_tmpl_id = fields.Many2one(
        'product.template', string="Producto")
    product_id = fields.Many2one(
        'product.product', string="Variante")
    message = fields.Text("Mensaje")
    woo_request = fields.Text("Request API")
    woo_response = fields.Text("Response API")
