import json

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'slim4_business')
class TestExport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.products = cls.env['product.product'].create([
            {'name': 'First article', 'default_code': 'S4-EXPORT-A'},
            {'name': 'Second article', 'default_code': 'S4-EXPORT-B'},
            {
                'name': 'Archived article',
                'default_code': 'S4-EXPORT-C',
                'active': False,
            },
            {'name': 'Article without reference'},
        ])
        cls.interface = cls.env['slim4.interface'].create({
            'name': 'Test article export',
            'technical_name': 'TestArticleExport',
            'source_model_id': cls.env['ir.model']._get_id('product.product'),
            'source_domain': repr([
                ('id', 'in', cls.products.ids),
                ('default_code', '!=', False),
                ('active', '=', True),
            ]),
        })
        cls.code = cls.env['slim4.interface.mapping'].create({
            'interface_id': cls.interface.id,
            'slim4_field': 'code',
            'mapping_type': 'field',
            'field_path': 'default_code',
            'field_type': 'char',
            'slim4_required': True,
            'status': 'validated',
        })
        cls.provider = cls.env['slim4.export.provider']
        cls.user = new_test_user(
            cls.env, login='slim4_export_user', groups='stock.group_stock_user',
            context={'no_reset_password': True},
        )

    def test_source_filter_and_keyset_pages_do_not_lose_equal_timestamp_records(self):
        # Equal write dates exercise the ID tie-breaker, independently of timing.
        self.products.write({'write_date': '2026-01-02 10:00:00'})
        first = self.provider.export_interface(self.interface, page_size=1)
        self.assertEqual(first['data'], [{'code': 'S4-EXPORT-A'}])
        self.assertTrue(first['has_more'])
        self.assertTrue(first['next_skiptoken'])

        second = self.provider.export_interface(
            self.interface, page_size=1, skiptoken=first['next_skiptoken'],
        )
        self.assertEqual(second, {
            'data': [{'code': 'S4-EXPORT-B'}],
            'has_more': False,
            'next_skiptoken': None,
        })
        offset_page = self.provider.export_interface(
            self.interface, page_size=1, offset=1,
        )
        self.assertEqual(offset_page, second)
        self.assertEqual(
            self.provider.export_interface(self.interface, offset=2),
            {'data': [], 'has_more': False, 'next_skiptoken': None},
        )

    def test_record_preview_keeps_source_filters(self):
        self.interface._create_json_preview(
            page_size=20, record=self.products[1].id,
        )
        result = json.loads(self.interface.mapping_preview_json)
        self.assertEqual(result['data'], [{'code': 'S4-EXPORT-B'}])
        for excluded in self.products[2:]:
            with self.subTest(product=excluded.name), self.assertRaisesRegex(
                UserError, 'No data found',
            ):
                self.interface._create_json_preview(page_size=20, record=excluded.id)

    def test_only_validated_authorized_mappings_are_exported(self):
        group = self.env['res.groups'].create({'name': 'Test restricted export'})
        self.env['slim4.interface.mapping'].create([
            {
                'interface_id': self.interface.id,
                'slim4_field': field,
                'mapping_type': 'constant',
                'constant_value': 'Restricted value',
                'status': status,
                'group_id': group_id,
            }
            for field, status, group_id in [
                ('restricted', 'validated', group.id),
                ('pending', 'to_validate', False),
                ('ignored', 'ignored', False),
            ]
        ])
        provider = self.provider.with_user(self.user)
        interface = self.interface.with_user(self.user)
        self.assertEqual(provider.export_interface(interface)['data'], [
            {'code': 'S4-EXPORT-A'}, {'code': 'S4-EXPORT-B'},
        ])

        self.user.group_ids += group
        self.assertEqual(provider.export_interface(interface)['data'], [
            {'code': 'S4-EXPORT-A', 'restricted': 'Restricted value'},
            {'code': 'S4-EXPORT-B', 'restricted': 'Restricted value'},
        ])

    def test_implied_group_also_authorizes_its_mapping(self):
        """Odoo grants access through implied groups as well as direct groups."""
        group = self.env['res.groups'].create({'name': 'Test export feature'})
        parent = self.env['res.groups'].create({
            'name': 'Test export role',
            'implied_ids': [Command.link(group.id)],
        })
        self.user.group_ids += parent
        self.env['slim4.interface.mapping'].create({
            'interface_id': self.interface.id,
            'slim4_field': 'feature',
            'mapping_type': 'constant',
            'constant_value': 'Enabled',
            'status': 'validated',
            'group_id': group.id,
        })
        result = self.provider.with_user(self.user).export_interface(
            self.interface.with_user(self.user), page_size=1,
        )
        self.assertEqual(result['data'], [
            {'code': 'S4-EXPORT-A', 'feature': 'Enabled'},
        ])

    def test_source_records_respect_user_company_access(self):
        other_company = self.env['res.company'].create({'name': 'Other export company'})
        self.products[1].company_id = other_company
        self.user.write({
            'company_id': self.env.company.id,
            'company_ids': [Command.set(self.env.company.ids)],
        })
        result = self.provider.with_user(self.user).with_context(
            allowed_company_ids=self.env.company.ids,
        ).export_interface(self.interface.with_user(self.user))
        self.assertEqual(result['data'], [{'code': 'S4-EXPORT-A'}])

    def test_required_values_reject_empty_but_accept_numeric_zero(self):
        self.code.write({
            'mapping_type': 'constant', 'constant_value': '0', 'field_type': 'integer',
        })
        self.assertEqual(
            self.provider.export_interface(self.interface, page_size=1)['data'],
            [{'code': 0}],
        )
        self.code.constant_value = False
        with self.assertRaisesRegex(UserError, '"code"'):
            self.provider.export_interface(self.interface)

    def test_warehouse_rule_prefers_assignment_then_accessible_fallback(self):
        warehouses = self.env['stock.warehouse'].create([
            {'name': 'Export fallback A', 'code': 'S4FA'},
            {'name': 'Export fallback B', 'code': 'S4FB'},
        ])
        self.env['ir.rule'].create({
            'name': 'Test export warehouse visibility',
            'model_id': self.env['ir.model']._get_id('stock.warehouse'),
            'domain_force': repr([('id', 'in', warehouses.ids)]),
        })
        self.env['slim4.interface.mapping'].create({
            'interface_id': self.interface.id,
            'slim4_field': 'warehouse',
            'mapping_type': 'rule',
            'field_path': 'warehouse_ids.code',
            'field_type': 'char',
            'split_records': True,
            'slim4_required': True,
            'status': 'validated',
        })
        self.products[0].warehouse_ids = warehouses[0]
        provider = self.provider.with_user(self.user)
        interface = self.interface.with_user(self.user)
        self.assertCountEqual(provider.export_interface(interface)['data'], [
            {'code': 'S4-EXPORT-A', 'warehouse': 'S4FA'},
            {'code': 'S4-EXPORT-B', 'warehouse': 'S4FA'},
            {'code': 'S4-EXPORT-B', 'warehouse': 'S4FB'},
        ])

    def test_specific_rule_result_is_normalized_and_missing_result_is_reported(self):
        self.code.write({
            'mapping_type': 'rule',
            'specific_rule': "result = record.default_code + '-CUSTOM'",
            'max_length': 14,
        })
        self.assertEqual(
            self.provider.export_interface(self.interface, page_size=1)['data'],
            [{'code': 'S4-EXPORT-A-CU'}],
        )
        self.code.specific_rule = 'unused = 1'
        with self.assertRaisesRegex(UserError, 'must assign a value to "result"'):
            self.provider.export_interface(self.interface)
