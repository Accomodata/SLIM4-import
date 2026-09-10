from odoo import models
from operator import attrgetter


class Slim4SuppliersExportProvider(models.AbstractModel):
    _name = 'slim4.export.provider.suppliers'
    _inherit = 'slim4.export.provider.logistics'
    _description = 'Slim4 Suppliers Export Provider'

    def _get_supplierinfo(self, record, rule_context=None):
        """Return the supplier line currently exported. To be able to reuse
        _rule_moq ,_rule_buying_price,.. from logistics.
        """
        return record

    def _rule_suppliers_warehouse(
        self,
        line,
        record,
        field_getter=None,
        rule_context=None,
    ):
        """Return the product warehouses, or all warehouses as fallback."""
        product = self._get_product(record, rule_context)
        warehouse_codes = product.mapped('warehouse_ids.code')

        return warehouse_codes or rule_context.get('warehouse')

    def _get_product(self, record, rule_context=None):
        """Return the variant linked to or generated for the supplier line."""
        occurrence = (rule_context or {}).get('occurrence', {})
        return occurrence.get('product_id') or record.product_id

    def _iter_export_occurrences(self, supplierinfo):
        """Yield one occurrence for each product using this supplier line."""
        if supplierinfo.product_id:
            # The supplier line already targets the correct variant.
            yield {}
            return

        # A template-level supplier line applies to every active variant.
        for product in supplierinfo.product_tmpl_id.product_variant_ids.filtered(
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
        """Resolve a field path from the supplier occurrence when applicable."""
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
