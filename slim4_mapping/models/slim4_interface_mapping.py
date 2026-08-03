import re
from odoo import api, fields, models


class Slim4InterfaceMapping(models.Model):
    _name = 'slim4.interface.mapping'
    _description = 'Slim4 Interface Mapping'
    _order = 'interface_id, sequence, id'

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
            ('ignored', 'Ignored / Not Used Now'),
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
            ('ready', 'Ready'),
            ('to_validate', 'To Validate'),
            ('ignored', 'Ignored'),
        ],
        required=True,
        default='to_validate',
    )
    notes = fields.Text(

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

    _unique_interface_mapping = models.Constraint(
            'unique(interface_id, slim4_field)',
            'Each Slim4 field can only be mapped once per interface.',
    )

    @api.depends('mapping_type', 'interface_id.technical_name', 'slim4_field')
    def _compute_rule_key(self):
        """Compute a deterministic technical key for generated/rule mappings."""
        for line in self:
            if line.mapping_type not in {'generated', 'rule'}:
                line.rule_key = False
                continue
            line.rule_key = line._get_default_rule_key(
                line.interface_id,
                line.slim4_field,
            )

    def _to_snake_name(self, value):
        """Convert a Slim4/Odoo technical string to snake_case."""
        value = value or ''
        # Keep the stored interface technical name exact, but normalize prefixes
        # when deriving pythonic rule keys.  `Slim4Import_` is accepted here only
        # to make the helper robust if old data is still present during upgrade.
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
