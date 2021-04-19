# -*- coding: utf-8 -*-

from odoo.addons.component.core import Component
from odoo import _


class ProductCombinationDeleter(Component):
    _name = 'prestashop.product.combination.deleter'
    _inherit = 'prestashop.deleter'
    _apply_on = 'prestashop.product.combination'


class ProductCombinationOptionDeleter(Component):
    _name = 'prestashop.product.combination.option.deleter'
    _inherit = 'prestashop.deleter'
    _apply_on = [
        'prestashop.product.combination.option',
        'prestashop.product.combination.option.value',
    ]
