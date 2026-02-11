import logging
from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

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

    def action_woo_pull_images(self):
        """Pull images from WooCommerce for selected products."""
        if not self:
            return
            
        woo_instances = self.env['woo.sync.instance'].search([
            ('state', '=', 'connected'),
            ('active', '=', True),
        ])

        if not woo_instances:
            raise UserError(_("No active WooCommerce instances found."))

        sync_cron = self.env['woo.sync.cron']
        success_count = 0
        error_count = 0
        
        for record in self:
            for instance in woo_instances:
                try:
                    sync_cron.pull_images_only(instance, record)
                    success_count += 1
                except Exception:
                    # Log but continue processing others
                    _logger.exception("WooSync: Failed to pull image for %s", record.name)
                    error_count += 1
                    continue

        if success_count == 0 and error_count > 0:
             raise UserError(_("Image pull failed for all selected products. Check logs."))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Batch Image Pull"),
                'message': _("Updated %d products. Failures: %d.") % (success_count, error_count),
                'sticky': False,
                'type': 'success' if error_count == 0 else 'warning',
            }
        }
