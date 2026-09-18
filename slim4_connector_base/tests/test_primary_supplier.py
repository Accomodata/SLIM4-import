from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'slim4_business')
class TestPrimarySupplier(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        attribute = cls.env['product.attribute'].create({
            'name': 'Test size',
            'value_ids': [
                Command.create({'name': 'Small'}),
                Command.create({'name': 'Large'}),
            ],
        })
        cls.template = cls.env['product.template'].create({
            'name': 'Test supplier selection',
            'attribute_line_ids': [Command.create({
                'attribute_id': attribute.id,
                'value_ids': [Command.set(attribute.value_ids.ids)],
            })],
        })
        cls.first, cls.second = cls.template.product_variant_ids.sorted('id')
        vendor = cls.env['res.partner'].create({'name': 'Test vendor'})
        cls.generic, cls.specific, cls.other_variant = (
            cls.env['product.supplierinfo'].create([
                {
                    'partner_id': vendor.id,
                    'product_tmpl_id': cls.template.id,
                    'sequence': 5,
                    'min_qty': 20,
                },
                {
                    'partner_id': vendor.id,
                    'product_tmpl_id': cls.template.id,
                    'product_id': cls.first.id,
                    'sequence': 5,
                    'min_qty': 2,
                },
                {
                    'partner_id': vendor.id,
                    'product_tmpl_id': cls.template.id,
                    'product_id': cls.second.id,
                    'sequence': 1,
                    'min_qty': 1,
                },
            ])
        )

    def test_only_generic_and_matching_variant_suppliers_are_eligible(self):
        self.assertCountEqual(
            self.first.slim4_matching_supplier_ids,
            self.generic | self.specific,
        )
        self.assertCountEqual(
            self.second.slim4_matching_supplier_ids,
            self.generic | self.other_variant,
        )
        # An eligible vendor is not primary until explicitly selected.
        self.assertFalse(self.first.slim4_primary_supplier_id)
        self.first.slim4_primary_supplier_ids = self.other_variant
        self.assertFalse(self.first.slim4_primary_supplier_id)

    def test_selection_uses_sequence_then_minimum_quantity(self):
        """The field help specifies sequence before the minimum quantity."""
        self.first.slim4_primary_supplier_ids = self.generic | self.specific
        self.assertEqual(self.first.slim4_primary_supplier_id, self.specific)
        self.assertTrue(self.specific.is_primary_supplier)

        self.generic.sequence = 1
        self.assertEqual(self.first.slim4_primary_supplier_id, self.generic)
        self.assertFalse(self.specific.is_primary_supplier)

        self.first.slim4_primary_supplier_ids = False
        self.assertFalse(self.first.slim4_primary_supplier_id)

    def test_reassigning_vendor_line_removes_stale_selection(self):
        self.first.slim4_primary_supplier_ids = self.generic | self.specific
        self.specific.product_id = self.second

        self.assertEqual(self.first.slim4_primary_supplier_ids, self.generic)
        self.assertEqual(self.first.slim4_primary_supplier_id, self.generic)
        self.assertNotIn(self.specific, self.first.slim4_matching_supplier_ids)
        self.assertIn(self.specific, self.second.slim4_matching_supplier_ids)
        self.assertFalse(self.second.slim4_primary_supplier_id)

    def test_single_variant_template_selection_updates_the_variant(self):
        product = self.env['product.product'].create({'name': 'Single variant'})
        seller = self.env['product.supplierinfo'].create({
            'partner_id': self.generic.partner_id.id,
            'product_tmpl_id': product.product_tmpl_id.id,
        })
        product.product_tmpl_id.slim4_primary_supplier_ids = seller
        self.assertEqual(product.slim4_primary_supplier_id, seller)
        self.assertTrue(seller.is_primary_supplier)

        product.product_tmpl_id.slim4_primary_supplier_ids = False
        self.assertFalse(product.slim4_primary_supplier_id)
        self.assertFalse(seller.is_primary_supplier)
