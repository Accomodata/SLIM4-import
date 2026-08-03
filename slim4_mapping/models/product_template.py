from odoo import fields, models

from .res_config_settings import get_slim4_visible_field_keys


class ProductProduct(models.Model):
    _inherit = 'product.template'

    warehouse_ids = fields.Many2many(
        comodel_name='stock.warehouse',
        relation='slim4_product_tmpl_stock_warehouse_rel',
        column1='product_tmpl_id',
        column2='warehouse_id',
        string='Warehouses',
        help='Warehouses used by Slim4 for this product.',
    )
    slim4_show_warehouse_ids = fields.Boolean(
        compute='_compute_slim4_show_warehouse_ids',
    )

    def _compute_slim4_show_warehouse_ids(self):
        is_visible = (
            'product.template.warehouse_ids'
            in get_slim4_visible_field_keys(self.env)
        )
        for product in self:
            product.slim4_show_warehouse_ids = is_visible
