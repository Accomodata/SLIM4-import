from datetime import date, datetime
from operator import attrgetter, methodcaller

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.tools import html2plaintext
from ..helpers.skiptoken import encode_skiptoken, decode_skiptoken


class Slim4ExportProvider(models.AbstractModel):
    _name = 'slim4.export.provider'
    _description = 'Slim4 Export Provider'

    @api.model
    def export_interface(
        self,
        interface,
        page_size=20,
        offset=0,
        skiptoken=None,
        **params,
    ):
        """Export one Slim4 interface as JSON-serializable dictionaries."""
        interface.ensure_one()

        fetched_records = self._get_source_records(
            interface,
            page_size=page_size,
            offset=offset,
            skiptoken=skiptoken,
            **params,
        )
        # Keep the overfetched record only to detect whether another page exists.
        has_more = len(fetched_records) > page_size
        source_records = fetched_records[:page_size]

        mapping_lines = self._get_available_mapping_lines(interface)
        mapping_plan = self._get_mapping_plan(mapping_lines)

        split_mapping = mapping_lines.filtered('split_records')
        split_key = split_mapping.slim4_field if split_mapping else None

        # Prepare export-wide values shared by mapping rules.
        rule_context = self._get_rule_context()

        rows = list(
            self._iter_export_rows(
                source_records,
                mapping_plan,
                split_key,
                rule_context,
            ),
        )

        return {
            'data': rows,
            'has_more': has_more,
            'next_skiptoken': (
                self._get_next_skiptoken(source_records)
                if has_more
                else None
            ),
        }

    def _get_source_records(
        self,
        interface,
        page_size=20,
        offset=0,
        skiptoken=None,
        **params,
    ):
        domain = self._get_source_domain(interface, **params)

        if skiptoken is not None:
            last_write_date, last_id = decode_skiptoken(skiptoken)
            domain += [
                '|',
                ('write_date', '>', last_write_date),
                '&',
                ('write_date', '=', last_write_date),
                ('id', '>', last_id),
            ]

        return self.env[interface.source_model].search(
            domain,
            limit=page_size + 1,
            offset=offset if skiptoken is None else 0,
            order='write_date ASC, id ASC',
        )

    def _get_available_mapping_lines(self, interface):
        """Return validated mappings available to the export user."""
        user_group_ids = set(self.env.user.group_ids.ids)

        return interface.mapping_line_ids.filtered(
            lambda line: (
                line.status == 'validated'
                and (
                    not line.group_id
                    or line.group_id.id in user_group_ids
                )
            ),
        )

    def _get_mapping_plan(self, mapping_lines):
        """Return the active mapping lines and their compiled field getters."""
        return [
            (
                line,
                self._get_mapping_field_getter(line),
            )
            for line in mapping_lines
        ]

    def _get_mapping_field_getter(self, line):
        """Compile the configured field path when the mapping requires one."""
        if (
            line.mapping_type not in {'field', 'rule'}
            or not line.field_path
        ):
            return None

        if line.split_records:
            return methodcaller('mapped', line.field_path)

        return attrgetter(line.field_path)

    def _get_rule_context(self):
        """Prepare reusable values required by configured rules."""
        rule_context = {
            # retrieve all warehouses as fallback for warehouse slim4 field
            'warehouse': self._get_rule_context_warehouse(),
        }
        return rule_context

    def _get_rule_context_warehouse(self):
        """Return all warehouse codes available to the export user."""
        company = self.env.company
        warehouses = self.env['stock.warehouse'].with_company(
            company.id).search([])
        return list(set(warehouses.mapped('code')))

    def _iter_export_rows(
        self,
        source_records,
        mapping_plan,
        split_key=None,
        rule_context=None,
    ):
        """Yield normalized rows for every export occurrence."""
        for record in source_records:
            for occurrence in self._iter_export_occurrences(record):
                current_context = dict(rule_context or {})
                current_context['occurrence'] = occurrence

                row = self._prepare_record_row(
                    record,
                    mapping_plan,
                    current_context,
                )

                yield from self._iter_split_rows(row, split_key)

    def _iter_export_occurrences(self, record):
        """Yield the row-level contexts generated from one source record.
        A source record controls search and pagination, while an occurrence
        represents one complete evaluation of its mapping.

        Providers may yield multiple contexts when several business occurrences
        must be exported from the same source record. Each yielded context is
        exposed through ``rule_context['occurrence']`` while preparing the row.

        The default implementation yields one empty context, preserving one
        mapping evaluation per source record. Any configured mapping-level split
        is applied afterwards.

        Overrides should use prefetched relations from ``record`` and avoid
        performing ORM searches inside this iterator.
        """
        yield {}

    def _iter_split_rows(self, row, split_key=None):
        """Yield rows produced by the configured mapping split."""
        split_values = row.get(split_key) if split_key else None

        if not isinstance(split_values, list):
            yield row
            return

        for split_value in split_values:
            split_row = row.copy()
            split_row[split_key] = split_value
            yield split_row

    def _get_source_domain(self, interface, **params):
        """Parse the configured source domain."""
        return safe_eval(interface.source_domain)

    def _prepare_record_row(self, record, mapping_plan, rule_context=None):
        """Apply the configured Slim4 mappings to one source record."""
        return {
            line.slim4_field: self._resolve_mapping_value(
                line,
                record,
                field_getter,
                rule_context,
            )
            for line, field_getter in mapping_plan
        }

    def _resolve_mapping_value(
        self,
        line,
        record,
        field_getter=None,
        rule_context=None,
    ):
        if line.mapping_type == 'field':
            value = self._resolve_field_path(record, line, field_getter, rule_context)

        if line.mapping_type == 'constant':
            value = self._normalize_mapping_value(line, line.constant_value)

        if line.mapping_type == 'rule':
            value = self._resolve_rule_value(line, record, field_getter, rule_context)

        if line.slim4_required and value in (None, '', []):
            raise UserError(
                _(
                    'Required Slim4 field "%(field)s" is empty for %(record)s.',
                    field=line.slim4_field,
                    record=record.display_name,
                ),
            )
        return value

    def _resolve_field_path(
        self,
        record,
        line,
        field_getter,
        rule_context=None,
    ):
        """Resolve and normalize a configured field path."""
        raw_value = self._get_field_path_value(
            record,
            line,
            field_getter,
            rule_context,
        )
        return self._normalize_mapping_value(line, raw_value)

    def _get_field_path_value(
        self,
        record,
        line,
        field_getter,
        rule_context=None,
    ):
        """Return the raw value produced by a field-path mapping."""
        return field_getter(record)

    def _resolve_rule_value(
        self,
        line,
        record,
        field_getter=None,
        rule_context=None,
    ):
        """Resolve a value using the Python rule configured on the mapping."""
        if line.specific_rule:
            return self._resolve_specific_rule_value(
                line,
                record,
                rule_context,
            )

        rule_method = self._get_rule_method(line)
        if not rule_method:
            raise UserError(
                _(
                    'No Python rule implements "%(rule)s" for Slim4 field '
                    '"%(field)s".',
                    rule=line.rule_key,
                    field=line.slim4_field,
                ),
            )

        value = rule_method(
            line,
            record,
            field_getter=field_getter,
            rule_context=rule_context,
        )
        return self._normalize_mapping_value(line, value)

    def _resolve_specific_rule_value(
        self,
        line,
        record,
        rule_context=None,
    ):
        eval_context = {
            'record': record,
            'line': line,
            'rule_context': rule_context,
        }

        try:
            safe_eval(
                line.specific_rule.strip(),
                eval_context,
                mode='exec',
                filename=f'<SLIM4 rule: {line.slim4_field}>',
            )
        except Exception as error:
            error_msg = _(
                'Error while executing Python rule for "%(field)s":\n%(error)s',
            ) % {
                'field': line.slim4_field,
                'error': str(error),
            }
            raise UserError(error_msg) from error

        if 'result' not in eval_context:
            raise UserError(
                _('Python rule for "%s" must assign a value to "result".')
                % line.slim4_field,
            )

        return self._normalize_mapping_value(
            line,
            eval_context['result'],
        )

    def _get_rule_method(self, line):
        """Return the interface rule method, falling back to the generic one."""
        interface_method = getattr(
            self,
            f'_rule_{line.rule_key}',
            None,
        )
        if interface_method:
            return interface_method

        return getattr(
            self,
            f'_rule_{line.generic_key}',
            None,
        )

    def _normalize_mapping_value(self, line, value):
        """Normalize a resolved value to the type expected by Slim4."""
        if value is False:
            value = None

        if line.convert_html_field:
            return html2plaintext(value)

        if isinstance(value, list):
            normalized_values = [
                self._normalize_mapping_value(line, item)
                for item in value
            ]
            return (
                normalized_values[0]
                if len(normalized_values) == 1
                else normalized_values
            )

        if value is None:
            return None

        if line.field_type == 'date' and isinstance(value, (date, datetime)):
            return value.strftime('%Y%m%d')

        if line.max_length and isinstance(value, str):
            value = value[:line.max_length]

        converter = {
            'integer': int,
            'decimal': float,
            'char': str,
        }.get(line.field_type)

        return converter(value) if converter else value

    def _rule_warehouse(self, line, record, field_getter=None, rule_context=None):
        """Return the record's warehouse value,
        fall back on all warehouses in rule_context.
        """
        value = field_getter(record) if field_getter else None
        if value:
            return value

        return rule_context.get(
            line.slim4_field,
            None,
        )

    def _get_next_skiptoken(self, source_records):
        """Return the keyset token following the last source record."""
        last_record = source_records[-1]

        return encode_skiptoken(
            last_record.write_date,
            last_record.id,
        )
