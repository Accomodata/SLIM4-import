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
    def get_purchase_order(self, limit=DEFAULT_LIMIT, offset=0, **params):
        return self._export_collection(limit=limit, offset=offset)
