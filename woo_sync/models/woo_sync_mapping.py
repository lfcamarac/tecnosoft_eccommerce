from odoo import fields, models


class WooSyncTemplateMapping(models.Model):
    _name = 'woo.sync.template.mapping'
    _description = 'WooSync Product Template Mapping'
    _rec_name = 'product_tmpl_id'

    instance_id = fields.Many2one(
        'woo.sync.instance', required=True, ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one(
        'product.template', string='Producto', required=True,
        ondelete='cascade', index=True)
    woo_product_id = fields.Integer(
        "WooCommerce Product ID", required=True, index=True)
    woo_product_type = fields.Selection([
        ('simple', 'Simple'),
        ('variable', 'Variable'),
    ], string="Tipo en WooCommerce")
    last_sync_date = fields.Datetime("Última sincronización")

    variant_mapping_ids = fields.One2many(
        'woo.sync.variant.mapping', 'template_mapping_id',
        string='Mapeos de variantes')

    _sql_constraints = [
        ('instance_template_uniq',
         'unique(instance_id, product_tmpl_id)',
         'Cada producto solo puede mapearse una vez por instancia.'),
        ('instance_woo_product_uniq',
         'unique(instance_id, woo_product_id)',
         'Cada producto WooCommerce solo puede mapearse una vez por instancia.'),
    ]


class WooSyncVariantMapping(models.Model):
    _name = 'woo.sync.variant.mapping'
    _description = 'WooSync Product Variant Mapping'
    _rec_name = 'product_id'

    instance_id = fields.Many2one(
        'woo.sync.instance', required=True, ondelete='cascade', index=True)
    template_mapping_id = fields.Many2one(
        'woo.sync.template.mapping', required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Variante', required=True,
        ondelete='cascade', index=True)
    woo_variation_id = fields.Integer(
        "WooCommerce Variation ID", required=True)
    last_sync_date = fields.Datetime("Última sincronización")

    _sql_constraints = [
        ('instance_variant_uniq',
         'unique(instance_id, product_id)',
         'Cada variante solo puede mapearse una vez por instancia.'),
    ]


class WooSyncCategoryMapping(models.Model):
    _name = 'woo.sync.category.mapping'
    _description = 'WooSync Category Mapping'
    _rec_name = 'category_id'

    instance_id = fields.Many2one(
        'woo.sync.instance', required=True, ondelete='cascade', index=True)
    category_id = fields.Many2one(
        'product.category', string='Categoría', required=True,
        ondelete='cascade', index=True)
    woo_category_id = fields.Integer(
        "WooCommerce Category ID", required=True)

    _sql_constraints = [
        ('instance_category_uniq',
         'unique(instance_id, category_id)',
         'Cada categoría solo puede mapearse una vez por instancia.'),
    ]


class WooSyncAttributeMapping(models.Model):
    _name = 'woo.sync.attribute.mapping'
    _description = 'WooSync Attribute Mapping'
    _rec_name = 'attribute_id'

    instance_id = fields.Many2one(
        'woo.sync.instance', required=True, ondelete='cascade', index=True)
    attribute_id = fields.Many2one(
        'product.attribute', string='Atributo', required=True,
        ondelete='cascade')
    woo_attribute_id = fields.Integer(
        "WooCommerce Attribute ID", required=True)

    _sql_constraints = [
        ('instance_attribute_uniq',
         'unique(instance_id, attribute_id)',
         'Cada atributo solo puede mapearse una vez por instancia.'),
    ]


class WooSyncAttributeValueMapping(models.Model):
    _name = 'woo.sync.attribute.value.mapping'
    _description = 'WooSync Attribute Value Mapping'
    _rec_name = 'attribute_value_id'

    instance_id = fields.Many2one(
        'woo.sync.instance', required=True, ondelete='cascade', index=True)
    attribute_value_id = fields.Many2one(
        'product.attribute.value', string='Valor de atributo',
        required=True, ondelete='cascade')
    woo_term_id = fields.Integer(
        "WooCommerce Term ID", required=True)
    woo_attribute_id = fields.Integer(
        "WooCommerce Attribute ID", required=True)

    _sql_constraints = [
        ('instance_attr_val_uniq',
         'unique(instance_id, attribute_value_id)',
         'Cada valor de atributo solo puede mapearse una vez por instancia.'),
    ]
