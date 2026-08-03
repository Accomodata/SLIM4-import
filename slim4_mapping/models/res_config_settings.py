import json

from odoo import api, fields, models


SLIM4_VISIBLE_FIELD_PARAM = 'slim4_mapping.visible_field_keys'
SLIM4_VISIBLE_FIELD_KEYS = (
    'product.template.warehouse_ids',
)


def get_slim4_visible_field_keys(env):
    default_keys = list(SLIM4_VISIBLE_FIELD_KEYS)
    raw_value = env['ir.config_parameter'].sudo().get_param(
        SLIM4_VISIBLE_FIELD_PARAM,
        json.dumps(default_keys),
    )
    try:
        configured_keys = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return default_keys

    return configured_keys if isinstance(configured_keys, list) else default_keys


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    slim4_visible_field_ids = fields.Many2many(
        comodel_name='ir.model.fields',
        relation='slim4_config_settings_field_rel',
        column1='config_id',
        column2='field_id',
        string='Visible Slim4 Fields',
        domain=lambda self: [
            ('id', 'in', self._get_slim4_available_fields().ids),
        ],
        help='Slim4-specific fields displayed in the Odoo user interface.',
    )

    @api.model
    def _get_slim4_available_fields(self):
        model_fields = self.env['ir.model.fields'].sudo()
        field_ids = []
        for field_key in SLIM4_VISIBLE_FIELD_KEYS:
            model_name, field_name = field_key.rsplit('.', 1)
            field = model_fields._get(model_name, field_name)
            if field:
                field_ids.append(field.id)
        return model_fields.browse(field_ids)

    @api.model
    def get_values(self):
        values = super().get_values()
        visible_keys = get_slim4_visible_field_keys(self.env)
        visible_fields = self._get_slim4_available_fields().filtered(
            lambda field: f'{field.model}.{field.name}' in visible_keys,
        )
        values['slim4_visible_field_ids'] = [(6, 0, visible_fields.ids)]
        return values

    def set_values(self):
        super().set_values()
        visible_keys = sorted(
            f'{field.model}.{field.name}'
            for field in self.slim4_visible_field_ids
            if f'{field.model}.{field.name}' in SLIM4_VISIBLE_FIELD_KEYS
        )
        self.env['ir.config_parameter'].sudo().set_param(
            SLIM4_VISIBLE_FIELD_PARAM,
            json.dumps(visible_keys),
        )
