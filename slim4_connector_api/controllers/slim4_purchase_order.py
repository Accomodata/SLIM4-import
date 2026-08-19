from odoo import http

from .common import API_PREFIX, DEFAULT_PAGE_SIZE, Slim4ControllerMixin


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
        page=DEFAULT_PAGE_SIZE,
        **params,
    ):
        skip = params.pop('$skip', None)
        skiptoken = params.pop('$skiptoken', None)

        return self._export_collection(
            page=page,
            skip=skip,
            skiptoken=skiptoken,
            **params,
        )
