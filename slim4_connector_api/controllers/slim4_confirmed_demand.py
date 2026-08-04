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
    def get_confirmed_demand(self, limit=DEFAULT_LIMIT, cursor=None, **params):
        return self._export_collection(limit=limit, cursor=cursor, **params)
