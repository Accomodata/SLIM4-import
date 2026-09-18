from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from ..helpers.provider_mapping import get_export_provider


@tagged('post_install', '-at_install', 'slim4_business')
class TestSupplierExports(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        attribute = cls.env['product.attribute'].create({
            'name': 'Test supplier variant',
            'value_ids': [
                Command.create({'name': name}) for name in ['A', 'B', 'C', 'D']
            ],
        })
        cls.template = cls.env['product.template'].create({
            'name': 'Supplier export article',
            'attribute_line_ids': [Command.create({
                'attribute_id': attribute.id,
                'value_ids': [Command.set(attribute.value_ids.ids)],
            })],
        })
        cls.first, cls.second, archived, uncoded = (
            cls.template.product_variant_ids.sorted('id')
        )
        cls.first.default_code = 'S4-SUPPLIER-A'
        cls.second.default_code = 'S4-SUPPLIER-B'
        archived.write({'default_code': 'S4-SUPPLIER-C', 'active': False})
        uncoded.default_code = False
        cls.warehouses = cls.env['stock.warehouse'].create([
            {'name': 'Test supplier warehouse A', 'code': 'S4SA'},
            {'name': 'Test supplier warehouse B', 'code': 'S4SB'},
        ])
        cls.template.warehouse_ids = cls.warehouses
        vendor = cls.env['res.partner'].create({
            'name': 'Supplier export vendor', 'ref': 'S4-VENDOR',
        })
        cls.seller = cls.env['product.supplierinfo'].create({
            'partner_id': vendor.id,
            'product_tmpl_id': cls.template.id,
            'min_qty': 3,
            'price': 12.5,
            'currency_id': cls.env.company.currency_id.id,
            'product_uom_id': cls.template.uom_id.id,
        })
        cls.interface = cls.env.ref('slim4_connector_base.slim4_interface_suppliers')
        # Retain the shipped business domain, restricted to our own fixtures.
        cls.interface.source_domain = (
            f"{cls.interface.source_domain} + [('id', '=', {cls.seller.id})]"
        )
        cls.provider = get_export_provider(cls.env, cls.interface)

    def test_template_vendor_exports_active_coded_variants_per_warehouse(self):
        result = self.provider.export_interface(self.interface, page_size=1)
        self.assertCountEqual([
            (row['code'], row['supplierNumber'], row['warehouse'])
            for row in result['data']
        ], [
            ('S4-SUPPLIER-A', 'S4-VENDOR', 'S4SA'),
            ('S4-SUPPLIER-A', 'S4-VENDOR', 'S4SB'),
            ('S4-SUPPLIER-B', 'S4-VENDOR', 'S4SA'),
            ('S4-SUPPLIER-B', 'S4-VENDOR', 'S4SB'),
        ])
        # A page counts source vendor lines, not the expanded JSON rows.
        self.assertFalse(result['has_more'])
        self.assertIsNone(result['next_skiptoken'])

    def test_variant_vendor_is_not_repeated_for_other_variants(self):
        self.seller.product_id = self.first
        self.template.warehouse_ids = self.warehouses[0]
        result = self.provider.export_interface(self.interface)
        self.assertEqual([
            (row['code'], row['supplierNumber'], row['warehouse'])
            for row in result['data']
        ], [('S4-SUPPLIER-A', 'S4-VENDOR', 'S4SA')])
        self.first.active = False
        self.assertEqual(self.provider.export_interface(self.interface)['data'], [])

    def test_split_pagination_keeps_all_occurrences_of_each_source(self):
        variant_seller = self.seller.copy({'product_id': self.first.id})
        self.interface.source_domain = repr([
            ('id', 'in', (self.seller | variant_seller).ids),
        ])
        (self.seller | variant_seller).write({'write_date': '2026-01-02 10:00:00'})
        first_page = self.provider.export_interface(self.interface, page_size=1)
        self.assertEqual(len(first_page['data']), 4)
        self.assertTrue(first_page['has_more'])

        second_page = self.provider.export_interface(
            self.interface, page_size=1, skiptoken=first_page['next_skiptoken'],
        )
        self.assertCountEqual([
            (row['code'], row['supplierNumber'], row['warehouse'])
            for row in second_page['data']
        ], [
            ('S4-SUPPLIER-A', 'S4-VENDOR', 'S4SA'),
            ('S4-SUPPLIER-A', 'S4-VENDOR', 'S4SB'),
        ])
        self.assertFalse(second_page['has_more'])
        self.assertIsNone(second_page['next_skiptoken'])

    def test_empty_optional_split_produces_no_rows_and_required_split_fails(self):
        warehouse = self.interface.mapping_line_ids.filtered(
            lambda line: line.slim4_field == 'warehouse',
        )
        # A field mapping has no fallback: no warehouse means no occurrence.
        warehouse.write({'mapping_type': 'field', 'slim4_required': False})
        self.template.warehouse_ids = False
        self.assertEqual(self.provider.export_interface(self.interface)['data'], [])

        warehouse.slim4_required = True
        with self.assertRaisesRegex(
            UserError, 'Required Slim4 field "warehouse" is empty',
        ):
            self.provider.export_interface(self.interface)

    def test_shipped_supplier_mapping_exports_minimum_order_quantity(self):
        """Check the shipped Suppliers field, which is named minimumOrderQuantity."""
        self.seller.product_id = self.first
        self.template.warehouse_ids = self.warehouses[0]
        rows = self.provider.export_interface(self.interface)['data']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['code'], 'S4-SUPPLIER-A')
        self.assertEqual(rows[0]['minimumOrderQuantity'], 3)
        self.assertEqual(rows[0]['buyingPrice'], 12.5)

        self.seller.min_qty = 0
        rows = self.provider.export_interface(self.interface)['data']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['minimumOrderQuantity'], 0)

    def test_logistics_exports_selected_supplier_minimum_quantity(self):
        """Logistics uses the selected supplier and keeps the Slim4 MOQ name."""
        interface = self.env.ref('slim4_connector_base.slim4_interface_logistics')
        interface.source_domain = (
            f"{interface.source_domain} + [('id', '=', {self.first.id})]"
        )
        self.first.slim4_primary_supplier_ids = self.seller
        self.template.warehouse_ids = self.warehouses[0]
        provider = get_export_provider(self.env, interface)

        rows = provider.export_interface(interface)['data']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['code'], 'S4-SUPPLIER-A')
        self.assertEqual(rows[0]['MOQ'], 3)
        self.assertEqual(rows[0]['buyingPrice'], 12.5)

        self.seller.min_qty = 0
        self.assertEqual(provider.export_interface(interface)['data'][0]['MOQ'], 0)
