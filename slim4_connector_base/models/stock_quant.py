from odoo import fields, models
from odoo.tools import SQL


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    available_quantity = fields.Float(search='_search_available_quantity')

    def _search_available_quantity(self, operator, value):
        sql_operators = {
            '>': SQL('>'),
            '>=': SQL('>='),
            '<': SQL('<'),
            '<=': SQL('<='),
        }
        if operator not in sql_operators:
            return NotImplemented

        self.flush_model(['quantity', 'reserved_quantity'])

        subquery = SQL(
            """
            SELECT id
              FROM stock_quant
             WHERE quantity - reserved_quantity %s %s
            """,
            sql_operators[operator],
            value,
        )
        return [('id', 'in', subquery)]
