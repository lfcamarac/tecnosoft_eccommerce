from odoo import models, _
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_woo_push_product(self):
        """Manually trigger sync for this product to all active Woo instances."""
        self.ensure_one()
        woo_instances = self.env['woo.sync.instance'].search([
            ('state', '=', 'connected'),
            ('active', '=', True),
        ])

        if not woo_instances:
            raise UserError(_("No active WooCommerce instances found."))

        sync_cron = self.env['woo.sync.cron']
        success_count = 0
        
        for instance in woo_instances:
            try:
                sync_cron.sync_specific_product(instance, self)
                success_count += 1
            except Exception as e:
                _logger.exception("WooSync: Failed to push product %s to instance %s", self.name, instance.name)
                last_error = str(e)
                continue

        if success_count == 0:
             raise UserError(_("Product sync failed. Detail: %s") % last_error)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Sync Initiated"),
                'message': _("Product '%s' pushed to %d WooCommerce instances.") % (self.name, success_count),
                'sticky': False,
                'type': 'success',
            }
        }
