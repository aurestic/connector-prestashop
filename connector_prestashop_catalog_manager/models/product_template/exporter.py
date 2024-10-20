# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from datetime import timedelta

from odoo.addons.connector.components.mapper import (
    mapping, m2o_to_external, changed_by)
from odoo.addons.component.core import Component

import unicodedata
import re

try:
    import slugify as slugify_lib
except ImportError:
    slugify_lib = None


def get_slug(name):
    if slugify_lib:
        try:
            return slugify_lib.slugify(name)
        except TypeError:
            pass
    uni = unicodedata.normalize('NFKD', name).encode(
        'ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[\W_]', ' ', uni).strip().lower()
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug


class ProductTemplateExporter(Component):
    _name = 'prestashop.product.template.exporter'
    _inherit = 'translation.prestashop.exporter'
    _apply_on = 'prestashop.product.template'

    def _create(self, record):
        res = super(ProductTemplateExporter, self)._create(record)
        return res['prestashop']['product']['id']

    def _update(self, data):
        """ Update an Prestashop record """
        assert self.prestashop_id
        self.export_variants()
        self.check_images()
        self.backend_adapter.write(self.prestashop_id, data)

    def export_categories(self, category):
        if not category:
            return
        category_binder = self.binder_for('prestashop.product.category')
        ext_id = category_binder.to_external(category, wrap=True)
        if ext_id:
            return ext_id

        ps_categ_obj = self.env['prestashop.product.category']
        position_cat_id = ps_categ_obj.search(
            [], order='position desc', limit=1)
        obj_position = position_cat_id.position + 1
        res = {
            'backend_id': self.backend_record.id,
            'odoo_id': category.id,
            'link_rewrite': get_slug(category.name),
            'position': obj_position,
        }
        binding = ps_categ_obj.with_context(
            connector_no_export=True).create(res)
        binding.export_record()

    def _parent_length(self, categ):
        if not categ.parent_id:
            return 1
        else:
            return 1 + self._parent_length(categ.parent_id)

    def _export_dependencies(self):
        """ Export the dependencies for the product"""
        super(ProductTemplateExporter, self)._export_dependencies()
        attribute_binder = self.binder_for(
            'prestashop.product.combination.option')
        option_binder = self.binder_for(
            'prestashop.product.combination.option.value')

        for category in self.binding.categ_ids:
            self.export_categories(category)

        for line in self.binding.attribute_line_ids:
            attribute_ext_id = attribute_binder.to_external(
                line.attribute_id, wrap=True)
            if not attribute_ext_id:
                self._export_dependency(
                    line.attribute_id,
                    'prestashop.product.combination.option')
            for value in line.value_ids:
                value_ext_id = option_binder.to_external(value, wrap=True)
                if not value_ext_id:
                    self._export_dependency(
                        value, 'prestashop.product.combination.option.value')

    def export_variants(self):
        combination_obj = self.env['prestashop.product.combination']
        for product in self.binding.product_variant_ids:
            if not product.attribute_value_ids:
                continue
            combination = combination_obj.search([
                ('backend_id', '=', self.backend_record.id),
                ('odoo_id', '=', product.id),
            ], limit=1)
            if not combination:
                combination = combination_obj.with_context(
                    connector_no_export=True).create({
                        'backend_id': self.backend_record.id,
                        'odoo_id': product.id,
                        'main_template_id': self.binding_id,
                    })
                # sólo lo exportamos si se ha creado uno nuevo y
                # con la función nueva export_record_saving_prestashop_id
                combination.with_delay(
                    priority=50,
                    eta=timedelta(seconds=20)
                ).export_record_saving_prestashop_id()

    def _not_in_variant_images(self, image):
        images = []
        if len(self.binding.product_variant_ids) > 1:
            for product in self.binding.product_variant_ids:
                images.extend(product.image_ids.ids)
        return image.id not in images

    def check_images(self):
        if self.binding.image_ids:
            image_binder = self.binder_for('prestashop.product.image')
            for image in self.binding.image_ids:
                image_ext_id = image_binder.to_external(image, wrap=True)
                # `image_ext_id` is ZERO as long as the image is not exported.
                # Here we delay the export so,
                # if we don't check this we create 2 records to be sync'ed
                # and this leads to:
                # ValueError:
                #   Expected singleton: prestashop.product.image(x, y)
                if image_ext_id is None:
                    image_ext = self.env[
                        'prestashop.product.image'].with_context(
                        connector_no_export=True).create({
                            'backend_id': self.backend_record.id,
                            'odoo_id': image.id,
                        })
                    image_ext.with_delay(priority=5).export_record()

    def update_quantities(self):
        if len(self.binding.product_variant_ids) == 1:
            product = self.binding.odoo_id.product_variant_ids[0]
            product.update_prestashop_quantities()

    def _after_export(self):
        self.check_images()
        self.export_variants()
        self.update_quantities()
        if not self.binding.date_add:
            self.binding.with_context(
                connector_no_export=True).date_add = fields.Datetime.now()


