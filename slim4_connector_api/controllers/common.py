import logging
from urllib.parse import urlencode

from odoo import _
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from ..helpers.provider_mapping import get_export_provider
from ..providers.slim4_export_provider import decode_skiptoken

API_PREFIX = '/slim4/api/v1'
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 1000


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


def _parse_integer(value, parameter_name):
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise InvalidPaginationError(
            _('%s must be an integer.') % parameter_name,
        ) from error


def parse_page_size(page=DEFAULT_PAGE_SIZE):
    """Validate and normalize the public page parameter."""
    page_size = _parse_integer(page, 'page')

    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise InvalidPaginationError(
            _('page must be between 1 and %s.') % MAX_PAGE_SIZE,
        )

    return page_size


def parse_offset(skip=None):
    """Validate and normalize the public $skip parameter."""
    if skip is None:
        return 0

    offset = _parse_integer(skip, '$skip')
    if offset < 0:
        raise InvalidPaginationError(
            _('$skip must be greater than or equal to 0.'),
        )

    return offset


def parse_skiptoken(skiptoken=None):
    """Validate a keyset token while preserving its encoded value."""
    if skiptoken is None:
        return None

    try:
        decode_skiptoken(skiptoken)
    except ValueError as error:
        raise InvalidPaginationError(str(error)) from error

    return skiptoken


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

    def _export_collection(
        self,
        page=DEFAULT_PAGE_SIZE,
        skip=None,
        skiptoken=None,
        **params,
    ):
        """Run the common export flow and return an HTTP JSON response."""
        try:
            return self._process_collection_request(
                page=page,
                skip=skip,
                skiptoken=skiptoken,
                **params,
            )
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
        except Exception as error:
            logging.exception(error)
            return make_error_response(
                code='internal_error',
                message='An unexpected error occurred while exporting Slim4 data.',
                status=500,
                context={'interface': self._interface_technical_name},
            )

    def _prepare_collection_request(
        self,
        page=DEFAULT_PAGE_SIZE,
        skip=None,
        skiptoken=None,
        **params,
    ):
        try:
            if skip is not None and skiptoken is not None:
                raise InvalidPaginationError(
                    _('$skip and $skiptoken cannot be used together.'),
                )

            page_size = parse_page_size(page)
            offset = parse_offset(skip)
            skiptoken = parse_skiptoken(skiptoken)
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
            'page_size': page_size,
            'offset': offset,
            'skiptoken': skiptoken,
            'params': params,
        }, None

    def _process_collection_request(
        self,
        page=DEFAULT_PAGE_SIZE,
        skip=None,
        skiptoken=None,
        **params,
    ):
        request_data, error_response = self._prepare_collection_request(
            page=page,
            skip=skip,
            skiptoken=skiptoken,
            **params,
        )
        if error_response:
            return error_response

        interface = request_data['interface']
        provider = get_export_provider(request.env, interface)
        export_result = provider.export_interface(
            interface,
            page_size=request_data['page_size'],
            offset=request_data['offset'],
            skiptoken=request_data['skiptoken'],
            **request_data['params'],
        )

        response_payload = {'data': export_result['data']}

        if export_result['has_more']:
            response_payload['@odata.nextLink'] = self._build_next_link(
                page_size=request_data['page_size'],
                skiptoken=export_result['next_skiptoken'],
                params=request_data['params'],
            )

        return request.make_json_response(response_payload)

    def _build_next_link(
        self,
        page_size,
        skiptoken,
        params,
    ):
        query_params = [
            ('page', page_size),
            ('$skiptoken', skiptoken),
        ]
        query_params.extend(params.items())
        query_string = urlencode(query_params, doseq=True, safe='$')
        return f'{request.httprequest.base_url}?{query_string}'
