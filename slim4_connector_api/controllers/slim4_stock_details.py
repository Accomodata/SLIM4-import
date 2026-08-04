from odoo import http

from .common import API_PREFIX, DEFAULT_LIMIT, Slim4ControllerMixin


class Slim4StockDetails(Slim4ControllerMixin, http.Controller):
    """HTTP controller for the Slim4 Stock Details interface."""

    _interface_technical_name = 'S4Import_StockDetails'

    @http.route(
        route=f'{API_PREFIX}/stock-details',
        type='http',
        auth='bearer',
        methods=['GET'],
    )
    def get_stock_details(self, limit=DEFAULT_LIMIT, cursor=None, **params):
        return self._export_collection(limit=limit, cursor=cursor, **params)
