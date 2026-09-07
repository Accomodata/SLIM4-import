import re
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import test_python_expr


class Slim4InterfaceMapping(models.Model):
    _name = 'slim4.interface.mapping'
    _description = 'Slim4 Interface Mapping'
    _order = 'interface_id, sequence, id'

    _DEFAULT_VALUE_FIELDS = (
        'sequence',
        'mapping_type',
        'field_path',
        'constant_value',
        'rule_key',
        'slim4_required',
        'status',
        'specific_rule',
        'split_records',
        'group_id',
    )

    name = fields.Char(
        compute='_compute_name',
    )
    interface_id = fields.Many2one(
        comodel_name='slim4.interface',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(
        default=10,
    )
    slim4_field = fields.Char(
        string='Slim4 Field',
        required=True,
        help='Target Slim4 field, for example poNumber, code or openQuantity.',
    )
    mapping_type = fields.Selection(
        selection=[
            ('field', 'Odoo Field Path'),
            ('constant', 'Constant Value'),
            ('rule', 'Python Rule'),
        ],
        required=True,
        default='field',
    )
    field_type = fields.Selection(
        selection=[
            ('integer', 'Integer'),
            ('decimal', 'Decimal'),
            ('char', 'Char'),
            ('date', 'Date'),
            ('time', 'Time'),
            ('boolean', 'Boolean'),
        ],
    )
    field_path = fields.Char(
        help='Example: order_id.name or product_id.default_code.',
    )
    constant_value = fields.Char(
    )
    rule_key = fields.Char(
        compute='_compute_rule_key',
        store=True,
        readonly=True,
        help=(
            'Computed from the interface technical name and the Slim4 field name. '
            'Example: S4Import_PurchaseOrder + openQuantity -> '
            'purchase_order_open_quantity.'
        ),
    )

    generic_key = fields.Char(
            compute='_compute_rule_key',
            store=True,
            readonly=True,
    )

    max_length = fields.Integer(

    )
    slim4_required = fields.Boolean(
        default=False,
    )
    status = fields.Selection(
        selection=[
            ('validated', 'Validated'),
            ('to_validate', 'To Validate'),
            ('ignored', 'Ignored'),
        ],
        required=True,
        default='to_validate',
    )
    notes = fields.Text(

    )
    mapping_error = fields.Text(
        compute='_compute_mapping_error',
    )
    interface_technical_name = fields.Char(
        related='interface_id.technical_name',
        readonly=True,
        store=True,
    )
    source_model = fields.Char(
        related='interface_id.source_model',
        readonly=True,
        store=True,
    )
    default_values_json = fields.Json(
        readonly=True,
        copy=False,
    )

    specific_rule = fields.Text(
        string='Specific Python Rule',
    )

    split_records = fields.Boolean(
        string='Split Records',
        help=(
            'Create one JSON record for each value returned by this mapping.'
        ),
    )

    group_id = fields.Many2one(
        comodel_name='res.groups',
        string='Security Group',
    )

    convert_html_field = fields.Boolean(
        string='Convert HTML to text',
        compute='_compute_convert_html_field',
        help=(
            'Indicates that the mapped Odoo field contains HTML that must be '
            'converted to plain text before export.'
        ),
    )

    _unique_interface_mapping = models.Constraint(
        'unique(interface_id, slim4_field, group_id)',
        'Each Slim4 field can only be mapped once per group on the same interface.',
    )

    @api.constrains('specific_rule')
    def _check_specific_rule(self):
        for mapping in self.filtered('specific_rule'):
            if error := test_python_expr(
                mapping.specific_rule.strip(),
                mode='exec',
            ):
                raise ValidationError(error)

    @api.constrains('interface_id', 'split_records')
    def _check_single_split_mapping(self):
        for mapping in self.filtered('split_records'):
            other_mapping = self.search([
                ('interface_id', '=', mapping.interface_id.id),
                ('split_records', '=', True),
                ('id', '!=', mapping.id),
            ], limit=1)
            if other_mapping:
                raise ValidationError(
                    self.env._('Only one mapping can split records for interface %s.')
                    % mapping.interface_id.display_name,
                )

    @api.model
    def create_default_values_snapshots(self, module_name):
        """Create initial snapshots for the module's standard mapping records."""
        xml_data = self.env['ir.model.data'].search([
            ('module', '=', module_name),
            ('model', '=', self._name),
        ])

        mappings = self.browse(xml_data.mapped('res_id')).exists()
        for mapping in mappings:
            mapping.default_values_json = {
                field_name: mapping._get_default_snapshot_value(field_name)
                for field_name in self._DEFAULT_VALUE_FIELDS
            }

    def _get_default_snapshot_value(self, field_name):
        value = self[field_name]

        if self._fields[field_name].type == 'many2one':
            return value.id or False

        return value

    @api.onchange('mapping_type', 'constant_value', 'rule_key')
    def _onchange_mapping_type(self):
        if self.mapping_type != 'constant':
            self.constant_value = False

        if self.mapping_type not in {'field', 'rule'}:
            self.field_path = False

        if self.mapping_type != 'rule':
            self.rule_key = False
            self.convert_html_field = False

    @api.depends('interface_technical_name', 'slim4_field')
    def _compute_name(self):
        for line in self:
            line.name = f'{line.interface_technical_name}: {line.slim4_field}'

    @api.depends('mapping_type', 'interface_id.technical_name', 'slim4_field')
    def _compute_rule_key(self):
        """Compute the technical key for rule mappings."""
        rule_mappings = self.filtered(lambda m: m.mapping_type == 'rule')
        other_mappings = self - rule_mappings
        for line in rule_mappings:
            if line.mapping_type == 'rule':
                line.rule_key = self._get_default_rule_key(
                    line.interface_id,
                    line.slim4_field,
                )
                line.generic_key = self._get_generic_key(
                    line.slim4_field,
                )
        other_mappings.rule_key = False
        other_mappings.generic_key = False

    @api.depends_context('uid')
    @api.depends(
        'status',
        'mapping_type',
        'field_path',
        'source_model',
    )
    def _compute_convert_html_field(self):
        field_mappings = self.filtered(
            lambda line: (
                line.status == 'validated'
                and line.mapping_type == 'field'
                and line.field_path
            ),
        )

        (self - field_mappings).convert_html_field = False

        for line in field_mappings:
            field_info = line._get_field_path_info()
            line.convert_html_field = bool(
                field_info
                and field_info.get('type') == 'html',
            )

    @api.depends_context('uid')
    @api.depends(
        'status',
        'mapping_type',
        'field_path',
        'constant_value',
        'rule_key',
        'group_id',
        'interface_id.source_model',
    )
    def _compute_mapping_error(self):
        validated_lines = self.filtered(
            lambda line: line.status == 'validated',
        )
        for line in validated_lines:
            if errors := line._get_mapping_errors():
                line.mapping_error = '\n'.join(errors)
            else:
                line.mapping_error = False

        if other_lines := self - validated_lines:
            other_lines.mapping_error = False

    def action_open_specific_rule_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Python Rule'),
            'res_model': 'slim4.specific.rule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_mapping_id': self.id,
                'default_code': self.specific_rule,
            },
        }

    def _get_mapping_errors(self):
        """Return the structural errors for one mapping line."""
        self.ensure_one()

        errors = []
        line_name = self.env._('%s / %s') % (
            self.interface_id.display_name,
            self.slim4_field,
        )

        required_field = self._get_required_fields_by_mapping_type().get(
            self.mapping_type,
        )

        if required_field and not self[required_field]:
            errors.append(
                self.env._('%s: missing %s') % (
                    line_name,
                    required_field,
                ),
            )

        if self._has_invalid_field_path():
            errors.append(
                self.env._(
                    '%s: field path "%s" is invalid or unavailable. '
                    'Enable the required feature or configure a replacement.',
                ) % (
                    line_name,
                    self.field_path,
                ),
            )

        return errors

    def _get_required_fields_by_mapping_type(self):
        return {
            'field': 'field_path',
            'constant': 'constant_value',
            'rule': 'rule_key',
        }

    def _has_invalid_field_path(self):
        """Check whether the configured field path is invalid."""
        self.ensure_one()
        return (
            self.mapping_type in {'field', 'rule'}
            and self.field_path
            and self.source_model
            and self.source_model in self.env
            and not self._field_path_is_valid()
        )

    def _to_snake_name(self, value):
        """Convert a Slim4/Odoo technical string to snake_case."""
        value = value or ''
        value = re.sub(r'^(S4Import|Slim4Import)_?', '', value.strip())
        value = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', value)
        value = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', value)
        value = re.sub(r'[^0-9A-Za-z_]+', '_', value)
        return re.sub(r'_+', '_', value).strip('_').lower()

    def _get_default_rule_key(self, interface, slim4_field):
        """Return the canonical rule key for an interface field.

        Examples:
            S4Import_PurchaseOrder + openQuantity = purchase_order_open_quantity
            S4Import_StockDetails + availableQuantity = stock_details_available_quantity

        """
        iface = interface or self.interface_id
        interface_part = self._to_snake_name(iface.technical_name if iface else '')
        field_part = self._to_snake_name(slim4_field)

        return '_'.join(part for part in (interface_part, field_part) if part) or False

    def _get_generic_key(self, slim4_field):
        """Return the canonical key for a generic Slim4 field."""
        return self._to_snake_name(slim4_field) or False

    def _field_path_is_valid(self):
        """Check whether the field path exists and is available."""
        self.ensure_one()

        if not self.field_path or not self.source_model:
            return True

        return bool(self._get_field_path_info())

    def _get_field_path_info(self):
        """Return the final field metadata when the field path is valid."""
        self.ensure_one()

        if (
            not self.field_path
            or not self.source_model
            or self.source_model not in self.env
        ):
            return None

        model_env = self.env[self.source_model]
        field_names = self.field_path.split('.')
        field_info = None

        for index, field_name in enumerate(field_names):
            field_info = model_env.fields_get([field_name]).get(field_name)
            if not field_info:
                return None

            if index < len(field_names) - 1:
                comodel_name = field_info.get('relation')
                if not comodel_name:
                    return None

                model_env = self.env[comodel_name]

        return field_info

    def _restore_default_values(self):
        """Restore the mapping values from the initial snapshot."""
        mappings = self.filtered('default_values_json')

        for mapping in mappings:
            mapping.write(dict(mapping.default_values_json))

        return len(mappings)
