from odoo import _
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from ..helpers.provider_mapping import get_export_provider
from ..providers.slim4_export_provider import decode_cursor

API_PREFIX = '/slim4/api/v1'
DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class Slim4RequestError(ValueError):
    """Base error raised while validating an incoming Slim4 request."""

    code = 'invalid_request'
    status = 400


class InvalidPaginationError(Slim4RequestError):
    """Raised when API pagination parameters are invalid."""

    code = 'invalid_pagination'


class InvalidFilterError(Slim4RequestError):
    code = 'invalid_filter'
    status = 400


def parse_limit(limit=DEFAULT_LIMIT):
    """Validate and normalize the pagination limit."""
    if isinstance(limit, bool) or not isinstance(limit, (int, str)):
        raise InvalidPaginationError(_('limit must be an integer.'))
    try:
        parsed_limit = int(limit)
    except (TypeError, ValueError) as error:
        raise InvalidPaginationError(
            _('limit must be an integer.'),
        ) from error

    if not 1 <= parsed_limit <= MAX_LIMIT:
        raise InvalidPaginationError(
            _('limit must be between 1 and %s.') % MAX_LIMIT,
        )

    return parsed_limit


def parse_cursor(cursor=None):
    """Validate a keyset pagination cursor while preserving its encoded value."""
    if cursor is None:
        return None

    try:
        decode_cursor(cursor)
    except ValueError as error:
        raise InvalidPaginationError(str(error)) from error

    return cursor


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
    """Shared request/export flow for Slim4 interface controllers."""

    _interface_technical_name = None

    def _get_interface_config(self):
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

    def _prepare_collection_request(self, limit=DEFAULT_LIMIT, cursor=None):
        try:
            limit = parse_limit(limit)
            cursor = parse_cursor(cursor)
        except Slim4RequestError as error:
            return None, make_error_response(
                code=error.code,
                message=str(error),
                status=error.status,
            )

        interface = self._get_interface_config()
        if not interface:
            return None, make_error_response(
                code='interface_not_configured',
                message=(
                    f'The {self._interface_technical_name} interface is not '
                    'configured or is inactive.'
                ),
                status=404,
                context={'interface': self._interface_technical_name},
            )

        if errors := interface._get_mapping_config_errors():
            return None, make_error_response(
                code='invalid_mapping_configuration',
                message='The Slim4 mapping configuration is structurally invalid.',
                status=422,
                context={
                    'interface': interface.technical_name,
                    'errors': errors,
                },
            )

        return {
            'interface': interface,
            'limit': limit,
            'cursor': cursor,
        }, None

    def _export_collection(self, limit=DEFAULT_LIMIT, cursor=None):
        """Run the common export flow and return an HTTP JSON response."""
        try:
            request_data, error_response = self._prepare_collection_request(
                limit=limit,
                cursor=cursor,
            )
            if error_response:
                return error_response

            interface = request_data['interface']
            provider = get_export_provider(request.env, interface)
            rows = provider.export_interface(
                interface,
                limit=request_data['limit'],
                cursor=request_data['cursor'],
            )
            return request.make_json_response(rows)

        except AccessError:
            return make_error_response(
                code='access_denied',
                message='You do not have permission to export this Slim4 interface.',
                status=403,
                context={'interface': self._interface_technical_name},
            )
        except UserError as error:
            return make_error_response(
                code='export_error',
                message=str(error),
                status=422,
                context={'interface': self._interface_technical_name},
            )
        except Exception:
            return make_error_response(
                code='internal_error',
                message='An unexpected error occurred while exporting Slim4 data.',
                status=500,
                context={'interface': self._interface_technical_name},
            )
