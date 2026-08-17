from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    slim4_primary_supplier_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='product_template_slim4_primary_supplier_rel',
        column1='product_tmpl_id',
        column2='partner_id',
        string='Primary Supplier',
        compute='_compute_slim4_primary_supplier_ids',
        store=True,
        groups='slim4_mapping.primary_supplier_field',
        help="Primary suppliers calculated from the product's vendor list.",
    )

    def _recompute_primary_suppliers(self):
        """Calculate primary supplier lines across template and individual variants."""
        for tmpl in self:
            primary_records = self.env['product.supplierinfo']

            # 1. Template-level Primary (sequence takes priority over min_qty)
            tmpl_lines = tmpl.seller_ids.filtered(lambda line: not line.product_id)
            if tmpl_lines:
                sorted_tmpl_lines = tmpl_lines.sorted(
                    key=lambda line: (line.sequence, line.min_qty, line.id or 0))
                primary_records |= sorted_tmpl_lines[0]

            # 2. Variant-level Primary (one per variant if specific lines exist)
            for variant in tmpl.product_variant_ids:
                variant_lines = tmpl.seller_ids.filtered(
                    lambda line, variant=variant: line.product_id == variant,
                )
                if variant_lines:
                    sorted_variant_lines = variant_lines.sorted(
                        key=lambda line: (line.sequence, line.min_qty, line.id or 0))
                    primary_records |= sorted_variant_lines[0]

            # Direct update without triggering re-entrancy loops
            for line in tmpl.seller_ids:
                is_primary = (line in primary_records)
                if line.slim4_is_primary != is_primary:
                    super(models.Model, line).write({'slim4_is_primary': is_primary})

    @api.depends(
        'seller_ids.sequence',
        'seller_ids.min_qty',
        'seller_ids.partner_id',
        'seller_ids.product_id',
        'product_variant_ids.seller_ids.sequence',
        'product_variant_ids.seller_ids.min_qty',
        'product_variant_ids.seller_ids.partner_id',
    )
    def _compute_slim4_primary_supplier_ids(self):
        for template in self:
            primary_sellers = template.seller_ids.filtered(lambda s: s.slim4_is_primary)
            variant_sellers = template.product_variant_ids.seller_ids.filtered(
                lambda s: s.slim4_is_primary)

            all_primary_partners = (
                primary_sellers | variant_sellers).mapped('partner_id')
            template.slim4_primary_supplier_ids = all_primary_partners.ids
