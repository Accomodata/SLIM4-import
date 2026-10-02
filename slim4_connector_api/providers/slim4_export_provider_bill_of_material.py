from odoo import models
from operator import attrgetter


class Slim4BillOfMaterialExportProvider(models.AbstractModel):
    _name = 'slim4.export.provider.bill.of.material'
    _inherit = 'slim4.export.provider'
    _description = 'Slim4 Bill Of Material Export Provider'

    def _iter_export_occurrences(self, bom_line):
        """Yield one occurrence for each product using this BoM."""
        bom = bom_line.bom_id
        if bom.product_id:
            # The BoM already targets the correct variant.
            yield {}
            return
        # A template-level BoM applies to every active variant.
        for product in bom.product_tmpl_id.product_variant_ids.filtered(
            lambda product: product.active and product.default_code,
        ):
            yield {
                'product_id': product,
            }

    def _get_field_path_value(
        self,
        record,
        line,
        field_getter,
        rule_context=None,
    ):
        """Resolve a field path from the BoM occurrence when applicable."""
        occurrence = (rule_context or {}).get('occurrence', {})
        root_field_name, _, remaining_field_path = (
            line.field_path or ''
        ).partition('.')

        if root_field_name not in occurrence:
            return super()._get_field_path_value(
                record,
                line,
                field_getter,
                rule_context,
            )

        occurrence_record = occurrence[root_field_name]

        if not remaining_field_path:
            return None

        if line.split_records:
            return occurrence_record.mapped(remaining_field_path)

        return attrgetter(remaining_field_path)(occurrence_record)
