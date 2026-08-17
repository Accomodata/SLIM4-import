from odoo import models
from odoo.fields import Domain
from odoo.tools import SQL


class Slim4PurchaseOrderExportProvider(models.AbstractModel):
    _name = 'slim4.export.provider.purchase.order'
    _inherit = 'slim4.export.provider'
    _description = 'Slim4 Purchase Order Export Provider'

    def _get_source_domain(self, interface):
        """Keep only purchase lines with a strictly positive open quantity."""
        domain = super()._get_source_domain(interface)
        # WHERE product_qty > qty_received
        domain = [
            *domain,
            Domain.custom(
                to_sql=lambda model, alias, query: SQL(
                    '%s > %s',
                    model._field_to_sql(alias, 'product_qty', query),
                    model._field_to_sql(alias, 'qty_received', query),
                ),
            ),
        ]
        return domain

    def _rule_purchase_order_open_quantity(
            self,
            line,
            record,
            field_getter=None,
            rule_context=None,
        ):
        return record.product_qty - record.qty_received
