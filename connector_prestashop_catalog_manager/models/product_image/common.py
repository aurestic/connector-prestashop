# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields
from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if


class ProductImage(models.Model):
    _inherit = 'base_multi_image.image'

    front_image = fields.Boolean(string='Front image')


class PrestashopProductImageListener(Component):
    _name = 'prestashop.product.image.event.listener'
    _inherit = 'base.connector.listener'
    _apply_on = 'base_multi_image.image',

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_create(self, record, fields=None):
        product = self.env[record.owner_model].browse(record.owner_id)
        if product.exists():
            for prestashop_product in product.prestashop_bind_ids:
                if record.storage == 'file':
                    binding = self.env['prestashop.product.image'].create({
                        'odoo_id': record.id,
                        'backend_id': prestashop_product.backend_id.id
                    })
                    binding.with_delay().export_record(fields=fields)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        """ Called when a record is written """
        for binding in record.prestashop_bind_ids:
            binding.with_delay().export_record(fields=fields)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_unlink(self, record, fields=None):
        """ Called when a record is created """
        for binding in record.prestashop_bind_ids:
            product = self.env[record.owner_model].browse(record.owner_id)
            if product.exists():
                template = product.prestashop_bind_ids.filtered(
                    lambda x: x.backend_id == binding.backend_id)
                if not template:
                    return

                work = self.work.work_on(collection=binding.backend_id)
                binder = work.component(
                    usage='binder', model_name='prestashop.product.template')
                template_prestashop_id = binder.to_external(template)
                binder = work.component(
                    usage='binder', model_name='prestashop.product.image')
                prestashop_id = binder.to_external(binding)
                if prestashop_id:
                    binding.with_delay().export_delete_record(
                        binding.backend_id,
                        prestashop_id,
                        template_prestashop_id)
