from datetime import datetime

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged

from ..services.errors import PayloadValidationError


@tagged('post_install', '-at_install', 'slim4_business')
class TestInboundOrders(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product, cls.second_product = cls.env['product.product'].create([
            {'name': 'First inbound article', 'default_code': 'S4-IN-A'},
            {'name': 'Second inbound article', 'default_code': 'S4-IN-B'},
        ])
        cls.vendor, cls.second_vendor = cls.env['res.partner'].create([
            {'name': 'First inbound vendor', 'ref': 'S4-IN-V1', 'supplier_rank': 1},
            {'name': 'Second inbound vendor', 'ref': 'S4-IN-V2', 'supplier_rank': 1},
        ])
        cls.warehouse, cls.second_warehouse = cls.env['stock.warehouse'].create([
            {'name': 'First inbound warehouse', 'code': 'S4I1'},
            {'name': 'Second inbound warehouse', 'code': 'S4I2'},
        ])
        cls.api_user = new_test_user(
            cls.env,
            login='slim4_inbound_user',
            groups=(
                'stock.group_stock_user,'
                'slim4_connector_api_inbound.group_slim4_inbound_api_user'
            ),
            context={'no_reset_password': True},
            company_id=cls.env.company.id,
            company_ids=[Command.set(cls.env.company.ids)],
        )
        cls.handler = cls.env['slim4.inbound.handler.orders']
        cls.messages = cls.env['slim4.inbound.message']
        cls.order = {
            'articleCode': 'S4-IN-A',
            'supplierNumber': 'S4-IN-V1',
            'warehouse': 'S4I1',
            'toOrder': 2.5,
            'expectedDate': '20261005',
        }

    def _receive(self, orders):
        """Exercise the same entry point and user rights as inbound staging."""
        before = self.messages.search([])
        self.handler.with_user(self.api_user).handle_payload({'order': orders})
        return (self.messages.search([]) - before).sorted('item_index')

    def test_receive_resolves_references_and_stages_without_creating_a_purchase(self):
        purchases = self.env['purchase.order'].search([])
        messages = self._receive([
            self.order,
            dict(self.order, articleCode='S4-IN-B', toOrder='3'),
        ])
        self.assertRecordValues(messages, [
            {
                'item_index': 0, 'product_id': self.product.id,
                'supplier_id': self.vendor.id, 'status': 'received',
                'picking_type_id': self.warehouse.in_type_id.id,
                'company_id': self.env.company.id,
            },
            {
                'item_index': 1, 'product_id': self.second_product.id,
                'supplier_id': self.vendor.id, 'status': 'received',
                'picking_type_id': self.warehouse.in_type_id.id,
                'company_id': self.env.company.id,
            },
        ])
        self.assertEqual(len(set(messages.mapped('batch_reference'))), 1)
        self.assertTrue(messages[0].batch_reference)
        self.assertEqual(messages[0].payload['expectedDate'], '2026-10-05')
        self.assertEqual(messages[1].payload['toOrder'], 3.0)
        self.assertEqual(self.env['purchase.order'].search([]), purchases)

    def test_invalid_batch_does_not_stage_the_valid_prefix(self):
        before = self.messages.search([])
        # Odoo's assertRaises rolls back writes and would hide partial staging.
        try:
            self._receive([self.order, dict(self.order, toOrder=-1)])
        except PayloadValidationError:
            pass
        else:
            self.fail('An invalid batch must be rejected before staging any item.')
        self.assertEqual(self.messages.search([]), before)

    def test_unknown_or_archived_references_do_not_block_valid_items(self):
        self.second_product.active = False
        messages = self._receive([
            self.order,
            dict(self.order, articleCode='MISSING', supplierNumber='UNKNOWN'),
            dict(self.order, articleCode='S4-IN-B'),
        ])
        self.assertEqual(messages.mapped('status'), ['received', 'error', 'error'])
        self.assertFalse(messages[1].product_id)
        self.assertFalse(messages[1].supplier_id)
        self.assertIn('MISSING', messages[1].error_message)
        self.assertIn('UNKNOWN', messages[1].error_message)
        self.assertFalse(messages[2].product_id)

    def test_duplicate_vendor_reference_is_not_silently_used_for_a_purchase(self):
        self.vendor.company_id = self.env.company
        self.env['res.partner'].create({
            'name': 'Duplicate vendor', 'ref': 'S4-IN-V1', 'supplier_rank': 1,
            'company_id': self.env.company.id,
        })
        message = self._receive([self.order])
        self.assertEqual(message.status, 'error')
        self.assertIn('ambiguous', message.error_message)
        purchases = self.env['purchase.order'].search([])
        self.assertEqual(self.handler.process_received_messages(), 0)
        self.assertEqual(self.env['purchase.order'].search([]), purchases)

    def test_references_are_resolved_in_message_company(self):
        other_company = self.env['res.company'].create({
            'name': 'Other vendor company',
        })
        self.vendor.company_id = self.env.company
        self.product.company_id = self.env.company
        self.second_product.company_id = other_company
        self.env['res.partner'].create([
            {
                'name': 'Other company same reference', 'ref': 'S4-IN-V1',
                'supplier_rank': 1, 'company_id': other_company.id,
            },
            {
                'name': 'Other company only vendor', 'ref': 'S4-IN-FOREIGN',
                'supplier_rank': 1, 'company_id': other_company.id,
            },
        ])
        self.api_user.company_ids += other_company
        self.handler = self.handler.with_context(
            allowed_company_ids=[self.env.company.id, other_company.id],
        )

        messages = self._receive([
            self.order,
            dict(self.order, supplierNumber='S4-IN-FOREIGN'),
            dict(self.order, articleCode='S4-IN-B'),
        ])
        self.assertEqual(messages.mapped('status'), ['received', 'error', 'error'])
        self.assertEqual(messages[0].supplier_id, self.vendor)
        self.assertFalse(messages[1].supplier_id)
        self.assertFalse(messages[2].product_id)
        self.assertEqual(messages.company_id, self.env.company)

    def test_warehouse_resolution_uses_current_company_and_first_incoming_type(self):
        other_company = self.env['res.company'].create({
            'name': 'Other inbound company',
        })
        self.env['stock.warehouse'].create({
            'name': 'Same code in another company',
            'code': 'S4I1',
            'company_id': other_company.id,
        })
        preferred = self.warehouse.in_type_id.copy({
            'name': 'Preferred inbound receipt',
            'sequence': self.warehouse.in_type_id.sequence - 1,
        })
        self.warehouse.out_type_id.sequence = preferred.sequence - 1
        self.api_user.company_ids += other_company
        handler = self.handler.with_user(self.api_user).with_context(
            allowed_company_ids=[self.env.company.id, other_company.id],
        )
        handler.handle_payload({'order': [self.order]})
        message = self.messages.search([('supplier_id', '=', self.vendor.id)])
        self.assertEqual(message.picking_type_id, preferred)
        self.assertEqual(message.company_id, self.env.company)

    def test_processing_groups_by_batch_vendor_and_receipt_type_and_is_repeatable(self):
        first_date = datetime(2026, 10, 5)
        second_date = datetime(2026, 10, 7)
        first_batch = self._receive([
            self.order,
            dict(self.order, articleCode='S4-IN-B', toOrder=4, expectedDate='20261007'),
            dict(self.order, supplierNumber='S4-IN-V2', toOrder=7),
            dict(self.order, warehouse='S4I2', toOrder=9),
        ])
        second_batch = self._receive([dict(self.order, toOrder=11)])
        before = self.env['purchase.order'].search([])

        self.assertEqual(self.handler.process_received_messages(), 5)
        purchases = self.env['purchase.order'].search([]) - before
        self.assertEqual(len(purchases), 4)
        self.assertEqual(set(purchases.mapped('state')), {'draft'})
        self.assertEqual(purchases.company_id, self.env.company)
        self.assertEqual(purchases.currency_id, self.env.company.currency_id)
        self.assertEqual(purchases.order_line.product_uom_id, self.product.uom_id)
        self.assertCountEqual([
            (
                purchase.partner_id.id,
                purchase.picking_type_id.id,
                tuple(sorted(
                    (line.product_id.id, line.product_qty, line.date_planned)
                    for line in purchase.order_line
                )),
            )
            for purchase in purchases
        ], [
            (self.vendor.id, self.warehouse.in_type_id.id, (
                (self.product.id, 2.5, first_date),
                (self.second_product.id, 4, second_date),
            )),
            (self.second_vendor.id, self.warehouse.in_type_id.id, (
                (self.product.id, 7, first_date),
            )),
            (self.vendor.id, self.second_warehouse.in_type_id.id, (
                (self.product.id, 9, first_date),
            )),
            (self.vendor.id, self.warehouse.in_type_id.id, (
                (self.product.id, 11, first_date),
            )),
        ])
        self.assertEqual(
            set((first_batch | second_batch).mapped('status')), {'processed'},
        )
        self.assertTrue(all((first_batch | second_batch).mapped('processed_at')))

        self.assertEqual(self.handler.process_received_messages(), 0)
        self.assertEqual(self.env['purchase.order'].search([]) - before, purchases)

    @freeze_time('2026-01-10 09:00:00')
    def test_missing_or_empty_expected_date_uses_odoo_purchase_defaults(self):
        self.env['product.supplierinfo'].create({
            'partner_id': self.vendor.id,
            'product_id': self.product.id,
            'delay': 4,
            'price': 12.5,
            'currency_id': self.env.company.currency_id.id,
            'product_uom_id': self.product.uom_id.id,
        })
        # The contract delegates planning to Odoo, not to a connector date formula.
        native_order = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'picking_type_id': self.warehouse.in_type_id.id,
            'order_line': [Command.create({
                'product_id': self.product.id, 'product_qty': 2.5,
            })],
        })
        self.assertTrue(native_order.order_line.date_planned)
        for optional_date in [{}, {'expectedDate': None}, {'expectedDate': ''}]:
            with self.subTest(optional_date=optional_date), self.cr.savepoint():
                payload: dict[str, str | float | None] = dict(self.order)
                payload.pop('expectedDate')
                payload.update(optional_date)
                message = self._receive([payload])
                before = self.env['purchase.order'].search([])

                self.assertEqual(self.handler.process_received_messages(), 1)
                purchase = self.env['purchase.order'].search([]) - before
                self.assertEqual(len(purchase), 1)
                self.assertEqual(
                    purchase.order_line.date_planned,
                    native_order.order_line.date_planned,
                )
                self.assertEqual(message.status, 'processed')

    def test_processing_limit_counts_groups_and_skips_unresolved_messages(self):
        messages = self._receive([
            self.order,
            dict(self.order, articleCode='S4-IN-B'),
            dict(self.order, supplierNumber='S4-IN-V2'),
            dict(self.order, articleCode='MISSING'),
            dict(self.order, supplierNumber='MISSING'),
        ])
        # A received message still needs both resolved references before processing.
        messages[3:].status = 'received'
        processed_count = self.handler.process_received_messages(limit=1)
        # Group order is not part of the contract.
        self.assertIn(processed_count, [1, 2])
        processed = messages.filtered(lambda message: message.status == 'processed')
        self.assertEqual(len(processed.supplier_id), 1)
        same_vendor = messages[:3].filtered(
            lambda message: message.supplier_id == processed.supplier_id,
        )
        self.assertCountEqual(processed, same_vendor)
        self.assertEqual(self.handler.process_received_messages(), 3 - processed_count)
        self.assertEqual(messages[3:].mapped('status'), ['received', 'received'])
        self.assertFalse(any(messages[3:].mapped('processed_at')))

    def test_api_user_can_stage_but_cannot_modify_delete_or_process_messages(self):
        message = self._receive([self.order]).with_user(self.api_user)
        with self.assertRaises(AccessError):
            message.write({'status': 'processed'})
        with self.assertRaises(AccessError):
            message.unlink()
        with self.assertRaises(AccessError):
            self.handler.with_user(self.api_user).process_received_messages()
        self.assertEqual(message.status, 'received')

    def test_user_without_inbound_permission_cannot_stage_messages(self):
        user = new_test_user(
            self.env, login='slim4_stock_only_user', groups='stock.group_stock_user',
            context={'no_reset_password': True},
        )
        before = self.messages.search([])
        with self.assertRaises(AccessError):
            self.handler.with_user(user).handle_payload({'order': [self.order]})
        self.assertEqual(self.messages.search([]), before)

    def test_inbound_messages_are_only_visible_in_allowed_companies(self):
        message = self._receive([self.order])
        other_company = self.env['res.company'].create({
            'name': 'Hidden inbound company',
        })
        hidden = message.copy({
            'company_id': other_company.id,
            'batch_reference': 'other-company-batch',
            'payload': dict(message.payload),
        })
        visible = self.messages.with_user(self.api_user).search([
            ('id', 'in', (message | hidden).ids),
        ])
        self.assertEqual(visible, message)
        with self.assertRaises(AccessError):
            hidden.with_user(self.api_user).read(['payload'])
