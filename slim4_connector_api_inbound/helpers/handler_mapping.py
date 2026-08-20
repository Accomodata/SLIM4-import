from ..services.errors import UnknownOperationError

HANDLER_BY_OPERATION = {
    'orders': 'slim4.inbound.handler.orders',
}


def get_inbound_handler(env, operation):
    """Return the handler registered for an inbound Slim4 operation."""
    handler_name = HANDLER_BY_OPERATION.get(operation)
    if not handler_name:
        raise UnknownOperationError(
            f'The Slim4 operation "{operation}" is not supported.',
            context={'operation': operation},
        )
    return env[handler_name]
