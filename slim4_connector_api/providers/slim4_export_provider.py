import base64
import json
from datetime import date, datetime
from operator import attrgetter, methodcaller

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


def encode_skiptoken(write_date, record_id):
    """Encode keyset pagination values as a Base64 JSON token."""
    payload = {
        'write_date': write_date.isoformat(),
        'id': record_id,
    }
    token_json = json.dumps(payload, separators=(',', ':'))
    return base64.b64encode(token_json.encode('utf-8')).decode('ascii')


def decode_skiptoken(skiptoken):
    """Decode and validate a Base64 JSON keyset pagination token."""
    try:
        payload = json.loads(
            base64.b64decode(skiptoken, validate=True).decode('utf-8'),
        )
        last_write_date = datetime.fromisoformat(payload['write_date'])
        last_id = payload['id']

        if isinstance(last_id, bool) or not isinstance(last_id, int):
            raise ValueError('id must be an integer')

    except Exception as error:
        raise ValueError(
            'Invalid $skiptoken: expected Base64 JSON with an ISO write_date '
            'and an integer id.',
        ) from error

    return last_write_date, last_id


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
        source_records = self._get_source_records(
            interface,
            page_size=page_size,
            offset=offset,
            skiptoken=skiptoken,
            **params,
        )
        # overfetching limit = limit + 1 in search()
        has_more = len(source_records) > page_size
        source_records = source_records[:page_size]

        mapping_plan = self._get_mapping_plan(interface)

        rule_context = self._get_rule_context()

        split_mapping = interface.mapping_line_ids.filtered('split_records')

        rows = list(
            self._iter_export_rows(
                source_records,
                mapping_plan,
                split_mapping.slim4_field if split_mapping else None,
                rule_context=rule_context,
            ),
        )

        return {
            'data': rows,
            'has_more': has_more,
            'next_skiptoken': (
                encode_skiptoken(
                    source_records[-1].write_date,
                    source_records[-1].id,
                )
                if has_more else None
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

    def _get_mapping_plan(self, interface):
        user = self.env.user
        mapping_lines = interface.mapping_line_ids.filtered(
            lambda line: line.status == 'validated' and (
                not line.group_id or user.has_group(
                    line.group_id.get_external_id().get(line.group_id.id),
                )
            ),
        )

        return [
            (
                line,
                (
                    methodcaller('mapped', line.field_path)
                    if line.split_records
                    else attrgetter(line.field_path)
                )
                if line.mapping_type in {'field', 'rule'}
                and line.field_path
                else None,
            )
            for line in mapping_lines
        ]

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
        warehouses = self.env['stock.warehouse'].with_company(company.id).search([])
        return list(set(warehouses.mapped('code')))

    def _iter_export_rows(
        self,
        source_records,
        mapping_plan,
        split_key=None,
        rule_context=None,
    ):
        """Yield normalized rows, applying the configured split if present."""
        for record in source_records:
            row = self._prepare_record_row(record, mapping_plan, rule_context)

            split_values = row.get(split_key) if split_key else None

            if not isinstance(split_values, list):
                yield row
                continue

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
            return self._resolve_field_path(record, line, field_getter)

        if line.mapping_type == 'constant':
            return self._normalize_mapping_value(line, line.constant_value)

        if line.mapping_type == 'rule':
            return self._resolve_rule_value(line, record, field_getter, rule_context)

        return None

    def _resolve_field_path(self, record, line, field_getter):
        """Resolve a dotted Odoo field path."""
        return self._normalize_mapping_value(
            line,
            field_getter(record),
        )

    def _resolve_rule_value(self, line, record, field_getter=None, rule_context=None):
        """Resolve a mapping value using the Python rule linked to the rule key."""
        if line.specific_rule:
            return self._resolve_specific_rule_value(
                line,
                record,
                rule_context,
            )
        specific_method = getattr(self, f'_rule_{line.rule_key}', None)
        # try to fall back on a generic method if a specific was not found or
        # implemented in the specific interface
        generic_method = getattr(self, f'_rule_{line.generic_key}', None)
        method = specific_method or generic_method
        if not method:
            return None
        return self._normalize_mapping_value(
            line,
            method(line, record, field_getter=field_getter, rule_context=rule_context),
        )

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

    def _normalize_mapping_value(self, line, value):
        """Normalize a resolved value to the type expected by Slim4."""
        if value is False:
            value = None

        elif isinstance(value, list):
            normalized_values = [
                self._normalize_mapping_value(line, item)
                for item in value
            ]
            value = (
                normalized_values[0]
                if len(normalized_values) == 1
                else normalized_values or None
            )

        elif value is not None:
            if line.field_type == 'date' and isinstance(value, (date, datetime)):
                value = value.strftime('%Y%m%d')
            else:
                if line.max_length and isinstance(value, str):
                    value = value[:line.max_length]

                if line.field_type == 'integer':
                    value = int(value)
                elif line.field_type == 'decimal':
                    value = float(value)
                elif line.field_type == 'boolean':
                    value = bool(value)
                elif line.field_type == 'char':
                    value = str(value if value else '')

        return value

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
