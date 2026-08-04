from odoo import http

from .common import API_PREFIX, DEFAULT_LIMIT, Slim4ControllerMixin


class Slim4Logistics(Slim4ControllerMixin, http.Controller):
    """HTTP controller for the Slim4 Logistics interface."""

    _interface_technical_name = 'S4Import_Logistics'

    @http.route(
        route=f'{API_PREFIX}/logistics',
        type='http',
        auth='bearer',
        methods=['GET'],
    )
    def get_logistics(self, limit=DEFAULT_LIMIT, offset=0, **params):
        return self._export_collection(limit=limit, offset=offset)
