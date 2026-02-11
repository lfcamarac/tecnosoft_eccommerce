import logging
import time

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

# Process templates in chunks to avoid memory issues
CHUNK_SIZE = 500
# Max time per cron run (50 min) to avoid Odoo worker timeout
MAX_CRON_SECONDS = 50 * 60


class WooSyncCron(models.AbstractModel):
    _name = 'woo.sync.cron'
    _description = 'WooSync Cron Logic'

    # -------------------------------------------------------------------------
    # CRON ENTRY POINTS
    # -------------------------------------------------------------------------

    @api.model
    def _cron_full_sync(self):
        """Cron entry: full product sync for all connected instances."""
        instances = self.env['woo.sync.instance'].search([
            ('state', '=', 'connected'),
            ('active', '=', True),
        ])
        for instance in instances:
            try:
                self._run_full_sync(instance)
            except Exception as e:
                _logger.exception(
                    "WooSync: Full sync failed for instance %s", instance.name)
                self._create_log(instance, 'full', 'error', message=str(e))
                self.env.cr.commit()

    @api.model
    def _cron_stock_price_sync(self):
        """Cron entry: lightweight stock & price sync for mapped products."""
        instances = self.env['woo.sync.instance'].search([
            ('state', '=', 'connected'),
            ('active', '=', True),
        ])
        for instance in instances:
            try:
                self._run_stock_price_sync(instance)
            except Exception as e:
                _logger.exception(
                    "WooSync: Stock/price sync failed for instance %s",
                    instance.name)
                self._create_log(instance, 'stock', 'error', message=str(e))
                self.env.cr.commit()

    # -------------------------------------------------------------------------
    # FULL SYNC (CHUNKED + TIME-AWARE)
    # -------------------------------------------------------------------------

    def _run_full_sync(self, instance):
        """Full sync pipeline for one instance. Processes in chunks and
        respects a time limit to avoid worker timeout."""
        api = instance._get_woo_api()
        start_time = time.time()
        success_count = 0
        error_count = 0
        skipped_timeout = False

        # Pre-load caches to avoid thousands of individual DB queries
        cache = self._build_cache(instance)

        # Pre-fetch WooCommerce products by SKU for barcode reconciliation
        # Only needed if there are unmapped templates
        woo_sku_index = {}
        if cache['unmapped_tmpl_ids']:
            woo_sku_index = self._fetch_woo_sku_index(api)

        # Get template IDs to sync and process in chunks
        domain = safe_eval(instance.product_domain or "[]")
        domain += [('active', 'in', [True, False])]
        template_ids = self.env['product.template'].with_context(
            active_test=False).search(domain).ids

        for i in range(0, len(template_ids), CHUNK_SIZE):
            if time.time() - start_time > MAX_CRON_SECONDS:
                skipped_timeout = True
                _logger.warning(
                    "WooSync: Time limit reached after %d products, "
                    "remaining will be processed in next run",
                    success_count + error_count)
                break

            chunk_ids = template_ids[i:i + CHUNK_SIZE]
            templates = self.env['product.template'].with_context(
                active_test=False).browse(chunk_ids)
            # Prefetch to load all records in one query
            templates.mapped('name')

            for template in templates:
                if time.time() - start_time > MAX_CRON_SECONDS:
                    skipped_timeout = True
                    break
                try:
                    self._sync_one_template(
                        instance, api, template, cache, woo_sku_index)
                    self.env.cr.commit()
                    success_count += 1
                except Exception as e:
                    self.env.cr.rollback()
                    _logger.exception(
                        "WooSync: Sync failed for '%s' [ID: %s]",
                        template.name, template.id)
                    self._create_log(
                        instance, 'product', 'error',
                        product_tmpl_id=template.id,
                        message=f"Error: {str(e)[:500]}")
                    self.env.cr.commit()
                    error_count += 1

            # Clear ORM cache between chunks to free memory
            self.env.invalidate_all()
            cache = self._build_cache(instance)

        elapsed = round(time.time() - start_time, 1)
        msg = (f"Sync completo en {elapsed}s: {success_count} ok, "
               f"{error_count} errores")
        if skipped_timeout:
            msg += " (interrumpido por timeout, continuará en próximo cron)"
        _logger.info("WooSync: %s - %s", instance.name, msg)
        self._create_log(instance, 'full', 'success', message=msg)
        self.env.cr.commit()

    # -------------------------------------------------------------------------
    # SINGLE PRODUCT SYNC (MANUAL)
    # -------------------------------------------------------------------------

    def sync_specific_product(self, instance, product_tmpl):
        """Sync a single product immediately (manual trigger)."""
        api = instance._get_woo_api()
        # Build minimal cache for just this product
        cache = self._build_single_product_cache(instance, product_tmpl)
        
        # We don't need full SKU index for single update usually, unless creating
        # But if creating, we might want to check if it exists by SKU to avoid dupes.
        # Fetching ALL products is too slow for single sync. 
        # So we'll fetch just by this product's SKUs if creating.
        woo_sku_index = {}
        
        # Collect SKUs to check (barcode or default_code)
        skus_to_check = set()
        if product_tmpl.barcode:
            skus_to_check.add(product_tmpl.barcode)
        if product_tmpl.default_code:
            skus_to_check.add(product_tmpl.default_code)
            
        for variant in product_tmpl.product_variant_ids:
            if variant.barcode:
                skus_to_check.add(variant.barcode)
            if variant.default_code:
                skus_to_check.add(variant.default_code)
                
        if skus_to_check and not cache['tmpl_map'].get(product_tmpl.id):
            # Only check if not already mapped locally
            for sku in skus_to_check:
                try:
                    res = api.get('products', params={'sku': sku})
                    if res.status_code == 200:
                        products = res.json()
                        for p in products:
                             p_sku = (p.get('sku') or '').strip()
                             if p_sku:
                                 woo_sku_index[p_sku] = p
                except Exception:
                    pass

        try:
            self._sync_one_template(
                instance, api, product_tmpl, cache, woo_sku_index)
            # Find the log for this operation to link if needed, or just commit
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            _logger.exception(
                "WooSync: Manual sync failed for '%s' [ID: %s]",
                product_tmpl.name, product_tmpl.id)
            self._create_log(
                instance, 'product', 'error',
                product_tmpl_id=product_tmpl.id,
                message=f"Manual Error: {str(e)[:500]}")
            self.env.cr.commit()
            raise e

    def _build_single_product_cache(self, instance, product_tmpl):
        """Build a cache dict containing ONLY data relevant for one product."""
        # 1. Template mapping
        tmpl_mapping = self.env['woo.sync.template.mapping'].search([
            ('instance_id', '=', instance.id),
            ('product_tmpl_id', '=', product_tmpl.id),
        ], limit=1)
        
        tmpl_map = {product_tmpl.id: tmpl_mapping} if tmpl_mapping else {}
        
        # 2. Category mappings (only for this product's category and parents)
        cat_map = {}
        categ = product_tmpl.categ_id
        while categ:
            mapping = self.env['woo.sync.category.mapping'].search([
                ('instance_id', '=', instance.id),
                ('category_id', '=', categ.id),
            ], limit=1)
            if mapping:
                cat_map[categ.id] = mapping.woo_category_id
            categ = categ.parent_id

        # 3. Attribute mappings
        # Check attributes used by this product
        attr_map = {}
        val_map = {}
        
        for line in product_tmpl.attribute_line_ids:
            attr = line.attribute_id
            # Attribute Mapping
            a_map = self.env['woo.sync.attribute.mapping'].search([
                ('instance_id', '=', instance.id),
                ('attribute_id', '=', attr.id),
            ], limit=1)
            if a_map:
                attr_map[attr.id] = a_map.woo_attribute_id
            
            # Value Mappings
            for val in line.value_ids:
                v_map = self.env['woo.sync.attribute.value.mapping'].search([
                    ('instance_id', '=', instance.id),
                    ('attribute_value_id', '=', val.id),
                ], limit=1)
                if v_map:
                    val_map[val.id] = v_map.woo_term_id

        return {
            'tmpl_map': tmpl_map,
            'cat_map': cat_map,
            'attr_map': attr_map,
            'val_map': val_map,
            'unmapped_tmpl_ids': set() if tmpl_mapping else {product_tmpl.id},
        }


    # -------------------------------------------------------------------------
    # IN-MEMORY CACHES (avoid repeated DB queries)
    # -------------------------------------------------------------------------

    def _build_cache(self, instance):
        """Pre-load all mappings into dicts for fast lookup."""
        # Template mappings: odoo_tmpl_id → mapping record
        tmpl_mappings = self.env['woo.sync.template.mapping'].search([
            ('instance_id', '=', instance.id),
        ])
        tmpl_map = {}
        mapped_tmpl_ids = set()
        for m in tmpl_mappings:
            tmpl_map[m.product_tmpl_id.id] = m
            mapped_tmpl_ids.add(m.product_tmpl_id.id)

        # Category mappings: odoo_categ_id → woo_category_id
        cat_mappings = self.env['woo.sync.category.mapping'].search([
            ('instance_id', '=', instance.id),
        ])
        cat_map = {m.category_id.id: m.woo_category_id for m in cat_mappings}

        # Attribute mappings: odoo_attr_id → woo_attribute_id
        attr_mappings = self.env['woo.sync.attribute.mapping'].search([
            ('instance_id', '=', instance.id),
        ])
        attr_map = {m.attribute_id.id: m.woo_attribute_id
                    for m in attr_mappings}

        # Attribute value mappings: odoo_attr_val_id → woo_term_id
        val_mappings = self.env['woo.sync.attribute.value.mapping'].search([
            ('instance_id', '=', instance.id),
        ])
        val_map = {m.attribute_value_id.id: m.woo_term_id
                   for m in val_mappings}

        # All template IDs in Odoo (for detecting unmapped)
        domain = safe_eval(instance.product_domain or "[]")
        domain += [('active', '=', True)]
        all_tmpl_ids = set(self.env['product.template'].search(domain).ids)
        unmapped_tmpl_ids = all_tmpl_ids - mapped_tmpl_ids

        return {
            'tmpl_map': tmpl_map,
            'cat_map': cat_map,
            'attr_map': attr_map,
            'val_map': val_map,
            'unmapped_tmpl_ids': unmapped_tmpl_ids,
        }

    # -------------------------------------------------------------------------
    # PRE-FETCH WOOCOMMERCE SKU INDEX (for barcode reconciliation)
    # -------------------------------------------------------------------------

    def _fetch_woo_sku_index(self, api):
        """Fetch ALL WooCommerce products and build a SKU→product dict.
        This avoids making one API call per product for barcode matching.
        Paginates through all WC products (100 per page).
        """
        sku_index = {}
        page = 1
        _logger.info("WooSync: Fetching WooCommerce product index for "
                      "barcode reconciliation...")
        while True:
            try:
                res = api.get('products', params={
                    'per_page': 100,
                    'page': page,
                    'fields': 'id,sku,type',
                })
                if res.status_code != 200:
                    _logger.warning(
                        "WooSync: WC product fetch page %d returned %s",
                        page, res.status_code)
                    break
                products = res.json()
                if not products:
                    break
                for p in products:
                    sku = (p.get('sku') or '').strip()
                    if sku:
                        sku_index[sku] = p
                page += 1
            except Exception:
                _logger.exception(
                    "WooSync: Error fetching WC products page %d", page)
                break

        _logger.info("WooSync: WC index loaded: %d products with SKU",
                      len(sku_index))
        return sku_index

    # -------------------------------------------------------------------------
    # SYNC ONE TEMPLATE
    # -------------------------------------------------------------------------

    def _sync_one_template(self, instance, api, template, cache,
                           woo_sku_index):
        """Sync a single product template to WooCommerce."""
        mapping = cache['tmpl_map'].get(template.id)

        # Handle archived products
        if not template.active:
            if mapping and instance.sync_archived_as_draft:
                self._woo_put(api, f'products/{mapping.woo_product_id}',
                              {'status': 'draft'})
                mapping.last_sync_date = fields.Datetime.now()
            return

        is_variable = self._is_variable_product(template)

        if not mapping:
            self._create_woo_product(
                instance, api, template, is_variable, cache, woo_sku_index)
        else:
            self._update_woo_product(
                instance, api, template, mapping, is_variable, cache)

    # -------------------------------------------------------------------------
    # PRODUCT CREATION (with barcode reconciliation)
    # -------------------------------------------------------------------------

    def _create_woo_product(self, instance, api, template, is_variable,
                            cache, woo_sku_index):
        """Create new product in WC, or map existing one by barcode."""
        # Try barcode reconciliation against pre-fetched index
        existing = self._match_by_barcode(template, woo_sku_index)
        if existing:
            self._map_existing_woo_product(
                instance, api, template, existing, is_variable, cache)
            return

        if is_variable:
            self._create_variable_product(instance, api, template, cache)
        else:
            self._create_simple_product(instance, api, template, cache)

    def _match_by_barcode(self, template, woo_sku_index):
        """Match template against pre-fetched WC SKU index by barcode.
        Returns WC product dict if found, None otherwise.
        """
        if not woo_sku_index:
            return None

        # Check template barcode
        if template.barcode and template.barcode.strip() in woo_sku_index:
            return woo_sku_index[template.barcode.strip()]

        # Check variant barcodes
        for variant in template.product_variant_ids:
            if variant.barcode and variant.barcode.strip() in woo_sku_index:
                return woo_sku_index[variant.barcode.strip()]

        return None

    def _map_existing_woo_product(self, instance, api, template, woo_product,
                                  is_variable, cache):
        """Create mapping records for a WC product that already exists."""
        woo_id = woo_product['id']
        woo_type = woo_product.get('type', 'simple')
        is_woo_variable = woo_type == 'variable'

        tmpl_mapping = self.env['woo.sync.template.mapping'].create({
            'instance_id': instance.id,
            'product_tmpl_id': template.id,
            'woo_product_id': woo_id,
            'woo_product_type': 'variable' if is_woo_variable else 'simple',
            'last_sync_date': fields.Datetime.now(),
        })
        # Update cache
        cache['tmpl_map'][template.id] = tmpl_mapping

        if is_woo_variable:
            self._map_existing_variations(
                instance, api, template, tmpl_mapping, woo_id)
        else:
            variant = template.product_variant_ids[:1]
            if variant:
                self.env['woo.sync.variant.mapping'].create({
                    'instance_id': instance.id,
                    'template_mapping_id': tmpl_mapping.id,
                    'product_id': variant.id,
                    'woo_variation_id': 0,
                    'last_sync_date': fields.Datetime.now(),
                })

        self._create_log(
            instance, 'product', 'success',
            product_tmpl_id=template.id,
            message=(f"Mapeado a WC existente (WC ID: {woo_id}) por barcode"))

    def _map_existing_variations(self, instance, api, template,
                                 tmpl_mapping, woo_product_id):
        """Fetch WC variations and match to Odoo variants by barcode."""
        woo_variations = self._fetch_all_variations(api, woo_product_id)

        # Build lookup: WC SKU → WC variation
        woo_by_sku = {}
        for wv in woo_variations:
            sku = (wv.get('sku') or '').strip()
            if sku:
                woo_by_sku[sku] = wv

        for variant in template.product_variant_ids:
            barcode = (variant.barcode or '').strip()
            if barcode and barcode in woo_by_sku:
                self.env['woo.sync.variant.mapping'].create({
                    'instance_id': instance.id,
                    'template_mapping_id': tmpl_mapping.id,
                    'product_id': variant.id,
                    'woo_variation_id': woo_by_sku[barcode]['id'],
                    'last_sync_date': fields.Datetime.now(),
                })

    def _fetch_all_variations(self, api, woo_product_id):
        """Paginate through all variations of a WC product."""
        variations = []
        page = 1
        while True:
            try:
                res = api.get(
                    f'products/{woo_product_id}/variations',
                    params={'per_page': 100, 'page': page})
                if res.status_code != 200:
                    break
                batch = res.json()
                if not batch:
                    break
                variations.extend(batch)
                page += 1
            except Exception:
                break
        return variations

    # -------------------------------------------------------------------------
    # PRODUCT CREATION (NEW in WooCommerce)
    # -------------------------------------------------------------------------

    def _create_simple_product(self, instance, api, template, cache):
        """Create a simple product in WooCommerce."""
        variant = template.product_variant_ids[:1]
        if not variant:
            return

        data = {
            'name': template.name,
            'type': 'simple',
            'sku': variant.barcode or variant.default_code or '',
            'regular_price': str(
                round(instance._get_product_price(variant), 2)),
            'description': template.description or '',
            'short_description': template.description_sale or '',
            'manage_stock': True,
            'stock_quantity': instance._get_product_qty(variant),
            'weight': str(template.weight) if template.weight else '',
            'status': instance.default_woo_status,
            'categories': self._get_woo_categories(
                instance, api, template, cache),
            'images': self._get_woo_images(template),
        }

        result = self._woo_post(api, 'products', data)
        woo_id = result.get('id')
        if not woo_id:
            raise Exception(
                f"No se pudo crear: {result.get('message', result)}")

        tmpl_mapping = self.env['woo.sync.template.mapping'].create({
            'instance_id': instance.id,
            'product_tmpl_id': template.id,
            'woo_product_id': woo_id,
            'woo_product_type': 'simple',
            'last_sync_date': fields.Datetime.now(),
        })
        cache['tmpl_map'][template.id] = tmpl_mapping

        self.env['woo.sync.variant.mapping'].create({
            'instance_id': instance.id,
            'template_mapping_id': tmpl_mapping.id,
            'product_id': variant.id,
            'woo_variation_id': 0,
            'last_sync_date': fields.Datetime.now(),
        })

        self._create_log(
            instance, 'product', 'success',
            product_tmpl_id=template.id,
            message=f"Creado simple (WC ID: {woo_id})")

    def _create_variable_product(self, instance, api, template, cache):
        """Create a variable product with variations in WooCommerce."""
        attributes = self._build_woo_attribute_lines(
            instance, api, template, cache)

        data = {
            'name': template.name,
            'type': 'variable',
            'description': template.description or '',
            'short_description': template.description_sale or '',
            'manage_stock': False,
            'status': instance.default_woo_status,
            'weight': str(template.weight) if template.weight else '',
            'categories': self._get_woo_categories(
                instance, api, template, cache),
            'images': self._get_woo_images(template),
            'attributes': attributes,
        }

        result = self._woo_post(api, 'products', data)
        woo_id = result.get('id')
        if not woo_id:
            raise Exception(
                f"No se pudo crear variable: {result.get('message', result)}")

        tmpl_mapping = self.env['woo.sync.template.mapping'].create({
            'instance_id': instance.id,
            'product_tmpl_id': template.id,
            'woo_product_id': woo_id,
            'woo_product_type': 'variable',
            'last_sync_date': fields.Datetime.now(),
        })
        cache['tmpl_map'][template.id] = tmpl_mapping

        # Create variations in batches
        variations_data = []
        variant_list = []
        for variant in template.product_variant_ids:
            var_data = self._build_variation_data(instance, api, variant, cache)
            variations_data.append(var_data)
            variant_list.append(variant)

        # Use batch API for creating variations (up to 100 at a time)
        batch_size = min(instance.batch_size, 100)
        for i in range(0, len(variations_data), batch_size):
            batch_data = variations_data[i:i + batch_size]
            batch_variants = variant_list[i:i + batch_size]
            result = self._woo_post(
                api, f'products/{woo_id}/variations/batch',
                {'create': batch_data})
            for idx, created in enumerate(result.get('create', [])):
                if created.get('id') and idx < len(batch_variants):
                    self.env['woo.sync.variant.mapping'].create({
                        'instance_id': instance.id,
                        'template_mapping_id': tmpl_mapping.id,
                        'product_id': batch_variants[idx].id,
                        'woo_variation_id': created['id'],
                        'last_sync_date': fields.Datetime.now(),
                    })

        self._create_log(
            instance, 'product', 'success',
            product_tmpl_id=template.id,
            message=(f"Creado variable (WC ID: {woo_id}) con "
                     f"{len(template.product_variant_ids)} variaciones"))

    # -------------------------------------------------------------------------
    # PRODUCT UPDATE
    # -------------------------------------------------------------------------

    def _update_woo_product(self, instance, api, template, mapping,
                            is_variable, cache):
        """Update an existing product in WooCommerce."""
        variant = template.product_variant_ids[:1]
        if not variant:
            return

        if is_variable:
            data = {
                'name': template.name,
                'description': template.description or '',
                'short_description': template.description_sale or '',
                'status': instance.default_woo_status,
                'weight': str(template.weight) if template.weight else '',
                'categories': self._get_woo_categories(
                    instance, api, template, cache),
                'images': self._get_woo_images(template),
                'attributes': self._build_woo_attribute_lines(
                    instance, api, template, cache),
            }
        else:
            data = {
                'name': template.name,
                'sku': variant.barcode or variant.default_code or '',
                'regular_price': str(
                    round(instance._get_product_price(variant), 2)),
                'description': template.description or '',
                'short_description': template.description_sale or '',
                'manage_stock': True,
                'stock_quantity': instance._get_product_qty(variant),
                'status': instance.default_woo_status,
                'weight': str(template.weight) if template.weight else '',
                'categories': self._get_woo_categories(
                    instance, api, template, cache),
                'images': self._get_woo_images(template),
            }

        result = self._woo_put(
            api, f'products/{mapping.woo_product_id}', data)

        if result.get('id'):
            mapping.last_sync_date = fields.Datetime.now()
        else:
            if self._is_not_found(result):
                mapping.unlink()
                cache['tmpl_map'].pop(template.id, None)
                self._create_woo_product(
                    instance, api, template, is_variable, cache, {})
                return
            raise Exception(
                f"Error actualizando: {result.get('message', result)}")

        if is_variable:
            self._update_variations(instance, api, template, mapping, cache)

    def _update_variations(self, instance, api, template, tmpl_mapping, cache):
        """Sync variations using batch API."""
        existing_var_mappings = {
            vm.product_id.id: vm
            for vm in tmpl_mapping.variant_mapping_ids
        }

        update_list = []
        create_list = []

        for variant in template.product_variant_ids:
            var_data = self._build_variation_data(instance, api, variant, cache)
            vm = existing_var_mappings.pop(variant.id, None)
            if vm:
                var_data['id'] = vm.woo_variation_id
                update_list.append((vm, var_data))
            else:
                create_list.append((variant, var_data))

        delete_ids = [
            vm.woo_variation_id for vm in existing_var_mappings.values()]

        woo_product_id = tmpl_mapping.woo_product_id
        batch_size = min(instance.batch_size, 100)

        # Batch updates
        for i in range(0, len(update_list), batch_size):
            batch = update_list[i:i + batch_size]
            payload = {'update': [d for _, d in batch]}
            result = self._woo_post(
                api, f'products/{woo_product_id}/variations/batch', payload)
            for item in result.get('update', []):
                if item.get('id'):
                    vm = next(
                        (m for m, _ in batch
                         if m.woo_variation_id == item['id']), None)
                    if vm:
                        vm.last_sync_date = fields.Datetime.now()

        # Batch creates
        for i in range(0, len(create_list), batch_size):
            batch = create_list[i:i + batch_size]
            payload = {'create': [d for _, d in batch]}
            result = self._woo_post(
                api, f'products/{woo_product_id}/variations/batch', payload)
            for idx, created in enumerate(result.get('create', [])):
                if created.get('id') and idx < len(batch):
                    variant, _ = batch[idx]
                    self.env['woo.sync.variant.mapping'].create({
                        'instance_id': instance.id,
                        'template_mapping_id': tmpl_mapping.id,
                        'product_id': variant.id,
                        'woo_variation_id': created['id'],
                        'last_sync_date': fields.Datetime.now(),
                    })

        # Batch deletes
        if delete_ids:
            for i in range(0, len(delete_ids), batch_size):
                self._woo_post(
                    api, f'products/{woo_product_id}/variations/batch',
                    {'delete': delete_ids[i:i + batch_size]})
            self.env['woo.sync.variant.mapping'].search([
                ('template_mapping_id', '=', tmpl_mapping.id),
                ('woo_variation_id', 'in', delete_ids),
            ]).unlink()

    # -------------------------------------------------------------------------
    # STOCK & PRICE SYNC (LIGHTWEIGHT CRON)
    # -------------------------------------------------------------------------

    def _run_stock_price_sync(self, instance):
        """Lightweight sync: only update stock and price for mapped products.
        Uses batch API for maximum efficiency."""
        api = instance._get_woo_api()
        batch_size = min(instance.batch_size, 100)
        start_time = time.time()

        # --- Simple products (batch by 100) ---
        simple_mappings = self.env['woo.sync.template.mapping'].search([
            ('instance_id', '=', instance.id),
            ('woo_product_type', '=', 'simple'),
            ('product_tmpl_id.active', '=', True),
        ])

        simple_batch = []
        for mapping in simple_mappings:
            variant = mapping.product_tmpl_id.product_variant_ids[:1]
            if not variant:
                continue
            simple_batch.append({
                'id': mapping.woo_product_id,
                'regular_price': str(
                    round(instance._get_product_price(variant), 2)),
                'stock_quantity': instance._get_product_qty(variant),
                'manage_stock': True,
            })

        for i in range(0, len(simple_batch), batch_size):
            batch = simple_batch[i:i + batch_size]
            try:
                self._woo_post(api, 'products/batch', {'update': batch})
            except Exception as e:
                _logger.exception(
                    "WooSync: Batch stock/price failed (simple batch %d)",
                    i // batch_size)
                self._create_log(
                    instance, 'stock', 'error',
                    message=f"Error batch simples: {str(e)[:300]}")
                self.env.cr.commit()

        # --- Variable products (batch variations per product) ---
        variable_mappings = self.env['woo.sync.template.mapping'].search([
            ('instance_id', '=', instance.id),
            ('woo_product_type', '=', 'variable'),
            ('product_tmpl_id.active', '=', True),
        ])

        for tmpl_mapping in variable_mappings:
            try:
                variations_data = []
                for vm in tmpl_mapping.variant_mapping_ids:
                    if not vm.product_id.active:
                        continue
                    variations_data.append({
                        'id': vm.woo_variation_id,
                        'regular_price': str(
                            round(instance._get_product_price(
                                vm.product_id), 2)),
                        'stock_quantity': instance._get_product_qty(
                            vm.product_id),
                        'manage_stock': True,
                    })

                for i in range(0, len(variations_data), batch_size):
                    batch = variations_data[i:i + batch_size]
                    self._woo_post(
                        api,
                        f'products/{tmpl_mapping.woo_product_id}'
                        f'/variations/batch',
                        {'update': batch})

                self.env.cr.commit()
            except Exception as e:
                self.env.cr.rollback()
                _logger.exception(
                    "WooSync: Stock/price failed for '%s'",
                    tmpl_mapping.product_tmpl_id.name)
                self._create_log(
                    instance, 'stock', 'error',
                    product_tmpl_id=tmpl_mapping.product_tmpl_id.id,
                    message=f"Error variaciones: {str(e)[:300]}")
                self.env.cr.commit()

        elapsed = round(time.time() - start_time, 1)
        _logger.info(
            "WooSync: Stock/price sync done for '%s' in %ss "
            "(%d simple, %d variable)",
            instance.name, elapsed,
            len(simple_mappings), len(variable_mappings))

    # -------------------------------------------------------------------------
    # CATEGORY SYNC (with cache)
    # -------------------------------------------------------------------------

    def _ensure_category_synced(self, instance, api, category, cache):
        """Recursively ensure a category exists in WC. Uses cache."""
        woo_id = cache['cat_map'].get(category.id)
        if woo_id:
            return woo_id

        # Sync parent first
        woo_parent_id = 0
        if category.parent_id:
            woo_parent_id = self._ensure_category_synced(
                instance, api, category.parent_id, cache)

        data = {'name': category.name, 'parent': woo_parent_id}
        result = self._woo_post(api, 'products/categories', data)
        woo_id = result.get('id')

        if not woo_id:
            woo_id = self._find_woo_category_by_name(
                api, category.name, woo_parent_id)
            if not woo_id:
                raise Exception(
                    f"No se pudo crear categoría '{category.name}': "
                    f"{result.get('message', result)}")

        self.env['woo.sync.category.mapping'].create({
            'instance_id': instance.id,
            'category_id': category.id,
            'woo_category_id': woo_id,
        })
        cache['cat_map'][category.id] = woo_id
        return woo_id

    def _find_woo_category_by_name(self, api, name, parent_id=0):
        """Search for existing WC category by name."""
        try:
            res = api.get('products/categories', params={
                'search': name, 'parent': parent_id, 'per_page': 10})
            if res.status_code == 200:
                for cat in res.json():
                    if cat.get('name', '').lower() == name.lower():
                        return cat['id']
        except Exception:
            pass
        return None

    def _get_woo_categories(self, instance, api, template, cache):
        """Get WC category IDs for a template."""
        categories = []
        if template.categ_id:
            woo_id = self._ensure_category_synced(
                instance, api, template.categ_id, cache)
            categories.append({'id': woo_id})
        return categories

    # -------------------------------------------------------------------------
    # ATTRIBUTE SYNC (with cache)
    # -------------------------------------------------------------------------

    def _ensure_attribute_synced(self, instance, api, attribute, cache):
        """Ensure attribute exists in WC. Uses cache."""
        woo_id = cache['attr_map'].get(attribute.id)
        if woo_id:
            return woo_id

        data = {
            'name': attribute.name,
            'type': 'select',
            'order_by': 'menu_order',
            'has_archives': True,
        }
        result = self._woo_post(api, 'products/attributes', data)
        woo_id = result.get('id')

        if not woo_id:
            woo_id = self._find_woo_attribute_by_name(api, attribute.name)
            if not woo_id:
                raise Exception(
                    f"No se pudo crear atributo '{attribute.name}': "
                    f"{result.get('message', result)}")

        self.env['woo.sync.attribute.mapping'].create({
            'instance_id': instance.id,
            'attribute_id': attribute.id,
            'woo_attribute_id': woo_id,
        })
        cache['attr_map'][attribute.id] = woo_id
        return woo_id

    def _find_woo_attribute_by_name(self, api, name):
        """Search for existing WC attribute by name."""
        try:
            res = api.get('products/attributes', params={'per_page': 100})
            if res.status_code == 200:
                for attr in res.json():
                    if attr.get('name', '').lower() == name.lower():
                        return attr['id']
        except Exception:
            pass
        return None

    def _ensure_attribute_value_synced(self, instance, api, attr_value,
                                       woo_attr_id, cache):
        """Ensure attribute value term exists in WC. Uses cache."""
        woo_id = cache['val_map'].get(attr_value.id)
        if woo_id:
            return woo_id

        data = {'name': attr_value.name}
        result = self._woo_post(
            api, f'products/attributes/{woo_attr_id}/terms', data)
        woo_id = result.get('id')

        if not woo_id:
            woo_id = self._find_woo_term_by_name(
                api, woo_attr_id, attr_value.name)
            if not woo_id:
                raise Exception(
                    f"No se pudo crear término '{attr_value.name}': "
                    f"{result.get('message', result)}")

        self.env['woo.sync.attribute.value.mapping'].create({
            'instance_id': instance.id,
            'attribute_value_id': attr_value.id,
            'woo_term_id': woo_id,
            'woo_attribute_id': woo_attr_id,
        })
        cache['val_map'][attr_value.id] = woo_id
        return woo_id

    def _find_woo_term_by_name(self, api, woo_attr_id, name):
        """Search for existing WC attribute term by name."""
        try:
            res = api.get(
                f'products/attributes/{woo_attr_id}/terms',
                params={'per_page': 100})
            if res.status_code == 200:
                for term in res.json():
                    if term.get('name', '').lower() == name.lower():
                        return term['id']
        except Exception:
            pass
        return None

    def _build_woo_attribute_lines(self, instance, api, template, cache):
        """Build WC 'attributes' list for a variable product."""
        attribute_list = []
        for idx, attr_line in enumerate(template.attribute_line_ids):
            woo_attr_id = self._ensure_attribute_synced(
                instance, api, attr_line.attribute_id, cache)
            for val in attr_line.value_ids:
                self._ensure_attribute_value_synced(
                    instance, api, val, woo_attr_id, cache)
            attribute_list.append({
                'id': woo_attr_id,
                'name': attr_line.attribute_id.name,
                'position': idx,
                'visible': True,
                'variation': True,
                'options': [v.name for v in attr_line.value_ids],
            })
        return attribute_list

    # -------------------------------------------------------------------------
    # VARIATION DATA
    # -------------------------------------------------------------------------

    def _build_variation_data(self, instance, api, variant, cache):
        """Build data dict for a single WC variation."""
        attrs = []
        for ptav in variant.product_template_attribute_value_ids:
            woo_attr_id = self._ensure_attribute_synced(
                instance, api, ptav.attribute_id, cache)
            attrs.append({
                'id': woo_attr_id,
                'name': ptav.attribute_id.name,
                'option': ptav.product_attribute_value_id.name,
            })
        return {
            'regular_price': str(
                round(instance._get_product_price(variant), 2)),
            'sku': variant.barcode or variant.default_code or '',
            'manage_stock': True,
            'stock_quantity': instance._get_product_qty(variant),
            'weight': str(variant.weight) if variant.weight else '',
            'attributes': attrs,
        }

    # -------------------------------------------------------------------------
    # IMAGES
    # -------------------------------------------------------------------------

    def _get_woo_images(self, template):
        """Build images list for WooCommerce."""
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url')
        images = []
        if template.image_1920:
            image_name = (template.name or 'product').replace('/', '-')
            images.append({
                'src': (f'{base_url}/web/image/product.template/'
                        f'{template.id}/image_1920/{image_name}.png'),
                'position': 0,
            })
        return images

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _is_variable_product(self, template):
        """Determine if template should be variable in WooCommerce."""
        return (
            bool(template.attribute_line_ids)
            and len(template.product_variant_ids) > 1
        )

    def _woo_post(self, api, endpoint, data):
        """POST to WooCommerce API and return parsed JSON."""
        try:
            res = api.post(endpoint, data)
            result = res.json()
            if res.status_code >= 400:
                _logger.warning(
                    "WooSync: POST %s → %s", endpoint, res.status_code)
            return result
        except Exception:
            _logger.exception("WooSync: POST %s failed", endpoint)
            raise

    def _woo_put(self, api, endpoint, data):
        """PUT to WooCommerce API and return parsed JSON."""
        try:
            res = api.put(endpoint, data)
            result = res.json()
            if res.status_code >= 400:
                _logger.warning(
                    "WooSync: PUT %s → %s", endpoint, res.status_code)
            return result
        except Exception:
            _logger.exception("WooSync: PUT %s failed", endpoint)
            raise

    def _is_not_found(self, result):
        """Check if a WC API response is a 404."""
        if isinstance(result, dict):
            return result.get('data', {}).get('status') == 404
        return False

    def _create_log(self, instance, sync_type, status, product_tmpl_id=None,
                    product_id=None, message=None):
        """Create a sync log entry."""
        self.env['woo.sync.log'].sudo().create({
            'instance_id': instance.id,
            'sync_type': sync_type,
            'status': status,
            'product_tmpl_id': product_tmpl_id,
            'product_id': product_id,
            'message': message,
        })
