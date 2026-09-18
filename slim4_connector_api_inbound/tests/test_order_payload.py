from copy import deepcopy

from odoo.tests import tagged
from odoo.tests.common import BaseCase

from ..services.errors import PayloadValidationError
from ..services.order_payload_validator import validate_order_payload


@tagged('post_install', '-at_install', 'slim4_business')
class TestOrderPayload(BaseCase):
    def test_alias_quantity_and_leap_day_are_normalized_without_mutating_input(self):
        payload = {'order': [{
            'code': 'S4-ARTICLE',
            'supplierNumber': 'S4-VENDOR',
            'toOrder': '2.5',
            'expectedDate': '20280229',
            'warehouse': 'S4WH',
        }]}
        original = deepcopy(payload)
        self.assertEqual(validate_order_payload(payload), [{
            'code': 'S4-ARTICLE',
            'articleCode': 'S4-ARTICLE',
            'supplierNumber': 'S4-VENDOR',
            'toOrder': 2.5,
            'expectedDate': '2028-02-29',
            'warehouse': 'S4WH',
        }])
        self.assertEqual(payload, original)

    def test_canonical_article_code_without_optional_fields(self):
        orders = validate_order_payload({'order': [{
            'articleCode': 'CANONICAL',
            'supplierNumber': 'VENDOR', 'toOrder': 1,
        }]})
        self.assertEqual(orders[0]['articleCode'], 'CANONICAL')
        self.assertNotIn('expectedDate', orders[0])

    def test_invalid_envelopes_and_missing_fields_are_rejected(self):
        for payload in [None, [], 'orders', {}, {'order': []}, {'order': {}}]:
            with self.subTest(payload=payload), self.assertRaises(
                PayloadValidationError,
            ):
                validate_order_payload(payload)

        with self.assertRaises(PayloadValidationError) as caught:
            validate_order_payload({'order': [{}]})
        self.assertEqual(caught.exception.context['item_index'], 0)
        self.assertCountEqual(
            caught.exception.context['missing_fields'],
            ['supplierNumber', 'articleCode/code', 'toOrder'],
        )

    def test_non_positive_non_finite_and_non_numeric_quantities_are_rejected(self):
        for quantity in [0, -1, True, False, 'NaN', 'inf', '-inf', 'invalid', [], {}]:
            with self.subTest(quantity=quantity):
                with self.assertRaises(PayloadValidationError) as caught:
                    validate_order_payload({'order': [{
                        'articleCode': 'ARTICLE', 'supplierNumber': 'VENDOR',
                        'toOrder': quantity,
                    }]})
                self.assertEqual(caught.exception.context['item_index'], 0)

    def test_error_identifies_the_failing_item_in_a_batch(self):
        for invalid_order in [None, {'articleCode': 'ARTICLE', 'toOrder': 2}]:
            with self.subTest(order=invalid_order):
                with self.assertRaises(PayloadValidationError) as caught:
                    validate_order_payload({'order': [
                        {
                            'articleCode': 'ARTICLE', 'supplierNumber': 'VENDOR',
                            'toOrder': 1,
                        },
                        invalid_order,
                    ]})
                self.assertEqual(caught.exception.context['item_index'], 1)

    def test_expected_date_must_be_a_valid_eight_digit_calendar_date(self):
        """The documented input format is YYYYMMDD, including leading zeroes."""
        for date in [
            '20260229', '20261301', '2026-01-01', '2026111', '202601011',
            '202611 1', '2026010a', 20260101, False, [], {},
        ]:
            with self.subTest(date=date), self.assertRaises(PayloadValidationError):
                validate_order_payload({'order': [{
                    'articleCode': 'ARTICLE', 'supplierNumber': 'VENDOR',
                    'toOrder': 1, 'expectedDate': date,
                }]})

    def test_empty_expected_date_is_optional(self):
        for date in [None, '']:
            with self.subTest(date=date):
                self.assertEqual(validate_order_payload({'order': [{
                    'articleCode': 'ARTICLE', 'supplierNumber': 'VENDOR',
                    'toOrder': 1, 'expectedDate': date,
                }]}), [{
                    'articleCode': 'ARTICLE', 'supplierNumber': 'VENDOR',
                    'toOrder': 1.0, 'expectedDate': date,
                }])
