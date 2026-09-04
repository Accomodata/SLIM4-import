from odoo import models
from operator import attrgetter


class Slim4SuppliersExportProvider(models.AbstractModel):
    _name = 'slim4.export.provider.suppliers'
    _inherit = 'slim4.export.provider.logistics'
    _description = 'Slim4 Suppliers Export Provider'

    def _iter_export_occurrences(self, record):
        """Yield one occurrence per supplier when the feature is enabled."""
        if not self._is_primary_supplier_feature_enabled():
            yield from super()._iter_export_occurrences(record)
            return

        for supplierinfo in record.slim4_primary_supplier_ids:
            yield {
                'slim4_primary_supplier_id': supplierinfo,
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
