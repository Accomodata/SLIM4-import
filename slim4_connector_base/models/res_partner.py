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
        """Find partners with matching references in one batched lookup."""
        self.same_ref_partner_id = False
        partners = self.filtered('ref')
        if not partners:
            return

        partner_sudo = self.with_context(active_test=False).sudo()
        partners_by_ref = partner_sudo.search_fetch(
            [('ref', 'in', partners.mapped('ref'))],
            ['ref', 'company_id'],
        ).grouped('ref')

        for partner in partners:
            domain = []

            if partner.company_id:
                domain.append(
                    ('company_id', 'in', [False, partner.company_id.id]),
                )

            if partner._origin.id:
                domain.append(
                    ('id', '!=', partner._origin.id),
                )

            candidates = partners_by_ref.get(
                partner.ref,
                partner_sudo.browse(),
            )
            partner.same_ref_partner_id = candidates.filtered_domain(domain)[:1]
