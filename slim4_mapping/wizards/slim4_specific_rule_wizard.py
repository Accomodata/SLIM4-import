
from odoo import fields, models


class Slim4SpecificRuleWizard(models.TransientModel):
    _name = 'slim4.specific.rule.wizard'
    _description = 'Edit Slim4 Specific Rule'

    mapping_id = fields.Many2one(
        comodel_name='slim4.interface.mapping',
        required=True,
        readonly=True,
    )

    code = fields.Text(
        string='Python Code',
    )

    def action_save(self):
        self.ensure_one()
        self.mapping_id.specific_rule = self.code or False
        return {'type': 'ir.actions.act_window_close'}
