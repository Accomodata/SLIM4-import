from .errors import PayloadValidationError
from datetime import datetime
from math import isfinite
import re


def validate_order_payload(payload):
    """Validate and normalize the order payload."""
    if not isinstance(payload, dict):
        raise PayloadValidationError('The JSON body must be an object.')

    orders = payload.get('order')
    if orders is None or orders == []:
        raise PayloadValidationError('No orders found in the request.')
    if not isinstance(orders, list):
        raise PayloadValidationError('The "order" property must be a list.')

    return [
        _validate_order(order, item_index)
        for item_index, order in enumerate(orders)
    ]


def _validate_order(order, item_index):
    """Validate and normalize one inbound order."""
    if not isinstance(order, dict):
        raise PayloadValidationError(
            'Each order must be a JSON object.',
            context={'item_index': item_index},
        )

    normalized_order = dict(order)

    # Slim4 may send the article reference under either key.
    if not normalized_order.get('articleCode') and normalized_order.get('code'):
        normalized_order['articleCode'] = normalized_order['code']

    missing_fields = _get_missing_fields(normalized_order)
    if missing_fields:
        raise PayloadValidationError(
            f"Missing required order fields: {', '.join(missing_fields)}",
            context={
                'item_index': item_index,
                'missing_fields': missing_fields,
            },
        )

    normalized_order['toOrder'] = _normalize_quantity(
        normalized_order['toOrder'],
        item_index,
    )

    warehouse = normalized_order.get('warehouse')
    if warehouse is not None:
        if isinstance(warehouse, bool) or not isinstance(warehouse, (str, int)):
            raise PayloadValidationError(
                'The "warehouse" value must be a string or an integer.',
                context={'item_index': item_index},
            )
        normalized_order['warehouse'] = str(warehouse).strip()

    expected_date = normalized_order.get('expectedDate')
    if expected_date not in (None, ''):  # noqa: PLR6201 - JSON values may be unhashable.
        normalized_order['expectedDate'] = _normalize_expected_date(
            expected_date,
            item_index,
        )

    return normalized_order


def _normalize_quantity(value, item_index):
    """Return a strictly positive finite quantity."""
    if isinstance(value, bool):
        raise PayloadValidationError(
            'The "toOrder" value must be numeric.',
            context={'item_index': item_index},
        )

    try:
        quantity = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise PayloadValidationError(
            'The "toOrder" value must be numeric.',
            context={'item_index': item_index},
        ) from error

    if not isfinite(quantity) or quantity <= 0:
        raise PayloadValidationError(
            'The "toOrder" value must be a strictly positive finite number.',
            context={'item_index': item_index},
        )

    return quantity


def _normalize_expected_date(value, item_index):
    """Convert a Slim4 YYYYMMDD date to an Odoo-compatible ISO string."""
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{8}', value):
        raise PayloadValidationError(
            'The "expectedDate" value must be a string in YYYYMMDD format.',
            context={'item_index': item_index},
        )

    try:
        return datetime.strptime(value, '%Y%m%d').date().isoformat()
    except ValueError as error:
        raise PayloadValidationError(
            'The "expectedDate" value must be a valid date in YYYYMMDD format.',
            context={
                'item_index': item_index,
                'expected_date': value,
            },
        ) from error


def _get_missing_fields(order):
    missing_fields = []
    if not order.get('supplierNumber'):
        missing_fields.append('supplierNumber')
    if not order.get('articleCode'):
        missing_fields.append('articleCode/code')
    if not order.get('toOrder'):
        missing_fields.append('toOrder')
    return missing_fields
