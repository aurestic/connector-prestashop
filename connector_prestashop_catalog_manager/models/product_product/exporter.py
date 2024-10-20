# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.connector.components.mapper import mapping, changed_by
from odoo.addons.component.core import Component
from collections import OrderedDict
import logging

_logger = logging.getLogger(__name__)


class ProductCombinationExporter(Component):
    _name = 'prestashop.product.combination.exporter'
    _inherit = 'translation.prestashop.exporter'
    _apply_on = 'prestashop.product.combination'

    def _create(self, record):
        """
        :param record: browse record to create in prestashop
        :return integer: Prestashop record id
        """
        res = super(ProductCombinationExporter, self)._create(record)
        return res['prestashop']['combination']['id']

    def _export_images(self):
        if self.binding.image_ids:
            image_binder = self.binder_for('prestashop.product.image')
            for image_line in self.binding.image_ids:
                image_ext_id = image_binder.to_external(
                    image_line.id, wrap=True)
                if not image_ext_id:
                    image_ext = \
                        self.env['prestashop.product.image']\
                            .with_context(connector_no_export=True).create({
                                'backend_id': self.backend_record.id,
                                'odoo_id': image_line.id,
                            })
                    image_content = getattr(image_line, "_get_image_from_%s" %
                                            image_line.storage)()
                    image_ext.export_record(
                        image_content)

    def _export_dependencies(self):
        """ Export the dependencies for the product"""
        # TODO add export of category
        attribute_binder = self.binder_for(
            'prestashop.product.combination.option')
        option_binder = self.binder_for(
            'prestashop.product.combination.option.value')
        for value in self.binding.attribute_value_ids:
            attribute_ext_id = attribute_binder.to_external(
                value.attribute_id.id, wrap=True)
            if not attribute_ext_id:
                attribute_ext = self.env[
                    'prestashop.product.combination.option'].with_context(
                    connector_no_export=True).create({
                        'backend_id': self.backend_record.id,
                        'odoo_id': value.attribute_id.id,
                    })
                attribute_ext.export_record()
            value_ext_id = option_binder.to_external(value.id, wrap=True)
            if not value_ext_id:
                value_ext = self.env[
                    'prestashop.product.combination.option.value']\
                    .with_context(connector_no_export=True).create({
                        'backend_id': self.backend_record.id,
                        'odoo_id': value.val_id.id,
                        'id_attribute_group': attribute_ext_id
                    })
                value_ext.export_record()
        self._export_images()

    def update_quantities(self):
        self.binding.odoo_id.with_context(
            self.env.context).update_prestashop_qty()

    def _after_export(self):
        self.update_quantities()


class ProductCombinationExportMapper(Component):
    _name = 'prestashop.product.combination.export.mapper'
    _inherit = 'translation.prestashop.export.mapper'
    _apply_on = 'prestashop.product.combination'

    direct = [
        ('default_code', 'reference'),
        ('active', 'active'),
        ('barcode', 'ean13'),
        ('minimal_quantity', 'minimal_quantity'),
    ]

    def _get_factor_tax(self, tax):
        factor_tax = tax.price_include and (1 + tax.amount / 100) or 1.0
        return factor_tax

    @mapping
    def combination_default(self, record):
        return {'default_on': int(record['default_on'])}

    def get_main_template_id(self, record):
        template_binder = self.binder_for('prestashop.product.template')
        return template_binder.to_external(record.main_template_id.id)

    @mapping
    def main_template_id(self, record):
        return {'id_product': self.get_main_template_id(record)}

    @mapping
    def _unit_price_impact(self, record):
        tax = record.taxes_id[:1]
        if tax.price_include and tax.amount_type == 'percent':
            # 6 is the rounding precision used by PrestaShop for the
            # tax excluded price.  we can get back a 2 digits tax included
            # price from the 6 digits rounded value
            return {
                'price': round(
                    record.impact_price / self._get_factor_tax(tax), 6)
            }
        else:
            return {'price': record.impact_price}

    @mapping
    def cost_price(self, record):
        return {'wholesale_price': float('{:.2f}'.format(record.standard_price))}

    @mapping
    def weight(self, record):
        return {'weight': round(record.weight, 3)}

    def _get_product_option_value(self, record):
        option_value = []
        option_binder = self.binder_for(
            'prestashop.product.combination.option.value')
        for value in record.attribute_value_ids:
            value_ext_id = option_binder.to_external(value.id, wrap=True)
            if value_ext_id:
                option_value.append({'id': value_ext_id})
        return option_value

    def _get_combination_image(self, record):
        images = []
        image_binder = self.binder_for('prestashop.product.image')
        for image in record.image_ids:
            image_ext_id = image_binder.to_external(image.id, wrap=True)
            if image_ext_id:
                images.append({'id': image_ext_id})
        return images

    @changed_by('attribute_value_ids', 'image_ids')
    @mapping
    def associations(self, record):
        return {
            'associations': {
                'product_option_values': {
                    'product_option_value': self._get_product_option_value(record)
                },
                'images': {
                    'image': self._get_combination_image(record)
                }
            }
        }


class ProductCombinationOptionExporter(Component):
    _name = 'prestashop.product.combination.option.exporter'
    _inherit = 'prestashop.exporter'
    _apply_on = 'prestashop.product.combination.option'

    def _create(self, record):
        res = super(ProductCombinationOptionExporter, self)._create(record)
        return res['prestashop']['product_option']['id']


class ProductCombinationOptionExportMapper(Component):
    _name = 'prestashop.product.combination.option.export.mapper'
    _inherit = 'translation.prestashop.export.mapper'
    _apply_on = 'prestashop.product.combination.option'

    direct = [
        ('prestashop_position', 'position'),
        ('group_type', 'group_type'),
    ]

    _translatable_fields = [
        ('name', 'name'),
        ('name', 'public_name'),
    ]


class ProductCombinationOptionValueExporter(Component):
    _name = 'prestashop.product.combination.option.value.exporter'
    _inherit = 'prestashop.exporter'
    _apply_on = 'prestashop.product.combination.option.value'

    def _create(self, record):
        res = super(ProductCombinationOptionValueExporter,
                    self)._create(record)
        return res['prestashop']['product_option_value']['id']

    def _export_dependencies(self):
        """ Export the dependencies for the record"""
        attribute_id = self.binding.attribute_id.id
        # export product attribute
        attr_model = 'prestashop.product.combination.option'
        binder = self.binder_for(attr_model)
        if not binder.to_external(attribute_id, wrap=True):
            with self.backend_id.work_on(attr_model) as work:
                exporter = work.component(usage='record.exporter')
                exporter.run(attribute_id)
        return


class ProductCombinationOptionValueExportMapper(Component):
    _name = 'prestashop.product.combination.option.value.export.mapper'
    _inherit = 'translation.prestashop.export.mapper'
    _apply_on = 'prestashop.product.combination.option.value'

    direct = [('name', 'value')]
    # handled by base mapping `translatable_fields`
    _translatable_fields = [
        ('name', 'name'),
    ]

    @mapping
    def prestashop_product_attribute_id(self, record):
        attribute_binder = self.binder_for(
            'prestashop.product.combination.option.value')
        return {
            'id_feature': attribute_binder.to_external(
                record.attribute_id.id, wrap=True)
        }

    @mapping
    def prestashop_product_group_attribute_id(self, record):
        attribute_binder = self.binder_for(
            'prestashop.product.combination.option')
        return {
            'id_attribute_group': attribute_binder.to_external(
                record.attribute_id.id, wrap=True),
        }
