from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    slim4_matching_supplier_ids = fields.Many2many(
        comodel_name='product.supplierinfo',
        string='Matching Suppliers',
        compute='_compute_slim4_template_field_from_variant_fields',
        groups='slim4_connector_base.primary_supplier_field',
    )

    slim4_primary_supplier_ids = fields.Many2many(
        comodel_name='product.supplierinfo',
        string='Primary Supplier',
        compute='_compute_slim4_template_field_from_variant_fields',
        inverse='_inverse_slim4_primary_supplier_ids',
        readonly=False,
        groups='slim4_connector_base.primary_supplier_field',
        help=(
            'Vendor lines selected for Slim4. The first line by sequence and '
            'minimum quantity is used as the primary supplier.'
        ),
    )

    configured_warehouse_ids = fields.One2many(
        comodel_name='slim4.warehouse.config',
        string='Configured Warehouses',
        inverse_name='product_tmpl_id',
        inverse='_inverse_configured_warehouse_ids',
        compute='_compute_slim4_template_field_from_variant_fields',
    )

    slim4_primary_supplier_id = fields.Many2one(
        comodel_name='product.supplierinfo',
        compute='_compute_slim4_template_field_from_variant_fields',
        groups='slim4_connector_base.primary_supplier_field',
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
        'product_variant_ids',
        'product_variant_ids.slim4_matching_supplier_ids',
        'product_variant_ids.slim4_primary_supplier_ids',
        'product_variant_ids.slim4_primary_supplier_id',
        'product_variant_ids.configured_warehouse_ids',
    )
    def _compute_slim4_template_field_from_variant_fields(self):
        self._compute_template_field_from_variant_field(
            'slim4_matching_supplier_ids',
        )
        self._compute_template_field_from_variant_field(
            'slim4_primary_supplier_ids',
        )
        self._compute_template_field_from_variant_field(
            'slim4_primary_supplier_id',
        )
        self._compute_template_field_from_variant_field(
            'configured_warehouse_ids',
        )

    def _inverse_slim4_primary_supplier_ids(self):
        self._set_product_variant_field('slim4_primary_supplier_ids')

    def _inverse_configured_warehouse_ids(self):
        self._set_product_variant_field('configured_warehouse_ids')

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

    @api.model_create_multi
    def create(self, vals_list):
        templates = super(
            ProductTemplate,
            self.with_context(skip_slim4_default_wh_config=True),
        ).create(vals_list)

        templates = templates.with_env(self.env)

        if not self.env.context.get('skip_slim4_default_wh_config'):
            warehouses = self.env['stock.warehouse'].search([
                ('company_id', '=', self.env.company.id),
            ])
            products = templates.product_variant_ids
            products._create_slim4_default_wh_config(warehouses, products)

        return templates

    @api.model
    def _get_related_fields_variant_template(self):
        return [
            *super()._get_related_fields_variant_template(),
            'configured_warehouse_ids',
        ]
