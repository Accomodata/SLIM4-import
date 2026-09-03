from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    warehouse_ids = fields.Many2many(
        comodel_name='stock.warehouse',
        relation='slim4_product_product_stock_warehouse_rel',
        column1='product_id',
        column2='warehouse_id',
        string='Slim4 Warehouses',
        help='Warehouses used by Slim4 for this product.',
        groups='slim4_connector_base.warehouse_field',
    )

    slim4_matching_supplier_ids = fields.Many2many(
        comodel_name='product.supplierinfo',
        string='Matching Suppliers',
        compute='_compute_slim4_supplier_fields',
        groups='slim4_connector_base.primary_supplier_field',
    )

    slim4_primary_supplier_ids = fields.Many2many(
        comodel_name='product.supplierinfo',
        string='Primary Suppliers',
        compute='_compute_slim4_supplier_fields',
        inverse='_inverse_slim4_primary_supplier_ids',
        readonly=False,
        groups='slim4_connector_base.primary_supplier_field',
        help=(
            'Vendor lines selected for Slim4. The first line by sequence and '
            'minimum quantity is used as the primary supplier.'
        ),
    )

    slim4_primary_supplier_id = fields.Many2one(
        comodel_name='product.supplierinfo',
        compute='_compute_slim4_supplier_fields',
        groups='slim4_connector_base.primary_supplier_field',
    )

    @api.depends(
        'product_variant_ids',
        'product_variant_ids.slim4_matching_supplier_ids',
        'product_variant_ids.slim4_primary_supplier_ids',
        'product_variant_ids.slim4_primary_supplier_id',
    )
    def _compute_slim4_supplier_fields(self):
        self._compute_template_field_from_variant_field(
            'slim4_matching_supplier_ids',
        )
        self._compute_template_field_from_variant_field(
            'slim4_primary_supplier_ids',
        )
        self._compute_template_field_from_variant_field(
            'slim4_primary_supplier_id',
        )

    def _inverse_slim4_primary_supplier_ids(self):
        self._set_product_variant_field('slim4_primary_supplier_ids')

    def _get_slim4_matching_sellers(self, variant):
        """Return the generic and variant-specific vendor lines."""
        self.ensure_one()

        return self.seller_ids.filtered(
            lambda line: not line.product_id or line.product_id == variant,
        ).sorted(
            key=lambda line: (
                line.sequence,
                line.min_qty,
                line.id or 0,
            ),
        )
