from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    slim4_matching_supplier_ids = fields.Many2many(
        comodel_name='product.supplierinfo',
        relation='product_product_slim4_matching_supplierinfo_rel',
        column1='product_id',
        column2='supplierinfo_id',
        string='Matching Suppliers',
        compute='_compute_slim4_matching_supplier_ids',
        store=True,
        groups='slim4_connector_base.primary_supplier_field',
        help=(
            'Technical field containing the vendor lines that apply to this '
            'variant. It is used to restrict the selectable Slim4 suppliers.'
        ),
    )

    slim4_primary_supplier_ids = fields.Many2many(
        comodel_name='product.supplierinfo',
        relation='product_product_slim4_primary_supplierinfo_rel',
        column1='product_id',
        column2='supplierinfo_id',
        string='Primary Supplier',
        domain="[('id', 'in', slim4_matching_supplier_ids)]",
        copy=False,
        groups='slim4_connector_base.primary_supplier_field',
        help=(
            'Vendor lines selected for Slim4. The first line by sequence and '
            'minimum quantity is used as the primary supplier.'
        ),
    )

    slim4_primary_supplier_id = fields.Many2one(
        comodel_name='product.supplierinfo',
        index=True,
        store=True,
        groups='slim4_connector_base.primary_supplier_field',
        compute='_compute_slim4_primary_supplier_id',
        help=(
            'Technical field containing the first selected vendor line by '
            'sequence and minimum quantity.'
        ),
    )

    _default_code_unique = models.Constraint(
        'unique(default_code)',
        'The Internal Reference must be unique.',
    )

    @api.depends(
        'product_tmpl_id',
        'product_tmpl_id.seller_ids',
        'product_tmpl_id.seller_ids.product_id',
    )
    def _compute_slim4_matching_supplier_ids(self):
        for product in self:
            product.slim4_matching_supplier_ids = (
                product.product_tmpl_id._get_slim4_matching_sellers(product)
            )

    @api.depends(
        'slim4_primary_supplier_ids',
        'slim4_primary_supplier_ids.sequence',
        'slim4_primary_supplier_ids.min_qty',
    )
    def _compute_slim4_primary_supplier_id(self):
        for product in self:
            product.slim4_primary_supplier_id = (
                product.slim4_primary_supplier_ids.sorted(
                    key=lambda line: (
                        line.sequence,
                        line.min_qty,
                        line.id or 0,
                    ),
                )[:1]
            )
