import ast
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

    def _get_rule_context(self):
        """Add warehouses aggregated by stocked item."""
        rule_context = super()._get_rule_context()
        if self.env.user.has_group('slim4_connector_base.stocked_item_field'):
            rule_context = {
                **rule_context,
                'stockedItem': self._get_wh_by_stocked_item(),

            }

        return rule_context

    def _get_wh_by_stocked_item(self):
        warehouses = self._get_all_warehouses()
        return {
            wh.code: wh.slim4_stocked_item.upper() for wh in warehouses.filtered(
                'slim4_stocked_item',
            )
        }

    def _rule_logistics_stocked_item(
        self,
        line,
        record,
        field_getter=None,
        rule_context=None,
    ):
        """Follow the exact same logic as warehouse rule:
        Return the record's warehouse.slim4_stocked_item value,
        fall back on all warehouses in rule_context.
        """
        value = field_getter(record) if field_getter else None
        if value:
            return value

        return rule_context.get(
            line.slim4_field,
            None,
    )

    def _iter_split_rows(self, row, split_key=None):
        """Add the correct stocked item value on row when splitting by warehouse."""
        if split_key != 'warehouse' or not self.env.user.has_group(
                'slim4_connector_base.stocked_item_field',
            ):
            yield from super()._iter_split_rows(row, split_key)
        else:
            wh_codes = row.get(split_key) if split_key else None
            if not isinstance(wh_codes, list):
                yield row
                return

            for wh_code in wh_codes:
                split_row = row.copy()
                split_row[split_key] = wh_code
                stocked_item_by_wh_code = (
                    ast.literal_eval(split_row['stockedItem']) or {}
                )
                split_row['stockedItem'] = stocked_item_by_wh_code.get(wh_code, None)
                yield split_row
