from odoo import models


class Slim4LogisticsExportProvider(models.AbstractModel):
    _name = 'slim4.export.provider.logistics'
    _inherit = 'slim4.export.provider'
    _description = 'Slim4 Logistics Export Provider'
