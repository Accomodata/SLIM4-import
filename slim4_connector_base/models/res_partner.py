from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    same_ref_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner with the same reference',
        compute='_compute_same_ref_partner_id',
        store=False,
    )

    @api.depends('ref', 'company_id')
    def _compute_same_ref_partner_id(self):
        """Find another partner using the same reference."""
        partner_sudo = self.with_context(active_test=False).sudo()
        for partner in self:
            domain = [('ref', '=', partner.ref)]

            if partner.company_id:
                domain.append(
                    ('company_id', 'in', [False, partner.company_id.id]),
                )

            if partner._origin.id:
                domain.append(
                    ('id', '!=', partner._origin.id),
                )

            partner.same_ref_partner_id = (
                bool(partner.ref)
                and partner_sudo.search(domain, limit=1)
            )
