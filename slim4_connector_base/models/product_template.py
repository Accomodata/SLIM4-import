from odoo import fields, models


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
        related='product_variant_id.slim4_matching_supplier_ids',
        string='Matching Suppliers',
        groups='slim4_connector_base.primary_supplier_field',
    )

    slim4_primary_supplier_ids = fields.Many2many(
        related='product_variant_id.slim4_primary_supplier_ids',
        string='Primary Suppliers',
        readonly=False,
        groups='slim4_connector_base.primary_supplier_field',
        help=(
            'Vendor lines selected for Slim4. The first line by sequence and '
            'minimum quantity is used as the primary supplier.'
        ),
    )

    slim4_primary_supplier_id = fields.Many2one(
        related='product_variant_id.slim4_primary_supplier_id',
        comodel_name='product.supplierinfo',
        groups='slim4_connector_base.primary_supplier_field',
    )

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
