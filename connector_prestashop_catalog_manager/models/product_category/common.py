# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tools import config
from odoo import api, fields, models
from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.connector_prestashop.components.backend_adapter import PrestaShopWebServiceImage


class PrestashopProductCategoryListener(Component):
    _name = 'prestashop.product.category.event.listener'
    _inherit = 'prestashop.connector.listener'
    _apply_on = 'prestashop.product.category'

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


class ProductCategoryListener(Component):
    _name = 'product.category.event.listener'
    _inherit = 'prestashop.connector.listener'
    _apply_on = 'product.category'

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        """ Called when a record is written """
        for binding in record.prestashop_bind_ids:
            binding.with_delay().export_record(fields=fields)
