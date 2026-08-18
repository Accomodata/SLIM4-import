import json
import logging

from odoo.exceptions import AccessError, UserError
from odoo.http import request

from ..helpers.handler_mapping import get_inbound_handler
from ..services.errors import InvalidJsonError, Slim4InboundError
from odoo.addons.slim4_connector_api.controllers.common import make_error_response

_logger = logging.getLogger(__name__)


def make_success_response(payload, status=200):
    """Create a successful JSON response using the connector API convention."""
    return request.make_json_response(payload, status=status)


class Slim4InboundControllerMixin:
    """Shared HTTP flow for inbound Slim4 endpoints."""

    _operation = None

    def _receive_payload(self):
        try:
            payload = self._parse_json_payload()
            handler = get_inbound_handler(request.env, self._operation)
            result = handler.handle_payload(payload)
        except Slim4InboundError as error:
            return make_error_response(
                code=error.code,
                message=str(error),
                status=error.status,
                context=error.context,
            )
        except AccessError:
            return make_error_response(
                code='access_denied',
                message='You do not have permission to receive Slim4 data.',
                status=403,
                context={'operation': self._operation},
            )
        except UserError as error:
            return make_error_response(
                code='processing_error',
                message=str(error),
                status=422,
                context={'operation': self._operation},
            )
        except Exception:
            _logger.exception(
                'Unexpected error while receiving Slim4 operation %s.',
                self._operation,
            )
            return make_error_response(
                code='internal_error',
                message='An unexpected error occurred while receiving Slim4 data.',
                status=500,
                context={'operation': self._operation},
            )

        return make_success_response(result)

    def _parse_json_payload(self):
        try:
            raw_payload = request.httprequest.get_data(as_text=True)
            return json.loads(raw_payload)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InvalidJsonError(
                'The request body must contain valid JSON.',
            ) from error
