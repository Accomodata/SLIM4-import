from odoo import http

from .common import API_PREFIX, DEFAULT_PAGE_SIZE, Slim4ControllerMixin


class Slim4Suppliers(Slim4ControllerMixin, http.Controller):
    """HTTP controller for the Slim4 Suppliers interface."""

    _interface_technical_name = 'S4Import_Suppliers'

    @http.route(
        route=f'{API_PREFIX}/suppliers',
        type='http',
        auth='bearer',
        methods=['GET'],
    )
    def get_suppliers(
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
