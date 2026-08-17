import json

from odoo import api, fields, models

SLIM4_VISIBLE_FIELD_PARAM = 'slim4_mapping.visible_field_keys'

# Map feature technical keys to target model.field strings
SLIM4_FEATURES = {
    'moq': [
        'product.product.slim4_moq',
        'product.template.slim4_moq',
    ],
    'ioq': [
        'product.product.slim4_ioq',
        'product.template.slim4_ioq',
    ],
    'warehouse': [
        'product.product.warehouse_ids',
    ],
}


def get_slim4_visible_field_keys(env):
    raw_value = env['ir.config_parameter'].sudo().get_param(
        SLIM4_VISIBLE_FIELD_PARAM,
        '[]',
    )
    try:
        configured_keys = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return []

    return configured_keys if isinstance(configured_keys, list) else []


class Slim4FeatureTag(models.Model):
    _name = 'slim4.feature.tag'
    _description = 'Slim4 Feature Tag'

    name = fields.Char(string='Feature Name', required=True)
    technical_name = fields.Char(string='Technical Key', required=True, index=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    slim4_feature_tag_ids = fields.Many2many(
        comodel_name='slim4.feature.tag',
        string='Visible Slim4 Features',
        help='Select features to activate associated model fields.',
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        configured_keys = set(get_slim4_visible_field_keys(self.env))

        # Identify tags where ALL mapped fields are active
        active_tech_names = []
        for feature_key, mapped_fields in SLIM4_FEATURES.items():
            if set(mapped_fields).issubset(configured_keys):
                active_tech_names.append(feature_key)

        # Lookup tag records by technical_name
        active_tags = self.env['slim4.feature.tag'].sudo().search([
            ('technical_name', 'in', active_tech_names)
        ])

        # Assign Many2many command tuple: (6, 0, [IDs])
        res['slim4_feature_tag_ids'] = [(6, 0, active_tags.ids)]
        return res

    def set_values(self):
        super().set_values()
        selected_tags = self.slim4_feature_tag_ids.mapped('technical_name')

        # Map selected tag technical names back to target model fields
        active_visible_keys = set()
        for tag in selected_tags:
            if tag in SLIM4_FEATURES:
                active_visible_keys.update(SLIM4_FEATURES[tag])

        self.env['ir.config_parameter'].sudo().set_param(
            SLIM4_VISIBLE_FIELD_PARAM,
            json.dumps(sorted(active_visible_keys)),
        )
