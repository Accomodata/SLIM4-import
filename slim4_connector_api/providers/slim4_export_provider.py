from datetime import date, datetime, time

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class Slim4ExportProvider(models.AbstractModel):
    _name = 'slim4.export.provider'
    _description = 'Slim4 Export Provider'

    @api.model
    def export_interface(self, interface, limit=None, offset=0):
        """Export one Slim4 interface as JSON-serializable dictionaries."""
        interface.ensure_one()
        records = self._get_source_records(
            interface,
            limit=limit,
            offset=offset,
        )
        mapping_lines = interface.mapping_line_ids.filtered(
            lambda line: line.status == 'validated',
        )

        return [
            self._prepare_record_row(record, mapping_lines)
            for record in records
        ]

    def _get_source_records(self, interface, limit=None, offset=0):
        """Retrieve source records through the ORM using the configured domain."""
        model_env = interface._get_source_model_env()
        domain = self._get_source_domain(interface)
        return model_env.search(domain, limit=limit, offset=offset)

    def _get_source_domain(self, interface):
        """Parse the configured source domain."""
        try:
            return safe_eval(interface.source_domain or '[]')
        except (ValueError, SyntaxError):
            raise UserError(_('Invalid source domain.')) from None

    def _prepare_record_row(self, record, mapping_lines):
        """Apply the configured Slim4 mappings to one source record."""
        return {
            line.slim4_field: self._resolve_mapping_value(line, record)
            for line in mapping_lines
        }

    def _resolve_mapping_value(self, line, record):
        if line.mapping_type == 'field':
            return self._resolve_field_path(record, line.field_path)
        if line.mapping_type == 'constant':
            return line.constant_value or False
        if line.mapping_type in {'generated', 'rule'}:
            return self._resolve_rule_value(line, record)
        return False

    def _resolve_field_path(self, record, field_path):
        """Follow a dotted Odoo field path and return an exportable value."""
        current = record
        for field_name in field_path.split('.'):
            if not current:
                return False
            current = current[field_name]
        return self._exportable_value(current)

    def _resolve_rule_value(self, line, record):
        """Resolve a mapping value using the Python rule linked to the rule key."""
        method = getattr(self, f'_rule_{line.rule_key}', None)
        if not method:
            return False
        return self._exportable_value(method(record))

    def _exportable_value(self, value):
        """Convert common Odoo values to JSON-serializable Python values."""
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()

        return value if value is not None else False
