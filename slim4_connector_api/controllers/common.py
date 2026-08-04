from datetime import date

from odoo.http import request


API_PREFIX = '/slim4/api/v1'

DEFAULT_LIMIT = 200
MAX_LIMIT = 1000


class Slim4RequestError(ValueError):
    """Base error raised while validating an incoming Slim4 request."""

    code = 'invalid_request'
    status = 400


class InvalidPaginationError(Slim4RequestError):
    """Raised when API pagination parameters are invalid."""

    code = 'invalid_pagination'


class InvalidDateError(Slim4RequestError):
    """Raised when an API date parameter is invalid."""

    code = 'invalid_date'


def parse_pagination(limit=DEFAULT_LIMIT, offset=0):
    """Validate and normalize collection pagination parameters."""
    try:
        limit = int(limit)
        offset = int(offset)
    except (TypeError, ValueError) as error:
        raise InvalidPaginationError(
            'limit and offset must be integers.',
        ) from error

    if not 1 <= limit <= MAX_LIMIT:
        raise InvalidPaginationError(
            f'limit must be between 1 and {MAX_LIMIT}.',
        )

    if offset < 0:
        raise InvalidPaginationError(
            'offset must be greater than or equal to 0.',
        )

    return limit, offset


def parse_iso_date(value, parameter_name):
    """Validate an optional ISO date parameter."""
    if not value:
        return None

    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise InvalidDateError(
            f'{parameter_name} must use the YYYY-MM-DD format.',
        ) from error


def make_error_response(code, message, status=400, context=None):
    """Create a consistent JSON error response."""
    error_payload = {
        'code': code,
        'message': message,
    }
    if context:
        error_payload['context'] = context

    return request.make_json_response(
        {'error': error_payload},
        status=status,
    )


class Slim4ControllerMixin:
    """Shared helpers for Slim4 HTTP interface controllers.

    Each concrete controller only needs to define
    ``_interface_technical_name`` and its route.
    """

    _interface_technical_name = None

    def _get_interface_config(self):
        """Return the active configuration of the current interface."""
        if not self._interface_technical_name:
            raise ValueError(
                'A Slim4 controller must define _interface_technical_name.',
            )

        return request.env['slim4.interface'].search(
            [
                ('technical_name', '=', self._interface_technical_name),
                ('active', '=', True),
            ],
            limit=1,
        )

    def _make_interface_not_configured_response(self):
        return make_error_response(
            code='interface_not_configured',
            message=(
                f'The {self._interface_technical_name} interface is not '
                'configured or is inactive.'
            ),
            status=404,
            context={
                'interface': self._interface_technical_name,
            },
        )

    def _make_invalid_mapping_response(self, interface_config, errors):
        return make_error_response(
            code='invalid_mapping_configuration',
            message='The Slim4 mapping configuration is structurally invalid.',
            status=422,
            context={
                'interface': interface_config.technical_name,
                'errors': errors,
            },
        )

    def _make_not_implemented_response(self, interface_config):
        return make_error_response(
            code='interface_not_implemented',
            message=(
                f'The {interface_config.name} endpoint is available, but its '
                'record retrieval and mapping logic have not been implemented '
                'yet.'
            ),
            status=501,
            context={
                'interface': interface_config.technical_name,
            },
        )

    def _prepare_collection_request(
        self,
        *,
        limit=DEFAULT_LIMIT,
        offset=0,
        date_from=None,
    ):
        """Validate common parameters and load the interface configuration.

        :return: ``(request_data, error_response)``. ``request_data`` contains
            the interface record and normalized parameters. When validation
            fails, ``request_data`` is ``None`` and ``error_response`` is an
            Odoo HTTP response ready to return.
        """
        try:
            limit, offset = parse_pagination(limit, offset)
            date_from = parse_iso_date(date_from, 'date_from')
        except Slim4RequestError as error:
            return None, make_error_response(
                code=error.code,
                message=str(error),
                status=error.status,
            )

        interface_config = self._get_interface_config()
        if not interface_config:
            return None, self._make_interface_not_configured_response()

        if config_errors := interface_config._get_config_errors():
            return None, self._make_invalid_mapping_response(
                interface_config,
                config_errors,
            )

        return {
            'interface_config': interface_config,
            'limit': limit,
            'offset': offset,
            'date_from': date_from,
        }, None
