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

    configured_warehouse_ids = fields.One2many(
        comodel_name='slim4.warehouse.config',
        inverse_name='product_id',
        string='Configured Warehouses',
        help='Configure Stock Item.',
        groups='slim4_connector_base.warehouse_field',
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

    _default_code_unique = models.UniqueIndex(
        """
        (default_code)
        WHERE active IS TRUE
        AND default_code IS NOT NULL
        AND default_code != ''
        """,
        'The Internal Reference must be unique among active products.',
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
        'slim4_matching_supplier_ids',
    )
    def _compute_slim4_primary_supplier_id(self):
        for product in self:
            # Check if primary supplier is still relevant after change
            matching_selected_suppliers = (
                product.slim4_primary_supplier_ids
                & product.slim4_matching_supplier_ids
            )

            product.slim4_primary_supplier_id = (
                matching_selected_suppliers.sorted(
                    key=lambda line: (
                        line.sequence,
                        line.min_qty,
                        line.id or 0,
                    ),
                )[:1]
            )

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)

        if not self.env.context.get('skip_slim4_default_wh_config'):
            warehouses = self.env['stock.warehouse'].search([
                ('company_id', '=', self.env.company.id),
            ])
            self._create_slim4_default_wh_config(warehouses, products)

        return products

    def _create_slim4_default_wh_config(self, warehouses, products):
        if not products or not warehouses:
            return

        config = self.env['slim4.warehouse.config']
        existing_configs = config.search([
            ('product_id', 'in', products.ids),
        ])
        products_to_configure = products - existing_configs.mapped('product_id')

        vals = [
            {
                'product_id': product.id,
                'warehouse_id': warehouse.id,
                'slim4_stocked_item': 'y',
            }
            for product in products_to_configure
            for warehouse in warehouses
        ]
        if vals:
            config.create(vals)
