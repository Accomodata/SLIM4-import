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

    def action_open_json_preview_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('JSON Preview'),
            'res_model': 'slim4.json.preview.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_interface_id': self.id,
                'default_model_id': self.source_model_id.id,
            },
        }

    def _create_json_preview(self, page_size, record=None):
        """Generate a preview through the same provider used by the API."""
        self.ensure_one()

        if errors := self._get_mapping_config_errors():
            raise UserError(
                _('The mapping configuration is structurally invalid:\n%s')
                % '\n'.join(errors),
            )

        try:
            provider = get_export_provider(self.env, self)
            params = {'filter_record': record}
            rows = provider.export_interface(
                self,
                page_size=page_size,
                params=params,
            )
        except UserError:
            raise
        except Exception as error:
            raise UserError(
                _('Unable to generate the JSON preview:\n%s') % str(error),
            ) from error

        if record and not rows.get('data'):
            raise UserError(
                _(
                    'No data found to generate the JSON preview for record: %s.\n'
                    'Please check the source domain and export filters.\n'
                    'Source domain: %s',
                ) % (record, self.source_domain),
            )

        self.mapping_preview_json = json.dumps(
            rows,
            indent=2,
            ensure_ascii=False,
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
