from odoo import http

from .common import API_PREFIX, DEFAULT_LIMIT, Slim4ControllerMixin


class Slim4Transactions(Slim4ControllerMixin, http.Controller):
    """HTTP controller for the Slim4 Transactions interface."""

    _interface_technical_name = 'S4Import_Transactions'

    @http.route(
        route=f'{API_PREFIX}/transactions',
        type='http',
        auth='bearer',
        methods=['GET'],
    )
    def get_stock_transactions(self, limit=DEFAULT_LIMIT, after_id=None, **params):
        return self._export_collection(limit=limit, after_id=after_id, **params)
