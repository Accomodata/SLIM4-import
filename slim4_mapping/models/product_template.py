from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    warehouse_ids = fields.Many2many(
        comodel_name='stock.warehouse',
        relation='slim4_product_product_stock_warehouse_rel',
        column1='product_id',
        column2='warehouse_id',
        string='Slim4 Warehouses',
        help='Warehouses used by Slim4 for this product.',
        groups='slim4_mapping.warehouse_field',
    )

    slim4_primary_supplier_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='product_template_slim4_primary_supplier_rel',
        column1='product_tmpl_id',
        column2='partner_id',
        string='Primary Supplier',
        compute='_compute_slim4_primary_supplier_ids',
        store=True,
        groups='slim4_mapping.primary_supplier_field',
        help="Primary suppliers determined from the product's vendor list. "
        "Suppliers with the highest priority (lowest sequence value) are selected.",
    )

    def _recompute_primary_suppliers(self):
        """Calculate primary supplier lines for templates and variants."""
        for tmpl in self:
            primary_records = self.env['product.supplierinfo']
            variants = tmpl.product_variant_ids

            # A template with more then 1 variant has no template primary.
            if len(variants) == 1:
                primary_records |= tmpl._get_slim4_primary_seller()

            # One primary per variant.
            # Generic and variant-specific lines compete by sequence/min_qty.
            for variant in variants:
                primary_records |= tmpl._get_slim4_primary_seller(variant)

            # Direct update without triggering re-entrancy loops
            for line in tmpl.seller_ids:
                is_primary = line in primary_records
                if line.slim4_is_primary != is_primary:
                    super(models.Model, line).write({
                        'slim4_is_primary': is_primary,
                    })

    def _get_slim4_primary_seller(self, variant=None):
        """Return the first applicable supplier line.

        Template:
            Only lines without product_id.

        Variant:
            Lines for this variant or generic lines without product_id.
        """
        self.ensure_one()

        if variant:
            seller_lines = self.seller_ids.filtered(
                lambda line: (
                    not line.product_id
                    or line.product_id == variant
                ),
            )
        else:
            seller_lines = self.seller_ids.filtered(
                lambda line: not line.product_id,
            )

        return seller_lines.sorted(
            key=lambda line: (
                line.sequence,
                line.min_qty,
                line.id or 0,
            ),
        )[:1]

    @api.depends(
        'seller_ids.sequence',
        'seller_ids.min_qty',
        'seller_ids.partner_id',
        'seller_ids.product_id',
        'product_variant_ids',
        'product_variant_ids.active',
    )
    def _compute_slim4_primary_supplier_ids(self):
        for template in self:
            # No primary supplier if multiple variants
            if len(template.product_variant_ids) > 1:
                template.slim4_primary_supplier_ids = False
                continue

            primary_seller = template._get_slim4_primary_seller()
            template.slim4_primary_supplier_ids = (
                primary_seller.partner_id.ids
            )
