from .errors import PayloadValidationError
from datetime import datetime


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
    if not isinstance(order, dict):
        raise PayloadValidationError(
            'Each order must be a JSON object.',
            context={'item_index': item_index},
        )

    if not order.get('articleCode') and order.get('code'):
        order = {
            **order,
            'articleCode': order['code'],
        }

    missing_fields = _get_missing_fields(order)

    if missing_fields:
        raise PayloadValidationError(
            f"Missing required order fields: {', '.join(missing_fields)}",
            context={
                'item_index': item_index,
                'missing_fields': missing_fields,
            },
        )

    to_order = order.get('toOrder')
    expected_date = order.get('expectedDate')

    try:
        quantity = float(to_order) if isinstance(to_order, str) else to_order
    except (TypeError, ValueError) as error:
        raise PayloadValidationError(
            'The "toOrder" value must be numeric.',
            context={'item_index': item_index},
        ) from error

    if isinstance(to_order, bool):
        raise PayloadValidationError(
            'The "toOrder value cannot be empty.',
            context={'item_index': item_index},
        )
    if isinstance(quantity, float) and quantity <= 0:
        raise PayloadValidationError(
            'The "toOrder" value must be strictly positive.',
            context={'item_index': item_index},
        )

    if expected_date:
        if not isinstance(expected_date, str):
            raise PayloadValidationError(
                'The "expectedDate" value must be a string in YYYYMMDD format.',
                context={'item_index': item_index},
            )

        try:
            order['expectedDate'] = datetime.strptime(
                expected_date,
                '%Y%m%d',
            ).date()
        except ValueError as error:
            raise PayloadValidationError(
                'The "expectedDate" value must be a valid date in YYYYMMDD format.',
                context={
                    'item_index': item_index,
                    'expected_date': expected_date,
                },
            ) from error

    return order


def _get_missing_fields(order):
    missing_fields = []
    if not order.get('supplierNumber'):
        missing_fields.append('supplierNumber')
    if not order.get('articleCode'):
        missing_fields.append('articleCode/code')
    if not order.get('toOrder'):
        missing_fields.append('toOrder')
    return missing_fields
