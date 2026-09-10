from odoo import Command, models, fields


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    slim4_ioq = fields.Float(
        string='IOQ',
        help='Incremental Order Quantity',
        groups='slim4_connector_base.ioq_field',
    )

    def write(self, vals):
        if 'product_id' in vals:
            self.filtered(
                lambda supplier: supplier.product_id.id != vals['product_id'],
            )._remove_from_slim4_primary_suppliers()

        return super().write(vals)

    def _remove_from_slim4_primary_suppliers(self):
        products = self.env['product.product'].search([
            ('slim4_primary_supplier_ids', 'in', self.ids),
        ])
        products.write({
            'slim4_primary_supplier_ids': [
                Command.unlink(supplier.id)
                for supplier in self
            ],
        })
