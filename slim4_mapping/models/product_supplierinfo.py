from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    slim4_is_primary = fields.Boolean(
        string='Primary',
        compute='_compute_slim4_is_primary',
        store=True,
        readonly=False,
        groups='slim4_mapping.primary_supplier_field',
        help='Indicates if this supplier is the primary supplier for the product.',
    )

    slim4_ioq = fields.Float(
        string='IOQ',
        help='Incremental Order Quantity',
        groups='slim4_mapping.ioq_field',
    )

    def _is_primary_supplier_enabled(self):
        return self.env.user.has_group('slim4_mapping.primary_supplier_field')

    @api.depends('sequence', 'min_qty', 'product_tmpl_id', 'product_id')
    def _compute_slim4_is_primary(self):
        templates = self.mapped('product_tmpl_id') | self.mapped(
            'product_id.product_tmpl_id')
        for tmpl in templates:
            tmpl._recompute_primary_suppliers()

    def write(self, vals):
        res = super().write(vals)
        # Re-evaluate all sibling lines synchronously when reordered
        if any(k in vals for k in (
            'sequence', 'min_qty', 'product_id', 'product_tmpl_id',
        )):
            templates = self.mapped('product_tmpl_id') | self.mapped(
                'product_id.product_tmpl_id',
            )
            for tmpl in templates:
                tmpl._recompute_primary_suppliers()
        return res

    @api.constrains('slim4_is_primary', 'product_tmpl_id', 'product_id')
    def _check_single_primary_supplier(self):
        for line in self:
            if not line.slim4_is_primary or not line._is_primary_supplier_enabled():
                continue

            domain = [
                ('id', '!=', line.id),
                ('slim4_is_primary', '=', True),
            ]
            if line.product_id:
                domain.append(('product_id', '=', line.product_id.id))
            else:
                domain.append(('product_tmpl_id', '=', line.product_tmpl_id.id))
                domain.append(('product_id', '=', False))

            if self.search_count(domain) > 0:
                raise ValidationError(self.env._(
                    "There can only be one 'Primary' supplier per product (or variant)",
                ))
