from odoo import models, fields, api

from .res_config_settings import get_slim4_visible_field_keys


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    slim4_primary_supplier_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='product_template_slim4_primary_supplier_rel',
        column1='product_tmpl_id',
        column2='partner_id',
        string='Primary Supplier',
    )

    slim4_moq = fields.Float(
        string='MOQ',
        compute='_compute_slim4_moq',
        inverse='_inverse_slim4_moq',
        help='Minimum Order Quantity',
    )
    slim4_ioq = fields.Float(
        string='IOQ',
        compute='_compute_slim4_ioq',
        inverse='_inverse_slim4_ioq',
        help='Incremental Order Quantity',
    )

    # Visibility compute flags
    slim4_show_moq = fields.Boolean(
        compute='_compute_slim4_show_fields',
    )
    slim4_show_ioq = fields.Boolean(
        compute='_compute_slim4_show_fields',
    )

    @api.depends('product_variant_ids.slim4_moq', 'product_variant_count')
    def _compute_slim4_moq(self):
        for template in self:
            if template.product_variant_count == 1:
                template.slim4_moq = template.product_variant_id.slim4_moq
            else:
                template.slim4_moq = 0.0

    def _inverse_slim4_moq(self):
        for template in self:
            if template.product_variant_count == 1:
                template.product_variant_id.slim4_moq = template.slim4_moq

    @api.depends('product_variant_ids.slim4_ioq', 'product_variant_count')
    def _compute_slim4_ioq(self):
        for template in self:
            if template.product_variant_count == 1:
                template.slim4_ioq = template.product_variant_id.slim4_ioq
            else:
                template.slim4_ioq = 0.0

    def _inverse_slim4_ioq(self):
        for template in self:
            if template.product_variant_count == 1:
                template.product_variant_id.slim4_ioq = template.slim4_ioq

    def _compute_slim4_show_fields(self):
        visible_keys = set(get_slim4_visible_field_keys(self.env))

        show_moq = bool(
            visible_keys & {
                'product.template.slim4_moq',
                'product.product.slim4_moq',
            }
        )
        show_ioq = bool(
            visible_keys & {
                'product.template.slim4_ioq',
                'product.product.slim4_ioq',
            }
        )

        for template in self:
            template.slim4_show_moq = show_moq
            template.slim4_show_ioq = show_ioq
