from odoo import models, fields


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    slim4_ioq = fields.Float(
        string='IOQ',
        help='Incremental Order Quantity',
        groups='slim4_connector_base.ioq_field',
    )
