from odoo import http

from .common import API_PREFIX, DEFAULT_PAGE_SIZE, Slim4ControllerMixin


class Slim4ArticleFilterController(Slim4ControllerMixin, http.Controller):
    """HTTP controller for the Slim4 Article Code Master interface."""

    _interface_technical_name = 'S4Import_ArticleFilter'

    @http.route(
        route=f'{API_PREFIX}/article-filter',
        type='http',
        auth='bearer',
        methods=['GET'],
    )
    def get_article_filter(
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
