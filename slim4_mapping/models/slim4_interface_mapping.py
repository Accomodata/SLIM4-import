import re
from odoo import _, api, fields, models


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
            ('generated', 'Generated'),
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
            ('error', 'Error'),
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

    _unique_interface_mapping = models.Constraint(
            'unique(interface_id, slim4_field)',
            'Each Slim4 field can only be mapped once per interface.',
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
                field_name: mapping[field_name]
                for field_name in self._DEFAULT_VALUE_FIELDS
            }

    @api.onchange('mapping_type')
    def _onchange_mapping_type(self):
        if self.mapping_type != 'constant':
            self.constant_value = False

        if self.mapping_type not in {'field', 'rule'}:
            self.field_path = False

        if self.mapping_type not in {'generated', 'rule'}:
            self.rule_key = False

    def _restore_default_values(self):
        """Restore the mapping values from the initial snapshot."""
        mappings = self.filtered('default_values_json')

        for mapping in mappings:
            mapping.write(dict(mapping.default_values_json))

        return len(mappings)

    @api.depends('mapping_type', 'interface_id.technical_name', 'slim4_field')
    def _compute_rule_key(self):
        """Compute the technical key for generated/rule mappings."""
        for line in self:
            if line.mapping_type == 'generated':
                line.rule_key = line._get_generated_key(line.slim4_field)
            elif line.mapping_type == 'rule':
                line.rule_key = line._get_default_rule_key(
                    line.interface_id,
                    line.slim4_field,
                )
            else:
                line.rule_key = False

    @api.depends(
        'status',
        'mapping_type',
        'field_path',
        'constant_value',
        'rule_key',
        'interface_id.source_model',
    )
    def _compute_mapping_error(self):
        validated_lines = self.filtered(
            lambda line: line.status in {'validated', 'error'},
        )
        for line in validated_lines:
            if errors := line._get_mapping_errors():
                line.mapping_error = '\n'.join(errors)
            else:
                line.mapping_error = False

        if other_lines := self - validated_lines:
            other_lines.mapping_error = False

    def _get_mapping_errors(self):
        """Return the structural errors for one mapping line."""
        self.ensure_one()

        errors = []
        line_name = _('%s / %s') % (
            self.interface_id.display_name,
            self.slim4_field,
        )

        required_field = self._get_required_fields_by_mapping_type().get(
            self.mapping_type,
        )

        if required_field and not self[required_field]:
            errors.append(
                _('%s: missing %s') % (
                    line_name,
                    required_field,
                ),
            )

        if self._has_invalid_field_path():
            errors.append(
                _('%s: invalid field path "%s" on model %s') % (
                    line_name,
                    self.field_path,
                    self.source_model,
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
            self.mapping_type == 'field'
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

    def _get_generated_key(self, slim4_field):
        """Return the canonical key for a generated Slim4 field."""
        return self._to_snake_name(slim4_field) or False

    def _field_path_is_valid(self):
        """Check whether the field path exists on the configured source model."""
        self.ensure_one()
        if not self.field_path or not self.source_model:
            return True

        model_env = self.env[self.source_model]
        parts = [part for part in self.field_path.split('.') if part]
        for index, part in enumerate(parts):
            field = model_env._fields.get(part)
            if not field:
                return False

            is_last_part = index == len(parts) - 1
            if not is_last_part:
                if not getattr(field, 'comodel_name', False):
                    return False
                model_env = self.env[field.comodel_name]
        return True
