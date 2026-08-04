import json
from odoo import _, fields, models
from odoo.exceptions import UserError
from ..helpers.provider_mapping import get_export_provider


class Slim4Interface(models.Model):
    _inherit = 'slim4.interface'

    mapping_preview_json = fields.Text(
        string='JSON Preview',
        readonly=True,
        copy=False,
    )

    def action_open_json_preview(self):
        """Generate a preview through the same provider used by the API."""
        self.ensure_one()

        if errors := self._get_mapping_config_errors():
            raise UserError(
                _('The mapping configuration is structurally invalid:\n%s')
                % '\n'.join(errors),
            )

        provider = get_export_provider(self.env, self)
        rows = provider.export_interface(self, limit=5)

        self.mapping_preview_json = json.dumps(
            rows,
            indent=2,
            ensure_ascii=False,
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
