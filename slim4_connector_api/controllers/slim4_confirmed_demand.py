from odoo import http

from .common import API_PREFIX, DEFAULT_LIMIT, Slim4ControllerMixin


class Slim4ConfirmedDemand(Slim4ControllerMixin, http.Controller):
    """HTTP controller for the Slim4 Confirmed Demand interface."""

    _interface_technical_name = 'S4Import_ConfirmedDemand'

    @http.route(
        route=f'{API_PREFIX}/confirmed-demand',
        type='http',
        auth='bearer',
        methods=['GET'],
    )
    def get_confirmed_demand(
        self,
        limit=DEFAULT_LIMIT,
        offset=0,
        date_from=None,
        **params,
    ):
        """Expose the contract of the Confirmed Demand endpoint."""
        request_data, error_response = self._prepare_collection_request(
            limit=limit,
            offset=offset,
            date_from=date_from,
        )
        if error_response:
            return error_response

        return self._make_not_implemented_response(
            request_data['interface_config'],
        )
