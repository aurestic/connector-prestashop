# © 2016 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import models, fields, api
import openerp.addons.decimal_precision as dp
from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if


class PrestashopProductTemplate(models.Model):
    _inherit = 'prestashop.product.template'

    meta_title = fields.Char(
        string='Meta Title',
        translate=True
    )
    meta_description = fields.Char(
        string='Meta Description',
        translate=True
    )
    meta_keywords = fields.Char(
        string='Meta Keywords',
        translate=True
    )
    tags = fields.Char(
        string='Tags',
        translate=True
    )
    online_only = fields.Boolean(string='Online Only')
    additional_shipping_cost = fields.Float(
        string='Additional Shipping Price',
        digits=dp.get_precision('Product Price'),
        help="Additionnal Shipping Price for the product on Prestashop")
    available_now = fields.Char(
        string='Available Now',
        translate=True
    )
    available_later = fields.Char(
        string='Available Later',
        translate=True
    )
    available_date = fields.Date(string='Available Date')
    minimal_quantity = fields.Integer(
        string='Minimal Quantity',
        help='Minimal Sale quantity',
        default=1,
    )

    state = fields.Boolean(string='State', default=True)


class PrestashopProductTemplateListener(Component):
    _name = 'prestashop.product.template.event.listener'
    _inherit = 'prestashop.connector.listener'
    _apply_on = 'prestashop.product.template'

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
        if 'minimal_quantity' in fields:
            record.product_variant_ids.mapped(
                'prestashop_combinations_bind_ids').filtered(
                    lambda cb: cb.backend_id == record.backend_id).write({
                        'minimal_quantity': record.minimal_quantity})


class ProductTemplateListener(Component):
    _name = 'product.template.event.listener'
    _inherit = 'prestashop.connector.listener'
    _apply_on = 'product.template'

    @skip_if(lambda self, record, **kwargs: self.env.context.get('install_mode'))
    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    @skip_if(lambda self, record, **kwargs: self.need_to_export(record.prestashop_bind_ids, **kwargs))
    def on_record_write(self, record, fields=None):
        """ Called when a record is written """
        for binding in record.prestashop_bind_ids:
            binding.with_delay().export_record(fields=fields)
