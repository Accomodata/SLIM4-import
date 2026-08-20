import json

from odoo import api, fields, models


class Slim4InboundMessage(models.Model):
    _name = 'slim4.inbound.message'
    _description = 'Slim4 Inbound Message'
    _order = 'create_date desc, id desc'
    _rec_name = 'batch_reference'

    operation = fields.Char(
        required=True,
        readonly=True,
        index=True,
    )
    batch_reference = fields.Char(
        required=True,
        readonly=True,
        copy=False,
        index=True,
    )
    item_index = fields.Integer(
        required=True,
        readonly=True,
    )
    payload = fields.Json(
        required=True,
        readonly=True,
        copy=False,
    )
    payload_display = fields.Text(
        compute='_compute_payload_display',
    )
    supplier_id = fields.Many2one(
        comodel_name='res.partner',
        readonly=True,
        index=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        readonly=True,
        index=True,
    )
    status = fields.Selection(
        selection=[
            ('received', 'Received'),
            ('processed', 'Processed'),
            ('error', 'Error'),
        ],
        required=True,
        default='received',
        readonly=True,
        index=True,
    )
    error_message = fields.Text(
        readonly=True,
        copy=False,
    )
    processed_at = fields.Datetime(
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
        index=True,
    )

    _batch_item_unique = models.Constraint(
        'unique(batch_reference, item_index)',
        'Each item index must be unique within an inbound Slim4 batch.',
    )

    @api.depends('payload')
    def _compute_payload_display(self):
        for message in self:
            message.payload_display = json.dumps(
                message.payload or {},
                indent=2,
                ensure_ascii=False,
            )
