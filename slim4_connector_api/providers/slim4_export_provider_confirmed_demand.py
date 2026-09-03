from odoo import models
from operator import attrgetter


class Slim4ConfirmedDemandExportProvider(models.AbstractModel):
    _name = 'slim4.export.provider.confirmed.demand'
    _inherit = 'slim4.export.provider'
    _description = 'Slim4 Confirmed Demand Export Provider'

    def _get_rule_context(self):
        """Add fall back to expected date."""
        rule_context = super()._get_rule_context()
        rule_context = {
            **rule_context,
            'requiredDate': 'order_id.expected_date',

        }

        return rule_context

    def _rule_confirmed_demand_required_date(
        self,
        line,
        record,
        field_getter=None,
        rule_context=None,
    ):

        if commitment_date := field_getter(record) if field_getter else None:
            return commitment_date

        field_getter = attrgetter(
            rule_context.get(line.slim4_field),
        )

        expected_date_fallback = field_getter(
          record,
        )

        return expected_date_fallback
