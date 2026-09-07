from odoo import models


class Slim4LogisticsExportProvider(models.AbstractModel):
    _name = 'slim4.export.provider.logistics'
    _inherit = 'slim4.export.provider'
    _description = 'Slim4 Logistics Export Provider'

    def _get_supplierinfo(self, record, rule_context=None):
        """Return the supplierinfo used to evaluate the current row."""
        return record.slim4_primary_supplier_id

    def _rule_moq(
        self,
        line,
        record,
        field_getter=None,
        rule_context=None,
    ):
        supplierinfo = self._get_supplierinfo(
            record,
            rule_context=rule_context,
        )
        return (
            supplierinfo.min_qty
            * supplierinfo.product_uom_id.relative_factor
        )

    def _rule_buying_price(
        self,
        line,
        record,
        field_getter=None,
        rule_context=None,
    ):
        supplierinfo = self._get_supplierinfo(
            record,
            rule_context=rule_context,
        )
        target_currency = (
            supplierinfo.partner_id.property_purchase_currency_id
            or record.env.company.currency_id
        )

        if not supplierinfo or not target_currency:
            return 0.0

        return supplierinfo.currency_id._convert(
            from_amount=supplierinfo.price,
            to_currency=target_currency,
            company=record.env.company,
        )