class ProductTemplateExportMapper(Component):
    _name = 'prestashop.product.template.export.mapper'
    _inherit = 'translation.prestashop.export.mapper'
    _apply_on = 'prestashop.product.template'

    direct = [
        ('available_for_order', 'available_for_order'),
        ('show_price', 'show_price'),
        ('online_only', 'online_only'),
        ('standard_price', 'wholesale_price'),
        (m2o_to_external('default_shop_id'), 'id_shop_default'),
        ('always_available', 'active'),
        ('barcode', 'barcode'),
        ('additional_shipping_cost', 'additional_shipping_cost'),
        ('minimal_quantity', 'minimal_quantity'),
        ('on_sale', 'on_sale'),
        ('date_add', 'date_add'),
        ('barcode', 'ean13'),
        (m2o_to_external(
            'prestashop_default_category_id',
            binding='prestashop.product.category'), 'id_category_default'),
        ('state', 'state'),
    ]
    # handled by base mapping `translatable_fields`
    _translatable_fields = [
        ('name', 'name'),
        ('link_rewrite', 'link_rewrite'),
        ('meta_title', 'meta_title'),
        ('meta_description', 'meta_description'),
        ('meta_keywords', 'meta_keywords'),
        ('tags', 'tags'),
        ('available_now', 'available_now'),
        ('available_later', 'available_later'),
        ('description_short_html', 'description_short'),
        ('description_html', 'description'),
    ]

    def _get_factor_tax(self, tax):
        return (1 + tax.amount / 100) if tax.price_include else 1.0

    @changed_by('taxes_id', 'list_price', 'lst_price')
    @mapping
    def list_price(self, record):
        tax = record.taxes_id
        if tax.price_include and tax.amount_type == 'percent':
            # 6 is the rounding precision used by PrestaShop for the
            # tax excluded price.  we can get back a 2 digits tax included
            # price from the 6 digits rounded value
            return {
                'price': str(
                    round(record.lst_price / self._get_factor_tax(tax), 6))
            }
        else:
            return {'price': str(round(record.lst_price, 6))}

    @changed_by('default_code', 'reference')
    @mapping
    def reference(self, record):
        return {'reference': record.reference or record.default_code or ''}

    def _get_product_category(self, record):
        ext_categ_ids = []
        binder = self.binder_for('prestashop.product.category')
        for category in record.categ_ids:
            ext_categ_ids.append(
                {'id': binder.to_external(category, wrap=True)})
        return ext_categ_ids


    # To extend in connector_prestashop_feature module. In this way we
    # dependencies on other modules like product_custom_info
    # see class FeaturesProductImportMapper

    # def _get_template_feature(self, record):
    #     template_feature = []
    #     attribute_binder = self.binder_for(
    #         'prestashop.product.combination.option')
    #     option_binder = self.binder_for(
    #         'prestashop.product.combination.option.value')
    #     for line in record.attribute_line_ids:
    #         feature_dict = {}
    #         attribute_ext_id = attribute_binder.to_external(
    #             line.attribute_id.id, wrap=True)
    #         if not attribute_ext_id:
    #             continue
    #         feature_dict = {'id': attribute_ext_id, 'custom': ''}
    #         values_ids = []
    #         for value in line.value_ids:
    #             value_ext_id = option_binder.to_external(value.id,
    #                                                      wrap=True)
    #             if not value_ext_id:
    #                 continue
    #             values_ids.append(value_ext_id)
    #         res = {'id_feature_value': values_ids}
    #         feature_dict.update(res)
    #         template_feature.append(feature_dict)
    #     return template_feature

    @changed_by(
        'attribute_line_ids', 'categ_ids', 'categ_id'
    )
    @mapping
    def associations(self, record):
        return {
            'associations': {
                'categories': {
                    'category_id': self._get_product_category(record)},
                # 'product_features': {
                #     'product_feature': self._get_template_feature(record)},
            }
        }

    # TOREVIEW: Tax rules group is not the same that odoo tax groups
    # @changed_by('taxes_id')
    # @mapping
    # def tax_ids(self, record):
    #     if not record.taxes_id:
    #         return
    #     binder = self.binder_for('prestashop.account.tax.group')
    #     ext_id = binder.to_external(
    #         record.taxes_id[:1].tax_group_id, wrap=True)
    #     return {'id_tax_rules_group': ext_id}

    @changed_by('available_date')
    @mapping
    def available_date(self, record):
        if record.available_date:
            return {'available_date': record.available_date}
        return {}

    @changed_by('weight')
    @mapping
    def weight(self, record):
        return {'weight': round(record.weight, 3)}

    # @mapping
    # def default_image(self, record):
    #     default_image = record.image_ids.filtered('front_image')[:1]
    #     if default_image:
    #         binder = self.binder_for('prestashop.product.image')
    #         ps_image_id = binder.to_external(default_image, wrap=True)
    #         if ps_image_id:
    #             return {'id_default_image': ps_image_id}
