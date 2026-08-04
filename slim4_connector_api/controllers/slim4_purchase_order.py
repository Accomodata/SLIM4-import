from odoo import http

from .common import API_PREFIX, DEFAULT_LIMIT, Slim4ControllerMixin


class Slim4PurchaseOrder(Slim4ControllerMixin, http.Controller):
    """HTTP controller for the Slim4 Purchase Order interface."""

    _interface_technical_name = 'S4Import_PurchaseOrder'

    @http.route(
        route=f'{API_PREFIX}/purchase-order',
        type='http',
        auth='bearer',
        methods=['GET'],
    )
    def get_purchase_order(
        self,
        limit=DEFAULT_LIMIT,
        offset=0,
        date_from=None,
        **params,
    ):
        """Expose the contract of the Purchase Order endpoint."""
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
