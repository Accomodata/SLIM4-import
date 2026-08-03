import ast
import json

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
        string='Source Model',
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
    last_record_count = fields.Integer(
        string='Last Record Count', readonly=True,
    )
    last_count_date = fields.Datetime(
        string='Last Count Date', readonly=True,
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
    mapping_preview_json = fields.Text(
        compute='_compute_mapping_preview_json',
        readonly=True,
    )

    _sql_constraints = [
        (
            'technical_name_unique',
            'unique(technical_name)',
            'The technical name must be unique.',
        ),
    ]

    @api.depends('mapping_line_ids')
    def _compute_mapping_count(self):
        for interface in self:
            interface.mapping_count = len(interface.mapping_line_ids)

    @api.depends(
        'mapping_line_ids.slim4_field',
        'mapping_line_ids.mapping_type',
        'mapping_line_ids.field_path',
        'mapping_line_ids.slim4_required',
        'mapping_line_ids.field_type',
        'mapping_line_ids.max_length',
    )
    def _compute_mapping_preview_json(self):
        for interface in self:
            preview = [
                {
                    'slim4_field': line.slim4_field,
                    'mapping_type': line.mapping_type,
                    'field_path': line.field_path or False,
                    'slim4_required': line.slim4_required,
                    'field_type': line.field_type,
                    'max_length': line.max_length,
                }
                for line in interface.mapping_line_ids.sorted(
                    lambda line: (line.sequence, line.id),
                )
            ]
            interface.mapping_preview_json = json.dumps(preview, indent=2, default=str)

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

    def _get_source_domain(self):
        self.ensure_one()
        domain_text = (self.source_domain or '').strip()
        if not domain_text:
            return []

        try:
            domain = ast.literal_eval(domain_text)
        except Exception as error:
            raise UserError(_('Invalid source domain:\n%s') % error) from error

        if not isinstance(domain, list):
            raise UserError(_('The source domain must be a list.'))

        return domain

    def action_refresh_record_count(self):
        for interface in self:
            model_env = interface._get_source_model_env()
            domain = interface._get_source_domain()
            try:
                count = model_env.search_count(domain)
            except Exception as error:
                raise UserError(
                    _('Error while counting matching records:\n%s') % error,
                ) from error

            interface.write(
                {
                    'last_record_count': count,
                    'last_count_date': fields.Datetime.now(),
                },
            )
        return True

    def action_open_matching_records(self):
        self.ensure_one()
        self._get_source_model_env()
        domain = self._get_source_domain()

        return {
            'name': _('%s - Matching Records') % self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': self.source_model,
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }

    def action_reset_count(self):
        self.write(
            {
                'last_record_count': 0,
                'last_count_date': False,
            },
        )
        return True

    def action_validate_mapping_config(self):
        """Validate that the mapping is structurally coherent."""
        source_config_errors = [
            _('%s: %s') % (interface.display_name, error)
            for interface in self
            for error in interface._get_source_configuration_errors()
        ]

        invalid_field_path_errors = [
            _('%s / %s: invalid field path "%s" on model %s')
            % (
                line.interface_id.display_name,
                line.slim4_field,
                line.field_path,
                line.source_model,
            )
            for line in self.mapped('mapping_line_ids')
            if line.mapping_type == 'field'
            and line.field_path
            and line.source_model
            and line.source_model in self.env
            and not line._field_path_is_valid()
        ]

        if errors := (
            source_config_errors +
            invalid_field_path_errors
        ):
            raise UserError('\n'.join(errors))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Mapping configuration validated'),
                'message': _('The mapping configuration is structurally valid.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def _get_source_configuration_errors(self):
        self.ensure_one()
        errors = []

        if not self.source_model:
            errors.append(_('No source model configured.'))

        elif self.source_model not in self.env:
            errors.append(
                _('The source model %s is not installed.') % self.source_model,
            )

        domain_text = (self.source_domain or '').strip()
        if domain_text:
            try:
                domain = ast.literal_eval(domain_text)
            except Exception as error:
                errors.append(_('Invalid source domain: %s') % error)
            else:
                if not isinstance(domain, list):
                    errors.append(_('The source domain must be a list.'))

        return errors
