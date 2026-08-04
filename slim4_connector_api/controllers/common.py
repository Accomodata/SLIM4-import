from odoo.exceptions import AccessError, UserError
from odoo.http import request

from ..helpers.provider_mapping import get_export_provider

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

    def _prepare_collection_request(self, limit=DEFAULT_LIMIT, offset=0):
        try:
            limit, offset = parse_pagination(limit, offset)
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
            'offset': offset,
        }, None

    def _export_collection(self, limit=DEFAULT_LIMIT, offset=0):
        """Run the common export flow and return an HTTP JSON response."""
        try:
            request_data, error_response = self._prepare_collection_request(
                limit=limit,
                offset=offset,
            )
            if error_response:
                return error_response

            interface = request_data['interface']
            provider = get_export_provider(request.env, interface)
            rows = provider.export_interface(
                interface,
                limit=request_data['limit'],
                offset=request_data['offset'],
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
