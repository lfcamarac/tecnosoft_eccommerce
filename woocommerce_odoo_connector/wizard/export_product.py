# -*- coding: utf-8 -*-
#################################################################################
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    See LICENSE file for full copyright and licensing details.
##########H#########Y#########P#########N#########O#########S###################
from urllib import parse as urlparse
import logging
_logger = logging.getLogger(__name__)
from odoo import api, fields, models,_
from odoo.exceptions import UserError


class ExportWoocommerceProducts(models.TransientModel):
    _inherit = 'export.products'

    def action_woocommerce_export_product(self):
        active_ids = self._context.get('active_ids')
        prod_env = self.env['product.product']
        temp_ids = [prod_env.browse(
            active_id).product_tmpl_id.id for active_id in active_ids]
        channel_id = self.channel_id.id
        return self.env['export.templates'].create({
            "channel_id": channel_id,
            "operation": "export" if self.operation == "export" else "update",
        }).with_context({
            "active_ids": temp_ids,
            "active_model": "product.template",
        }).action_woocommerce_export_template()


class ExportWoocommerceTemplates(models.TransientModel):
    _inherit = "export.templates"

    def woocommerce_export_now(self, record):
        remote_object = {}
        channel = self._context.get('channel_id')
        woocommerce = self._context.get('woocommerce')
        response = self._woocommerce_export_update_template(woocommerce, channel, record)
        remote_object["id"], variant_list = response
        remote_object["variants"] = [{"id": variant_id} for variant_id in variant_list]
        return True, remote_object

    def _woocommerce_export_update_template(self, woocommerce, channel, template_record):
        if template_record.attribute_line_ids:
            data_list = self._create_update_woocommerce_variable_product(
                woocommerce, channel, template_record)
        else:
            returnid = self._create_update_woocommerce_simple_product(
                woocommerce, channel, template_record)
            data_list = [returnid, ["No Variants"]]
        return data_list

    def _set_woocommerce_image_path(self, product_id):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # multi-channel new image endpoint, new image size based on image field
        image_name = urlparse.quote(product_id.display_name.replace("/", "-"), safe="")
        image_url = f'/channel/image/product.product/{product_id.id}/image_1920/{image_name}.png'
        return urlparse.urljoin(base_url, image_url) 

    def _create_woocommerce_product_image(self, template, is_multi_variant=False):
        image_list = []
        count = 0
        template_url = self._set_woocommerce_image_path(
            template.product_variant_id)
        image_list.append({
            'src' : template_url,
            'position' : 0,
        })
        if is_multi_variant:
            for variant_id in template.product_variant_ids:
                count += 1
                variant_url = self._set_woocommerce_image_path(variant_id)
                image_list.append({
                    'src' : variant_url,
                    'position' : count,
                })
        return image_list

    def _get_woocommerce_attribute_dict(self, woocommerce, channel, variant):
        attribute_dict = []
        if variant.product_template_attribute_value_ids:
            for attribute_line in variant.product_template_attribute_value_ids:
                attr_name, attr_id = self.export_attribute(
                    woocommerce, channel, attribute_line.attribute_id,attribute_line.product_attribute_value_id)
                value_name = attribute_line.product_attribute_value_id.name
                attribute_dict.append({
                    'id'	: attr_id,
                    'name'	: attr_name,
                    'option': value_name,
                })
        return attribute_dict

    def _get_woocommerce_attribute_value(self, attribute_line):
        return [value.name for value in attribute_line.value_ids]

    def export_attribute(self, woocommerce, channel, attribute,attribute_values):
        store_attribute_id = False
        is_attribute_mapped = self.env['channel.attribute.mappings'].search([
            ('odoo_attribute_id', '=', attribute.id),
            ('channel_id', '=', channel.id)])
        if not is_attribute_mapped:
            return_dict = woocommerce.post(
                'products/attributes', {
                "name"			: attribute.name,
                "type"			: "select",
                "order_by"		: "menu_order",
                "has_archives"	: True
            }).json()
            if 'message' in return_dict:
                raise UserError(f"Error in Creating Attributes : {return_dict['message']}")
            store_attribute_id = return_dict['id']
            channel.create_attribute_mapping(attribute, store_attribute_id,store_attribute_name = attribute.name)
        else:
            store_attribute_id = is_attribute_mapped.store_attribute_id
        for attribute_value in attribute_values:
            self.export_attribute_values(
                woocommerce, channel, attribute_value, store_attribute_id)
        return attribute.name, store_attribute_id

    def export_attribute_values(self, woocommerce, channel, attribute_value, store_attribute_id):
        attr_value_mapping = self.env['channel.attribute.value.mappings'].search([
            ("channel_id", '=', channel.id),
            ("attribute_value_name", '=', attribute_value.id)
        ])
        if not attr_value_mapping:
            return_dict = woocommerce.post(f'products/attributes/{store_attribute_id}/terms', {
                "name": attribute_value.name,
            }).json()
            if 'message' in return_dict:
                raise UserError(f"Error in Creating terms {return_dict['message']}")
            channel.create_attribute_value_mapping(attribute_value,return_dict["id"],store_attribute_value_name = attribute_value.name)

    def _set_woocommerce_attribute_line(self, woocommerce, channel, template):
        attribute_list = []
        attribute_count = 0
        if template.attribute_line_ids:
            for attribute_line in template.attribute_line_ids:
                attr_name, attr_id = self.export_attribute(woocommerce, channel, attribute_line.attribute_id,attribute_line.value_ids)
                values = self._get_woocommerce_attribute_value(attribute_line)
                attribute_list.append({
                    'name'	: attr_name,
                    'id'    	: attr_id,
                    'variation'	: "true",
                    'visible'	: "true",
                    'position'	: attribute_count,
                    'options'	: values,
                })
                attribute_count += 1
        return attribute_list

    def _create_woocommerce_variation(self, woocommerce, channel, store_product_id, template,
            image_ids=False):
        count = 0
        variant_list = []
        for variant in template.product_variant_ids:
            variant_data = {
                'regular_price'	: str(channel.pricelist_name._get_product_price(variant, quantity=1)) or "",
                'visible'		: True,
                'sku'			: variant.default_code or "",
                'stock_quantity': channel.get_quantity(variant),
                'description'	: variant.description or "",
                'manage_stock'	: True,
                'in_stock'		: True,
                'attributes'	: self._get_woocommerce_attribute_dict(woocommerce, channel, variant),
                'weight':str(variant.weight)
            }
            if image_ids:
                variant_data.update(
                    {'image': {'id': image_ids[count]}})
            return_dict = woocommerce.post(f'products/{store_product_id}/variations', variant_data).json()
            count += 1
            if "message" in return_dict:
                raise UserError(f"Error in creating variant : {return_dict['message']}")
            variant_list.append(return_dict['id'])
        return variant_list

    def _create_update_woocommerce_variable_product(self, woocommerce, channel, template):
        request = woocommerce.post
        resource = 'products'
        toUpdate = self._context.get('update')
        remoteId = self._context.get('remoteId')
        operation = self._create_woocommerce_variation
        if toUpdate and remoteId :
            request = woocommerce.put
            resource = f'products/{remoteId}'
            operation = self._update_woocommerce_variation
        productDict = {
            'name'				: template.name,
            'sku' 				: "",
            'images'			: self._create_woocommerce_product_image(template,
                                    is_multi_variant = True),
            'type'				: 'variable',
            'categories'		: self._set_woocommerce_product_categories(woocommerce, channel, template),
            'status'			: 'publish',
            'manage_stock'		: False,
            'attributes'		: self._set_woocommerce_attribute_line(woocommerce, channel, template),
            'default_attributes': self._get_woocommerce_attribute_dict(
                woocommerce, channel, template.product_variant_ids[0]),
            'short_description'	: template.description_sale or "",
            'description'		: template.description or "",
            'weight'            :str(template.weight),
        }
        returnDict = request(resource, productDict).json()
        if 'message' in returnDict:
            raise UserError(f'Error in exporting/updating product : {returnDict["message"]}')
        imageIds = [image['id'] for image in returnDict['images'] if image['position'] !=0]
        storeTemplateId = returnDict["id"]
        returnList = operation(
            woocommerce, channel, storeTemplateId, template, image_ids=imageIds)
        return returnDict['id'], returnList

    def _create_update_woocommerce_simple_product(self, woocommerce, channel, template):
        request = woocommerce.post
        resource = 'products'
        toUpdate = self._context.get('update')
        remoteId = self._context.get('remoteId')
        if toUpdate and remoteId :
            request = woocommerce.put
            resource = f'products/{remoteId}'
        productDict = {
            'name'				: template.name,
            'sku' 				: template.default_code or "",
            'regular_price'		: str(channel.pricelist_name._get_product_price(template.product_variant_ids[0], quantity=1)) or "",
            'type'				: 'simple',
            'categories'		: self._set_woocommerce_product_categories(woocommerce, channel, template),
            'status'			: 'publish',
            'short_description'	: template.description_sale or "",
            'description'		: template.description or "",
            'manage_stock'		: True,
            'stock_quantity'	: channel.get_quantity(template),
            'in_stock'		    : True,
            'weight'            : str(template.weight),
            'images'            : self._create_woocommerce_product_image(template),
        }
        returnDict = request(resource, productDict).json()
        if 'message' in returnDict:
            raise UserError(f'Error in exporting/updating Products : {returnDict["message"]}')
        return returnDict['id']

    def _set_woocommerce_product_categories(self, woocommerce, channel, template):
        categ_list = []
        for extra_categ in template.channel_category_ids:
            if extra_categ.instance_id.id == channel.id:
                categ_list = list(map(lambda ele:{'id':ele}, extra_categ.mapped('extra_category_ids.channel_mapping_ids.store_category_id')))
                break
        return categ_list