# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################

from odoo import models, _

class MultiChannelSale(models.Model):
    _inherit = 'multi.channel.sale'

    @staticmethod
    def get_operation_message_v1(obj='product', obj_model='feed', operation='created', obj_ids=None):
        """
        Get message for operation .
        :param obj: model name ==> product , attribute , category
        :name obj_name: object name ==> feed ,mapping , object , record
        :operation: operation ==> created ,updated
        :obj_ids: list of object
        :return: message .
        """
        obj_ids = obj_ids or []
        message = ''
        if len(obj_ids):
            message += '<br/>Total {count}  {obj} {obj_model}  {operation}.'.format(
                count=len(obj_ids), obj=obj, obj_model=obj_model, operation=operation)
        return message

    @staticmethod
    def get_feed_import_message(obj, create_ids=[], update_ids=[], map_create_ids=[], map_update_ids=[]):
        message = ''
        if map_create_ids or map_update_ids:
            if len(map_create_ids):
                message += '<br/>Total %s  new %s created.' % (
                    len(map_create_ids), obj)
            if len(map_update_ids):
                message += '<br/>Total %s  %s updated.' % (
                    len(map_update_ids), obj)
        else:
            if len(create_ids):
                message += '<br/>Total %s new %s feed created.' % (
                    len(create_ids), obj)
            if len(update_ids):
                message += '<br/>Total %s  %s feed updated.' % (
                    len(update_ids), obj)
            if not (len(create_ids) or len(update_ids)):
                message += '<br/>No  data imported/updated.'

        return message

    def display_message(self, message):
        return self.env['wk.wizard.message'].genrated_message(message, 'Summary')
