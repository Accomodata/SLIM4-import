from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_slim4_warehouse_field = fields.Boolean(
        string='Enable Warehouse',
        implied_group='slim4_mapping.warehouse_field',
        group='base.group_user',
        help='Enables the warehouse functionality on products.',
    )

    group_slim4_primary_supplier_field = fields.Boolean(
        string='Enable Primary Supplier',
        implied_group='slim4_mapping.primary_supplier_field',
        group='base.group_user',
        help='Enables the primary supplier functionality on suppliers.',
    )

    group_slim4_ioq_field = fields.Boolean(
        string='Enable IOQ Field',
        implied_group='slim4_mapping.ioq_field',
        group='base.group_user',
        help='Enables the ability to register an incremental order'
        ' of quantity on suppliers.',
    )
