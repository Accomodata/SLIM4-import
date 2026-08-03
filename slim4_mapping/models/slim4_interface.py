from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Slim4Interface(models.Model):
    _name = 'slim4.interface'
    _description = 'Slim4 Interface'
    _order = 'name'

    name = fields.Char(
        required=True,
    )
    technical_name = fields.Char(
        required=True,
        help='Internal identifier used by the Slim4 export service.',
    )
    source_model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Root Source Model',
        required=True,
        ondelete='cascade',
        help='Technical Odoo model used as source for this Slim4 interface.',
    )
    source_model = fields.Char(
        related='source_model_id.model',
        string='Source Model Name',
        store=True,
        readonly=True,
    )
    source_domain = fields.Text(
        default='[]',
        help='Static Odoo domain used to preview source records for this interface.',
    )
    active = fields.Boolean(
        default=True,
    )
    notes = fields.Text(

    )
    mapping_line_ids = fields.One2many(
        comodel_name='slim4.interface.mapping',
        inverse_name='interface_id',
        string='Field Mappings',
    )
    mapping_count = fields.Integer(
        compute='_compute_mapping_count',
    )

    _interface_unique_technical_name = models.Constraint(
            'unique(technical_name)',
            'The technical name must be unique.',
        )

    @api.depends('mapping_line_ids')
    def _compute_mapping_count(self):
        for interface in self:
            interface.mapping_count = len(interface.mapping_line_ids)

    def action_reset_mapping_to_default(self):
        """Restore the default values of the interface mappings."""
        self.ensure_one()
        self.mapping_line_ids._restore_default_values()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _get_source_model_env(self):
        self.ensure_one()
        if not self.source_model:
            raise UserError(
                _('No source model configured for interface %s.') % self.display_name,
            )
        try:
            return self.env[self.source_model]
        except KeyError as error:
            raise UserError(
                _('The source model %s is not installed.') % self.source_model,
            ) from error

    def action_validate_mapping_config(self):
        """Validate that the mapping configuration is structurally coherent."""
        self.ensure_one()
        errors = self._get_mapping_config_errors()
        if errors:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Mapping configuration not valid'),
                    'message': _(
                        'The mapping configuration is structurally invalid:\n%s',
                    ) % '\n'.join(errors),
                    'type': 'danger',
                    'sticky': True,
                },
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Mapping configuration validated'),
                'message': _(
                    'The mapping configuration is structurally valid.',
                ),
                'type': 'success',
                'sticky': False,
            },
        }

    def _get_mapping_config_errors(self):
        """Aggregate interface and mapping-line configuration errors."""
        self.ensure_one()
        source_errors = [
            _('%s: %s') % (
                self.display_name,
                error,
            )
            for error in self._get_source_configuration_errors()
        ]

        mapping_errors = self.mapping_line_ids.filtered(
            'mapping_error',
        ).mapped('mapping_error')

        return source_errors + mapping_errors

    def _get_source_configuration_errors(self):
        self.ensure_one()
        errors = []

        if not self.source_model:
            errors.append(_('No source model configured.'))

        if self.source_model not in self.env:
            errors.append(
                _('The source model %s is not installed.') % self.source_model,
            )

        return errors
