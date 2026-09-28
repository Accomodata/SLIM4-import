from odoo import fields, models


class SlimWarehouseConfig(models.Model):
    _name = 'slim4.warehouse.config'
    _description = 'Slim4 Warehouse Config'

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        index=True,
    )

    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
    )

    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        groups='slim4_connector_base.warehouse_field',
        string='Warehouse',
    )

    code = fields.Char(
        related='warehouse_id.code',
    )

    slim4_stocked_item = fields.Selection(
        string='Stocked Item',
        groups='slim4_connector_base.warehouse_field',
        default='n',
        selection=[
            ('y', 'Stocked'),
            ('n', 'Non-Stocked'),
            ('p', 'Promotion'),
        ],
    )

    _slim4_warehouse_config_unique = models.Constraint(
            'unique (product_id, warehouse_id)',
            'This Configuration Already exists for this product/warehouse',
    )
