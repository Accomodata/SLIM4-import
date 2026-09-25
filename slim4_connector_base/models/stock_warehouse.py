from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    slim4_stocked_item = fields.Selection(
        string='Stocked Item',
        selection=[
            ('y', 'Stocked'),
            ('n', 'Non-Stocked'),
            ('p', 'Promotion'),
        ],
    )
