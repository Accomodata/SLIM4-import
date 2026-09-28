from odoo import models
from operator import attrgetter, methodcaller


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

    def _get_mapping_field_getter(self, line):
        """Apply ``mapped`` to stockedItem fields, as they use an O2M relation
        (``configured_warehouse_ids.slim4_stocked_item``).
        """
        if not self.env.user.has_group('slim4_connector_base.stocked_item_field'):
            return super()._get_mapping_field_getter(line)
        if (
            line.mapping_type not in {'field', 'rule'}
            or not line.field_path
        ):
            return None
        # Use ``mapped`` for stockedItem fields to support the O2M relation.
        if line.split_records or line.slim4_field == 'stockedItem':
            return methodcaller('mapped', line.field_path)

        return attrgetter(line.field_path)

    def _iter_split_rows(self, row, split_key=None):
        """Split rows by warehouse and keep the matching stocked item value.
        ``stockedItem`` is mapped as a list because it comes from an O2M
        relation. When splitting the row by warehouse, select the stocked item
        at the same index as the current warehouse(code) to preserve the mapping
        between both values.
        """
        if not self.env.user.has_group(
                'slim4_connector_base.stocked_item_field',
            ):
            yield from super()._iter_split_rows(row, split_key)
        else:
            wh_codes = row.get(split_key) if split_key else None
            if not isinstance(wh_codes, list):
                yield row
                return

            for idx, wh_code in enumerate(wh_codes):
                split_row = row.copy()
                split_row[split_key] = wh_code
                # ``stockedItem`` contains one value per warehouse. Keep the
                # value corresponding to the warehouse currently being split.
                stocked_item_vals = split_row.get('stockedItem', [])
                stocked_item = stocked_item_vals[idx]
                split_row['stockedItem'] = (
                    stocked_item.upper() if isinstance(stocked_item, str)
                    else stocked_item
                )
                yield split_row
