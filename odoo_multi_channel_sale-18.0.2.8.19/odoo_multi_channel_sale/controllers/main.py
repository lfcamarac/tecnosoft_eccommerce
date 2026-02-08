# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import http
from odoo.http import request
from odoo.tools.image import image_guess_size_from_field_name
from odoo.exceptions import UserError


class Channel(http.Controller):
    @http.route(['/channel/update/mapping'], auth="public", type='json')
    def update_mapping(self, **post):
        field = {
            'product.product': 'erp_product_id',
            'sale.order': 'odoo_order_id',
            }.get(str(post.get('model')))
        model = {
            'product.product': 'channel.product.mappings',
            'sale.order': 'channel.order.mappings',
                }.get(str(post.get('model')))
        if field and model:
            domain = [(field, '=', int(post.get('id')))]
            mappings = request.env[model].sudo().search(domain)
            for mapping in mappings:
                pass
                # mapping.need_sync='yes'
        return True

    def core_content_image(self, xmlid=None, model='ir.attachment', id=None, field='raw',
                           filename_field='name', filename=None, mimetype=None, unique=False,
                           download=False, width=0, height=0, crop=False, access_token=None,
                           nocache=False):
        try:
            record = request.env['ir.binary'].sudo()._find_record(xmlid, model, id and int(id), access_token)
            stream = request.env['ir.binary'].sudo()._get_image_stream_from(
                record, field, filename=filename, filename_field=filename_field,
                mimetype=mimetype, width=int(width), height=int(height), crop=crop,
            )
        except UserError as exc:
            if download:
                raise request.not_found() from exc
            # Use the ratio of the requested field_name instead of "raw"
            if (int(width), int(height)) == (0, 0):
                width, height = image_guess_size_from_field_name(field)
            record = request.env.ref('web.image_placeholder').sudo()
            stream = request.env['ir.binary']._get_image_stream_from(
                record, 'raw', width=int(width), height=int(height), crop=crop,
            )

        send_file_kwargs = {'as_attachment': download}
        if unique:
            send_file_kwargs['immutable'] = True
            send_file_kwargs['max_age'] = http.STATIC_CACHE_LONG
        if nocache:
            send_file_kwargs['max_age'] = None

        return stream.get_response(**send_file_kwargs)

    @http.route([
        '/channel/image.png',
        '/channel/image/<xmlid>.png',
        '/channel/image/<xmlid>/<int:width>x<int:height>.png',
        '/channel/image/<xmlid>/<field>.png',
        '/channel/image/<xmlid>/<field>/<int:width>x<int:height>.png',
        '/channel/image/<model>/<id>/<field>.png',
        '/channel/image/<model>/<id>/<field>/<int:width>x<int:height>.png',
        '/channel/image/<model>/<id>/<field>/<string:filename>.png',
        '/channel/image/<model>/<id>/<field>/<int:width>x<int:height>/<string:filename>.png',
        '/channel/image.jpg',
        '/channel/image/<xmlid>.jpg',
        '/channel/image/<xmlid>/<int:width>x<int:height>.jpg',
        '/channel/image/<xmlid>/<field>.jpg',
        '/channel/image/<xmlid>/<field>/<int:width>x<int:height>.jpg',
        '/channel/image/<model>/<id>/<field>.jpg',
        '/channel/image/<model>/<id>/<field>/<int:width>x<int:height>.jpg',
        '/channel/image/<model>/<id>/<field>/<string:filename>.jpg',
        '/channel/image/<model>/<id>/<field>/<int:width>x<int:height>/<string:filename>.jpg',
    ], type='http', auth="public", website=False, multilang=False)
    def content_image(self, id=None, **kw):
        if id:
            id, _, unique = id.partition('_')
            kw['id'] = int(id)
            if unique:
                kw['unique'] = unique
        return self.core_content_image(**kw)
