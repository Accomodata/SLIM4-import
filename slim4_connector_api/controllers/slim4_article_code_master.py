from odoo import http

from .common import API_PREFIX, DEFAULT_LIMIT, Slim4ControllerMixin


class Slim4ArticleCodeMasterController(Slim4ControllerMixin, http.Controller):
    """HTTP controller for the Slim4 Article Code Master interface."""

    _interface_technical_name = 'S4Import_ArticleCodeMaster'

    @http.route(
        route=f'{API_PREFIX}/article-code-master',
        type='http',
        auth='bearer',
        methods=['GET'],
    )
    def get_article_code_master(self, limit=DEFAULT_LIMIT, after_id=None, **params):
        return self._export_collection(limit=limit, after_id=after_id, **params)
