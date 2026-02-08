# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from logging import getLogger
_logger = getLogger(__name__)

METAMAP = {
    'product.category': {
        'model': 'channel.category.mappings',
        'local_field': 'odoo_category_id',
        'remote_field': 'store_category_id'
    },
    'product.template': {
        'model': 'channel.template.mappings',
        'local_field': 'odoo_template_id',
        'remote_field': 'store_product_id'
    },
    'product.product': {
        'model': 'channel.product.mappings',
        'local_field': 'erp_product_id',
        'remote_field': 'store_variant_id'
    }
}
IMPORT_OPR = [
    ('product.template', 'Product'),
    ('sale.order', 'Order'),
    ('product.category', 'Category'),
    ('res.partner', 'Customer'),
    ('delivery.carrier', 'Shipping Method'),
]

class Transaction:
    def __init__(self, channel, *args, **kwargs):
        self.instance = channel
        self.channel = channel.channel
        self.env = channel.env
        self._cr = channel._cr
        self.evaluate_feed = channel.auto_evaluate_feed
        self.display_message = channel.display_message

    def import_data(self, object, **kw):
        msg = "Current channel doesn't allow it."

        success_ids = []
        error_ids = []
        create_ids = []
        update_ids = []
        kw.update(
            page_size=self.instance.api_record_limit
        )
        page, total_record_limit = 0, self.instance.total_record_limit
        if hasattr(self.instance, 'import_{}'.format(self.channel)):
            msg = ''
            try:
                while True:
                    page += 1
                    _logger.debug(">> page >> : %r", page)
                    s_ids, e_ids, feeds = [], [], False
                    data_list, kw = getattr(
                        self.instance, 'import_{}'.format(self.channel))(object, **kw), kw
                    kw = data_list[1] if isinstance(data_list, tuple) else kw
                    data_list = [] if data_list in [None, False, ''] or len(data_list) < 1 else data_list[0]
                    if data_list and type(data_list) is list:
                        kw['last_id'] = data_list[-1].get('store_id')

                    if data_list:
                        objectmapping = self.getFeedObjectDictionary()
                        if object in objectmapping:
                            s_ids, e_ids, feeds = self.env[objectmapping.get(object)].with_context(
                                channel_id=self.instance
                            ).with_company(self.instance.company_id.id)._create_feeds(data_list)
                        elif object == 'product.attribute':
                            data_list = data_list.get('create_ids', []) if data_list.get('create_ids') else data_list.get('update_ids', [])
                            msg = "<div class='alert alert-success' role='alert'><h3 class='alert-heading'><i class='fa fa-smile-o'/>  Congratulations !</h3><hr><span class='badge badge-pill badge-success'>Success</span>All attributes are synced along with the <span class='font-weight-bold'> {} attribute sets</span></div>".format(len(data_list)) if data_list else "<div class='alert alert-danger' role='alert'>Attributes are failed to import.</div>"
                        else:
                            raise Exception('Invalid object type')
                    elif not data_list and page == 1:
                        msg = "No Data Available to Import!"
                        raise Exception(kw.get('message'))

                    # NOTE: To handle api_limit==1 infinity loop
                    if kw.get('page_size', 0) == 1:
                        if locals().get('old_last_id') == kw.get('last_id'):
                            break
                        else:
                            old_last_id = kw.get('last_id')

                    self._cr.commit()
                    success_ids.extend(s_ids)
                    error_ids.extend(e_ids)
                    if self.evaluate_feed and feeds:
                        mapping_ids = feeds.with_context(get_mapping_ids=True).import_items()
                        create_ids.extend([mapping.id for mapping in mapping_ids.get('create_ids')])
                        update_ids.extend([mapping.id for mapping in mapping_ids.get('update_ids')])
                        self._cr.commit()
                    if len(data_list) < kw.get('page_size'):
                        break
                    if total_record_limit and page * (kw.get('page_size') or self.instance.api_record_limit) >= total_record_limit:
                        break
            except Exception as e:
                if not msg:
                    msg = f'Something went wrong: `{e.args[0]}`'
                _logger.exception(msg)
                msg = f"<div class='alert alert-danger' role='alert'><h3 class='alert-heading'><i class='fa fa-frown-o'/>  Exception !</h3><hr><span class='badge badge-pill badge-danger'> {msg} </span></div>"

            if not msg:
                operation = dict(IMPORT_OPR)[object]
                debug = self.instance.debug
                last_id = kw.get('last_id')
                ext_msg = kw.get('ext_msg')
                msg = self.getActionMessage(msg, success_ids, error_ids, create_ids, update_ids, last_id, debug, operation, ext_msg)
            if not msg:
                msg += f"<div class='alert alert-danger' role='alert'><h3 class='alert-heading'><i class='fa fa-frown-o'/>  Sorry !</h3><hr><span class='badge badge-pill badge-danger'> 404 </span> <span class='font-weight-bold'> No records found for applied filter.</span></div>"
        return self.display_message(msg)

    def getFeedObjectDictionary(self):
        return {'product.category': 'category.feed', 'product.template': 'product.feed', 'res.partner': 'partner.feed', 'sale.order': 'order.feed', 'delivery.carrier': 'shipping.feed'}

    def export_data(self, object, object_ids, operation='export'):
        msg = "Selected Channel doesn't allow it."
        success_ids, error_ids = [], []

        mappings = self.env[METAMAP.get(object).get('model')].search(
            [
                ('channel_id', '=', self.instance.id),
                (
                    METAMAP.get(object).get('local_field'),
                    'in',
                    object_ids
                ),
            ]
        )

        if operation == 'export' and hasattr(self.instance, 'export_{}'.format(self.channel)):
            msg = ''
            local_ids = mappings.mapped(
                lambda mapping: int(getattr(mapping, METAMAP.get(object).get('local_field')))
            )
            local_ids = set(object_ids) - set(local_ids)
            if not local_ids:
                return self.display_message(
                    """<p style='color:orange'>
                        Selected records have already been exported.
                    </p>"""
                )
            operation = 'exported'
            for record in self.env[object].browse(local_ids):
                res, remote_object = getattr(self.instance, 'export_{}'.format(self.channel))(record)
                if res:
                    self.create_mapping(record, remote_object)
                    self.env.cr.commit()
                    success_ids.append(record.id)
                else:
                    error_ids.append(record.id)

        elif operation == 'update' and hasattr(self.instance, 'update_{}'.format(self.channel)):
            msg = ''
            local_ids = mappings.filtered_domain([
                ('need_sync', '=', 'yes')]).mapped(
                lambda mapping: int(getattr(mapping, METAMAP.get(object).get('local_field')))
            )
            if not local_ids:
                if mappings:
                    return self.display_message(
                        """<p style='color:orange'>
                            Nothing to update on selected records.
                        </p>"""
                    )
                else:
                    return self.display_message(
                        """<p style='color:orange'>
                            Selected records haven't been exported yet.
                        </p>"""
                    )
            operation = 'updated'
            for record in self.env[object].browse(local_ids):
                res, remote_object = getattr(self.instance, 'update_{}'.format(self.channel))(
                    record=record,
                    get_remote_id=self.get_remote_id
                )
                if res:
                    success_ids.append(record.id)
                else:
                    error_ids.append(record.id)

        self.env[METAMAP.get(object).get('model')].search([
            ('channel_id', '=', self.instance.id),
            (
                METAMAP.get(object).get('local_field'),
                'in',
                success_ids
            )]).write({'need_sync': 'no'})

        if not msg:
            if success_ids:
                msg += f"<p style='color:green'>{success_ids} {operation}.</p>"
            if error_ids:
                msg += f"<p style='color:red'>{error_ids} not {operation}.</p>"
        return self.display_message(msg)

    def get_remote_id(self, record):
        mapping = self.env[METAMAP.get(record._name).get('model')].search(
            [
                ('channel_id', '=', self.instance.id),
                (METAMAP.get(record._name).get('local_field'), '=', record.id)
            ]
        )
        return getattr(mapping, METAMAP.get(record._name).get('remote_field'))

    def create_mapping(self, local_record, remote_object):
        if local_record._name == 'product.category':
            self.env['channel.category.mappings'].create(
                {
                    'channel_id': self.instance.id,
                    'ecom_store': self.instance.channel,
                    'category_name': local_record.id,
                    'odoo_category_id': local_record.id,
                    'store_category_id': remote_object.get('id') if isinstance(remote_object, dict) else remote_object.id,
                    'operation': 'export',
                }
            )
        elif local_record._name == 'product.template':
            self.env['channel.template.mappings'].create(
                {
                    'channel_id': self.instance.id,
                    'ecom_store': self.instance.channel,
                    'template_name': local_record.id,
                    'odoo_template_id': local_record.id,
                    'default_code': local_record.default_code,
                    'barcode': local_record.barcode,
                    'store_product_id': remote_object.get('id') if isinstance(remote_object, dict) else remote_object.id,
                    'operation': 'export',
                }
            )
            remote_variants = remote_object.get('variants') if isinstance(remote_object, dict) else remote_object.variants
            for local_variant, remote_variant in zip(local_record.product_variant_ids, remote_variants):
                self.env['channel.product.mappings'].create(
                    {
                        'channel_id': self.instance.id,
                        'ecom_store': self.instance.channel,
                        'product_name': local_variant.id,
                        'erp_product_id': local_variant.id,
                        'default_code': local_variant.default_code,
                        'barcode': local_variant.barcode,
                        'store_product_id': remote_object.get('id') if isinstance(remote_object, dict) else remote_object.id,
                        'store_variant_id': remote_variant.get('id') if isinstance(remote_variant, dict) else remote_variant.id,
                        'operation': 'export',
                    }
                )

    def getActionMessage(self, msg, success_ids, error_ids, create_ids, update_ids, last_id, debug, operation, ext_msg):
        if success_ids:
            msg += (f"<div class='alert alert-success' role='alert'>"
                    f"<h3 class='alert-heading'><i class='fa fa-smile-o'/>  Congratulations !</h3>"
                    f"<hr><span class='badge badge-pill badge-success'>Success</span>"
                    f"Data of the {operation} has been successfully imported. "
                    f"<span class='font-weight-bold'> {len(success_ids)} records of {operation} has been created/updated at Odoo</span></div>")
            if debug == 'enable':
                msg += f"<hr><div class='alert alert-success' role='alert'><br/>Ids of the records are <br/>{success_ids}.</div>"
        if error_ids:
            msg += (f"<div class='alert alert-danger' role='alert'>"
                    f"<h3 class='alert-heading'><i class='fa fa-frown-o'/>  Sorry !</h3>"
                    f"<hr><span class='badge badge-pill badge-danger'>Success</span>"
                    f"Data of the {operation} has been failed to imported. "
                    f"<span class='font-weight-bold'> {len(error_ids)} records of {operation} has been failed to create/update at Odoo</span></div>")
            if debug == 'enable':
                msg += f"<hr><div class='alert alert-danger' role='alert'><br/>Failed records are <br/>{error_ids}.</div>"
        if create_ids:
            msg += (f"<div class='alert alert-warning' role='alert'>"
                    f"<h3 class='alert-heading'><i class='fa fa-check-circle'/>  Great !</h3>"
                    f"<hr><span class='badge badge-pill badge-warning'>Imported</span>"
                    f"Data of the {operation} has been successfully created. "
                    f"<span class='font-weight-bold'> {len(create_ids)} records of {operation} has been created at Odoo</span></div>")
            if debug == 'enable':
                msg += f"<hr><div class='alert alert-warning' role='alert'><br/>Ids of the records are <br/>{create_ids}.</div>"
        if update_ids:
            msg += (f"<div class='alert alert-warning' role='alert'>"
                    f"<h3 class='alert-heading'><i class='fa fa-check-circle'/>  Yippee !</h3>"
                    f"<hr><span class='badge badge-pill badge-warning'>Updated</span>"
                    f"Data of the {operation} has been successfully updated. "
                    f"<span class='font-weight-bold'> {len(update_ids)} records of {operation} has been updated at Odoo</span></div>")
            if debug == 'enable':
                msg += f"<hr><div class='alert alert-warning' role='alert'><br/>Ids of the records are <br/>{update_ids}.</div>"
        if ext_msg:
            msg += (f"<div class='alert alert-info' role='alert'>"
                    f"<h3 class='alert-heading'><i class='fa fa-info-circle'/>  Info !</h3>"
                    f"<hr><span class='badge badge-pill badge-info'>Information</span>"
                    f"Data of the {operation} has been failed to imported. <span class='font-weight-bold'> {ext_msg} </span></div>")
        if last_id:
            msg += f"<hr><span class='badge badge-pill badge-info'>Last Imported Record :{last_id}.</span>"
        return msg
