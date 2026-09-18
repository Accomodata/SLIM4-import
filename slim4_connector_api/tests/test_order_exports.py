from freezegun import freeze_time

from odoo import Command
from odoo.tests import TransactionCase, tagged

from ..helpers.provider_mapping import get_export_provider


@tagged('post_install', '-at_install', 'slim4_business')
class TestPurchaseOrderExport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Test purchase export vendor',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Test purchased article', 'default_code': 'S4-PO', 'type': 'consu',
        })
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test purchase export warehouse', 'code': 'S4PO',
        })
        cls.interface = cls.env.ref(
            'slim4_connector_base.slim4_interface_purchase_order',
        )
        cls.interface.source_domain = (
            f"{cls.interface.source_domain} + "
            f"[('order_id.partner_id', '=', {cls.vendor.id})]"
        )
        cls.provider = get_export_provider(cls.env, cls.interface)

    def _create_order(self, quantity=10):
        return self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'picking_type_id': self.warehouse.in_type_id.id,
            'date_order': '2026-01-10 09:00:00',
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_qty': quantity,
                'price_unit': 12.5,
                'date_planned': '2026-02-03 12:00:00',
            })],
        })

    def test_confirmed_open_order_exports_quantities_dates_and_plain_text(self):
        order = self._create_order()
        order.note = '<p>Handle with care</p>'
        order.button_confirm()
        rows = self.provider.export_interface(self.interface)['data']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['number'], order.name)
        self.assertEqual(rows[0]['warehouse'], 'S4PO')
        self.assertEqual(rows[0]['code'], 'S4-PO')
        self.assertEqual(rows[0]['originalQuantity'], 10)
        self.assertEqual(rows[0]['suppliedQuantity'], 0)
        self.assertEqual(rows[0]['openQuantity'], 10)
        self.assertEqual(rows[0]['deliveryDate'], '20260203')
        self.assertEqual(rows[0]['buyingPrice'], 12.5)
        self.assertEqual(rows[0]['type'], 1)
        self.assertEqual(rows[0]['comment'].strip(), 'Handle with care')
        self.assertNotIn('activeDate', rows[0])

    def test_draft_cancelled_zero_and_uncoded_orders_are_not_exported(self):
        self._create_order()
        cancelled = self._create_order()
        cancelled.button_cancel()
        self._create_order(quantity=0).button_confirm()
        uncoded = self._create_order()
        uncoded.order_line.product_id = self.env['product.product'].create({
            'name': 'Uncoded purchased article',
        })
        uncoded.button_confirm()
        self.assertEqual(self.provider.export_interface(self.interface)['data'], [])

    def test_partially_received_order_still_exports_remaining_quantity(self):
        """Four received out of ten leaves six units still due from the vendor."""
        order = self._create_order()
        order.button_confirm()
        picking = order.picking_ids
        picking.move_ids.write({'quantity': 4, 'picked': True})
        picking._action_done()
        self.assertEqual(order.order_line.qty_received, 4)

        rows = self.provider.export_interface(self.interface)['data']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['suppliedQuantity'], 4)
        self.assertEqual(rows[0]['openQuantity'], 6)

    def test_fully_received_and_over_received_orders_are_not_exported(self):
        for received in [10, 12]:
            with self.subTest(received=received):
                order = self._create_order()
                order.button_confirm()
                picking = order.picking_ids
                picking.move_ids.write({'quantity': received, 'picked': True})
                picking._action_done()
                self.assertEqual(order.order_line.qty_received, received)
                self.assertEqual(
                    self.provider.export_interface(self.interface)['data'], [],
                )


@tagged('post_install', '-at_install', 'slim4_business')
class TestConfirmedDemandDate(TransactionCase):
    @freeze_time('2026-01-10 09:00:00')
    def test_commitment_date_takes_precedence_over_expected_date(self):
        customer = self.env['res.partner'].create({'name': 'Test demand customer'})
        product = self.env['product.product'].create({
            'name': 'Test demand article', 'default_code': 'S4-DEMAND',
        })
        warehouse = self.env['stock.warehouse'].create({
            'name': 'Test demand warehouse', 'code': 'S4DEM',
        })
        order = self.env['sale.order'].create({
            'partner_id': customer.id,
            'warehouse_id': warehouse.id,
            'date_order': '2026-01-10 09:00:00',
            'commitment_date': '2026-02-01 12:00:00',
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 1,
                'customer_lead': 5,
            })],
        })
        order.action_confirm()
        interface = self.env.ref(
            'slim4_connector_base.slim4_interface_confirmed_demand',
        )
        interface.source_domain = (
            f"{interface.source_domain} + [('id', '=', {order.order_line.id})]"
        )
        provider = get_export_provider(self.env, interface)
        rows = provider.export_interface(interface)['data']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['code'], 'S4-DEMAND')
        self.assertEqual(rows[0]['requiredDate'], '20260201')

        order.commitment_date = False
        rows = provider.export_interface(interface)['data']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['requiredDate'], '20260115')
