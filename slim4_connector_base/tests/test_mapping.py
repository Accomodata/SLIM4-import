from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'slim4_business')
class TestMappingConfiguration(TransactionCase):
    def test_reset_restores_shipped_values_and_preserves_custom_mapping(self):
        """Expected defaults come from the Article Filter XML configuration."""
        interface = self.env.ref('slim4_connector_base.slim4_interface_article_filter')
        code = self.env.ref(
            'slim4_connector_base.slim4_connector_base_article_filter_code',
        )
        warehouse = self.env.ref(
            'slim4_connector_base.slim4_connector_base_article_filter_warehouse',
        )
        custom = self.env['slim4.interface.mapping'].create({
            'interface_id': interface.id,
            'slim4_field': 'customerExtension',
            'mapping_type': 'constant',
            'constant_value': 'Keep this value',
            'status': 'validated',
        })
        code.write({
            'mapping_type': 'constant',
            'constant_value': 'Wrong reference',
            'field_path': False,
            'slim4_required': False,
            'status': 'ignored',
        })
        warehouse.write({'split_records': False, 'specific_rule': "result = 'OTHER'"})

        interface.action_reset_mapping_to_default()

        self.assertRecordValues(code, [{
            'mapping_type': 'field',
            'field_path': 'default_code',
            'constant_value': False,
            'slim4_required': True,
            'status': 'validated',
        }])
        self.assertRecordValues(warehouse, [{
            'mapping_type': 'rule',
            'field_path': 'warehouse_ids.code',
            'split_records': True,
            'specific_rule': False,
        }])
        self.assertEqual(custom.constant_value, 'Keep this value')
        self.assertEqual(custom.status, 'validated')

    def test_only_one_split_mapping_can_be_enabled_per_interface(self):
        interface = self.env['slim4.interface'].create({
            'name': 'Test split configuration',
            'technical_name': 'TestSplitConfiguration',
            'source_model_id': self.env['ir.model']._get_id('product.product'),
        })
        first, second = self.env['slim4.interface.mapping'].create([
            {
                'interface_id': interface.id,
                'slim4_field': 'warehouse',
                'field_path': 'warehouse_ids.code',
                'split_records': True,
            },
            {
                'interface_id': interface.id,
                'slim4_field': 'vendor',
                'field_path': 'seller_ids.partner_id.ref',
            },
        ])
        with self.assertRaisesRegex(
            ValidationError, 'Only one mapping can split',
        ), self.cr.savepoint():
            second.split_records = True

        first.split_records = False
        second.split_records = True
        self.assertEqual(interface.mapping_line_ids.filtered('split_records'), second)
