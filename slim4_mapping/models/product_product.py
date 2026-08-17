from odoo import fields, models

from .res_config_settings import get_slim4_visible_field_keys


class ProductProduct(models.Model):
    _inherit = 'product.product'

    warehouse_ids = fields.Many2many(
        comodel_name='stock.warehouse',
        relation='slim4_product_product_stock_warehouse_rel',
        column1='product_id',
        column2='warehouse_id',
        string='Slim4 Warehouses',
        help='Warehouses used by Slim4 for this product.',
    )

    slim4_moq = fields.Float(string='MOQ', help='Minimum Order Quantity')
    slim4_ioq = fields.Float(string='IOQ', help='Incremental Order Quantity')

    # Visibility compute flags
    slim4_show_warehouse_ids = fields.Boolean(
        compute='_compute_slim4_show_fields',
    )
    slim4_show_moq = fields.Boolean(
        compute='_compute_slim4_show_fields',
    )
    slim4_show_ioq = fields.Boolean(
        compute='_compute_slim4_show_fields',
    )

    def _get_visible_keys(self):
        return set(get_slim4_visible_field_keys(self.env))

    def _compute_slim4_show_fields(self):
        visible_keys = self._get_visible_keys()

        # Resolve field keys for product.product (or product.template)
        model_name = self._name
        show_warehouse = f'{model_name}.warehouse_ids' in visible_keys
        show_moq = f'{model_name}.slim4_moq' in visible_keys
        show_ioq = f'{model_name}.slim4_ioq' in visible_keys

        for record in self:
            record.slim4_show_warehouse_ids = show_warehouse
            record.slim4_show_moq = show_moq
            record.slim4_show_ioq = show_ioq
