from odoo import api, models, fields
from odoo.exceptions import ValidationError


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    slim4_ioq = fields.Float(
        string='IOQ',
        help='Incremental Order Quantity',
        groups='slim4_connector_base.ioq_field',
    )

    @api.constrains('product_id', 'product_tmpl_id')
    def _check_slim4_primary_supplier_assignment(self):
        product = self.env['product.product']

        for line in self:
            domain = [
                ('slim4_primary_supplier_ids', 'in', line.ids),
            ]

            if line.product_id:
                domain.append(('id', '!=', line.product_id.id))
            else:
                domain.append(
                    ('product_tmpl_id', '!=', line.product_tmpl_id.id),
                )

            linked_product = product.search(domain, limit=1)
            if linked_product:
                raise ValidationError(
                    self.env._(
                        'This vendor line is selected as a Slim4 supplier forennials '
                        '%(product)s. Remove it from the Slim4 Primary Supplier '
                        'field before changing its product.',
                        product=linked_product.display_name,
                    ),
                )
