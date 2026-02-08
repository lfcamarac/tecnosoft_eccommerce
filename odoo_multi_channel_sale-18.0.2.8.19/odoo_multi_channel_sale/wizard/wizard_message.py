# -*- coding: utf-8 -*-
################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
################################################################################
from odoo import models


class WkWizardMessage(models.TransientModel):
    _inherit = "wk.wizard.message"

    def operation_back(self):
        ctx = dict(self._context or {})
        active_model = ctx.get('active_model')
        partial = self.env[active_model].browse(ctx.get('active_id'))
        ctx['active_id'] = False
        ctx['default_channel_id'] = False
        return {'name': "Import Operation",
                'view_mode': 'form',
                'view_id': False,
                'res_model': active_model,
                'res_id': partial.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'context': ctx,
                'domain': '[]',
                }

