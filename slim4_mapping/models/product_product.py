from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    slim4_primary_supplier_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='product_product_slim4_primary_supplier_rel',
        column1='product_id',
        column2='partner_id',
        string='Primary Supplier',
        compute='_compute_slim4_primary_supplier_ids',
        store=True,
        groups='slim4_mapping.primary_supplier_field',
        help='Primary supplier selected by sequence and minimum quantity.',
    )

    @api.depends(
        'product_tmpl_id',
        'product_tmpl_id.seller_ids.sequence',
        'product_tmpl_id.seller_ids.min_qty',
        'product_tmpl_id.seller_ids.partner_id',
        'product_tmpl_id.seller_ids.product_id',
    )
    def _compute_slim4_primary_supplier_ids(self):
        for product in self:
            primary_seller = (
                product.product_tmpl_id._get_slim4_primary_seller(product)
            )
            product.slim4_primary_supplier_ids = (
                primary_seller.partner_id.ids
            )
