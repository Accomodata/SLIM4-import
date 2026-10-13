from odoo import models


class Slim4BillOfMaterialExportProvider(models.AbstractModel):
    _name = 'slim4.export.provider.bill.of.material'
    _inherit = 'slim4.export.provider'
    _description = 'Slim4 Bill Of Material Export Provider'

    def _iter_export_occurrences(self, bom_line):
        """Yield one occurrence for each eligible variant of this BoM line."""
        bom = bom_line.bom_id
        products = bom.product_id or bom.product_tmpl_id.product_variant_ids
        for product in products.filtered(
            lambda product: product.active and product.default_code,
        ):
            if not bom_line._skip_bom_line(product):
                yield {
                    'bom_product': product,
                }

    def _rule_bill_of_material_article_code(
        self,
        line,
        record,
        field_getter=None,
        rule_context=None,
    ):
        """Return the finished product code for the current BoM occurrence."""
        occurrence = (rule_context or {}).get('occurrence', {})
        bom_product = occurrence.get('bom_product')
        return bom_product.default_code if bom_product else None
