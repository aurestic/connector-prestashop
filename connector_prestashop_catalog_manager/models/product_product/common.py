# © 2016 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import models, fields
from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if


class PrestashopProductCombination(models.Model):
    _inherit = 'prestashop.product.combination'
    minimal_quantity = fields.Integer(
        string='Minimal Quantity',
        default=1,
        help='Minimal Sale quantity',
    )


class PrestashopProductProductListener(Component):
    _name = 'prestashop.product.product.event.listener'
    _inherit = 'prestashop.connector.listener'
    _apply_on = 'prestashop.product.combination'

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    @skip_if(lambda self, record, **kwargs: self.need_to_export(record, **kwargs))
    def on_record_create(self, record, fields=None):
        """ Called when a record is created """
        record.with_delay().export_record(fields=fields)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    @skip_if(lambda self, record, **kwargs: self.need_to_export(record, **kwargs))
    def on_record_write(self, record, fields=None):
        """ Called when a record is written """
        work = self.work.work_on(collection=record)
        inv_listener = work.component(usage='product.inventory.listener')
        inventory_fields = inv_listener._get_inventory_fields()
        fields = list(set(fields).difference(set(inventory_fields)))
        if fields:
            record.with_delay().export_record(fields=fields)


class ProductProductListener(Component):
    _name = 'product.product.event.listener'
    _inherit = 'prestashop.connector.listener'
    _apply_on = 'product.product'

    EXCLUDE_FIELDS = ['lst_price']

    def prestashop_product_combination_unlink(self, record):
        # binding is deactivate when deactive a product variant
        for binding in record.prestashop_combinations_bind_ids:
            work = self.work.work_on(collection=binding.backend_id)
            binder = work.component(
                usage='binder', model_name='prestashop.product.combination')
            prestashop_id = binder.to_external(binding)
            binding.with_delay().export_delete_record(
                binding.backend_id, prestashop_id)
        record.prestashop_combinations_bind_ids.unlink()

    @skip_if(lambda self, record, **kwargs: self.env.context.get('install_mode'))
    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    @skip_if(lambda self, record, **kwargs: self.need_to_export(record.prestashop_combinations_bind_ids, **kwargs))
    def on_record_write(self, record, fields=None):
        """ Called when a record is written """
        for field in self.EXCLUDE_FIELDS:
            if field in fields:
                fields.remove(field)
        if 'active' in fields and not record.active:
            self.prestashop_product_combination_unlink(record)
            return
        if fields:
            priority = 20
            if 'default_on' in fields and record.active:
                # PS has to uncheck actual default combination first
                priority = 99
            for binding in record.prestashop_combinations_bind_ids:
                binding.with_delay(
                    priority=priority).export_record(fields=fields)


class PrestashopAttributeListener(Component):
    _name = 'prestashop.attribute.event.listener'
    _inherit = 'prestashop.connector.listener'
    _apply_on = [
        'prestashop.product.combination.option',
        'prestashop.product.combination.option.value'
    ]

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    @skip_if(lambda self, record, **kwargs: self.need_to_export(record, **kwargs))
    def on_record_create(self, record, fields=None):
        """ Called when a record is created """
        record.with_delay().export_record(fields=fields)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    @skip_if(lambda self, record, **kwargs: self.need_to_export(record, **kwargs))
    def on_record_write(self, record, fields=None):
        """ Called when a record is written """
        record.with_delay().export_record(fields=fields)


class AttributeListener(Component):
    _name = 'attribute.event.listener'
    _inherit = 'prestashop.connector.listener'
    _apply_on = [
        'product.attribute',
    ]

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        """ Called when a record is written """
        for binding in record.prestashop_bind_ids:
            if not self.need_to_export(binding, fields):
                binding.with_delay().export_record(fields=fields)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_unlink(self, record, fields=None):
        """ Called when a record is deleted """
        for binding in record.prestashop_bind_ids:
            work = self.work.work_on(collection=binding.backend_id)
            binder = work.component(
                usage='binder',
                model_name='prestashop.product.combination.option')
            prestashop_id = binder.to_external(binding)
            if prestashop_id:
                self.env['prestashop.product.combination.option'].\
                    with_delay().export_delete_record(
                        binding.backend_id, prestashop_id)


class AttributeValueListener(Component):
    _name = 'attribute.value.event.listener'
    _inherit = 'prestashop.connector.listener'
    _apply_on = [
        'product.attribute.value',
    ]

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        """ Called when a record is written """
        for binding in record.prestashop_bind_ids:
            if not self.need_to_export(binding, fields):
                binding.with_delay().export_record(fields=fields)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_unlink(self, record, fields=None):
        """ Called when a record is deleted """
        for binding in record.prestashop_bind_ids:
            work = self.work.work_on(collection=binding.backend_id)
            binder = work.component(
                usage='binder',
                model_name='prestashop.product.combination.option.value')
            prestashop_id = binder.to_external(binding)
            if prestashop_id:
                self.env['prestashop.product.combination.option.value'].\
                    with_delay().export_delete_record(
                        binding.backend_id, prestashop_id)
