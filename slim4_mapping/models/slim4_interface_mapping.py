from odoo import fields, models


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
            ('generated', 'Generated Value'),
            ('rule', 'Python Rule'),
            ('manual', 'Manual / To Define'),
            ('ignored', 'Ignored / Not Used Now'),
        ],
        required=True,
        default='field',
    )

    field_type = fields.Selection(
        selection=[
            ('integer', 'Integer'),
            ('char', 'Char'),
            ('date', 'Date'),
        ],
    )
    max_length = fields.Integer(
        string='Field Max length value',
    )
    field_path = fields.Char(
        help='Example: order_id.name or product_id.default_code.',
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
            'interface_slim4_field_unique',
            'unique(interface_id, slim4_field)',
            'Each Slim4 field can only be mapped once per interface.',
    )

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
