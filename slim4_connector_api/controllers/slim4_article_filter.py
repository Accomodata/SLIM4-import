from odoo import http

from .common import API_PREFIX, DEFAULT_LIMIT, Slim4ControllerMixin


class Slim4ArticleFilterController(Slim4ControllerMixin, http.Controller):
    """HTTP controller for the Slim4 Article Filter interface."""

    _interface_technical_name = 'S4Import_ArticleFilter'

    @http.route(
        route=f'{API_PREFIX}/article-filter',
        type='http',
        auth='bearer',
        methods=['GET'],
    )
    def get_article_filter(self, limit=DEFAULT_LIMIT, after_id=None, **params):
        return self._export_collection(limit=limit, after_id=after_id, **params)
