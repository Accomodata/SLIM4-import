from odoo import http

from odoo.addons.slim4_connector_api.controllers.common import API_PREFIX

from .common import Slim4InboundControllerMixin


class Slim4OrdersInboundController(Slim4InboundControllerMixin, http.Controller):
    """Receive the order payload."""

    _operation = 'orders'

    @http.route(
        route=f'{API_PREFIX}/orders',
        type='http',
        auth='bearer',
        methods=['POST'],
        csrf=False,
    )
    def receive_orders(self, **params):
        return self._receive_payload()
