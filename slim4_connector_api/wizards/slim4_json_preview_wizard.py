from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

MAX_PAGE_SIZE = 1000


class Slim4JsonPreviewWizard(models.TransientModel):
    _name = 'slim4.json.preview.wizard'
    _description = 'Preview JSON'

    interface_id = fields.Many2one(
        comodel_name='slim4.interface',
        required=True,
        readonly=True,
    )

    model_id = fields.Many2one(
        comodel_name='ir.model',
        related='interface_id.source_model_id',
        readonly=True,
    )

    model_name = fields.Char(
        related='model_id.model',
        readonly=True,
    )

    source_domain = fields.Text(
        related='interface_id.source_domain',
        readonly=True,
    )
    record_id = fields.Many2oneReference(
        string='Record',
        model_field='model_name',
    )

    query_limit = fields.Integer(
        string='Limit',
        default=5,
        help='Number of Odoo records to query (between 1 and 1000).',
    )

    @api.onchange('record_id')
    def _onchange_record_id(self):
        if self.record_id:
            self.query_limit = 1

    def action_create_json_preview(self):
        self.ensure_one()
        page_size = 1 if self.record_id else self.query_limit

        if not 1 <= page_size <= MAX_PAGE_SIZE:
            raise ValidationError(
                _('The limit must be between 1 and 1000.'),
            )

        return self.interface_id._create_json_preview(
            page_size=page_size,
            record=self.record_id,
        )
