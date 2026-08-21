from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    warehouse_ids = fields.Many2many(
        comodel_name='stock.warehouse',
        relation='slim4_product_product_stock_warehouse_rel',
        column1='product_id',
        column2='warehouse_id',
        string='Slim4 Warehouses',
        help='Warehouses used by Slim4 for this product.',
        groups='slim4_mapping.group_slim4_warehouse_field',
    )
