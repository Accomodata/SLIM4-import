import uuid

from odoo import api, fields, models

from ..services.order_payload_validator import validate_order_payload


class Slim4OrdersInboundHandler(models.AbstractModel):
    _name = 'slim4.inbound.handler.orders'
    _inherit = 'slim4.inbound.handler'
    _description = 'Slim4 Orders Inbound Handler'

    @api.model
    def _validate_payload(self, payload):
        return validate_order_payload(payload)

    @api.model
    def _process_payload(self, validated_payload):
        """Stage a validated batch without applying customer-specific rules."""
        batch_reference = str(uuid.uuid4())

        article_codes = {
            str(order['articleCode'])
            for order in validated_payload
        }
        supplier_numbers = {
            str(order['supplierNumber'])
            for order in validated_payload
        }

        product_by_code = self._get_products_by_code(article_codes)
        suppliers_by_ref = self._get_suppliers_by_ref(supplier_numbers)

        message_vals_list = []
        for item_index, order in enumerate(validated_payload):
            article_code = str(order['articleCode'])
            supplier_number = str(order['supplierNumber'])
            product = product_by_code.get(article_code)
            supplier = suppliers_by_ref.get(supplier_number)

            resolution_errors = []
            if not product:
                resolution_errors.append(
                    f'Product with article code "{article_code}" was not found.',
                )
            if not supplier:
                resolution_errors.append(
                    f'Supplier with number "{supplier_number}" was not found.',
                )

            message_vals_list.append({
                'operation': 'orders',
                'batch_reference': batch_reference,
                'item_index': item_index,
                'payload': order,
                'product_id': product.id if product else False,
                'supplier_id': supplier.id if supplier else False,
                'status': 'error' if resolution_errors else 'received',
                'error_message': ' '.join(resolution_errors) or False,
            })

        self.env['slim4.inbound.message'].create(message_vals_list)

        return {
            'status': 'success',
            'message': 'Orders received successfully',
        }

    def _get_products_by_code(self, article_codes):
        products = self.env['product.product'].search([
            ('default_code', 'in', list(article_codes)),
        ])
        return {
            product.default_code: product
            for product in products
        }

    def _get_suppliers_by_ref(self, supplier_numbers):
        suppliers = self.env['res.partner'].search([
            ('ref', 'in', list(supplier_numbers)),
        ])
        return {
            supplier.ref: supplier
            for supplier in suppliers
        }

    @api.model
    def process_received_messages(self):
        """Create draft purchase orders from resolved inbound messages."""
        grouped_messages = self.env['slim4.inbound.message']._read_group(
            domain=[
                ('operation', '=', 'orders'),
                ('status', '=', 'received'),
                ('supplier_id', '!=', False),
                ('product_id', '!=', False),
            ],
            groupby=['batch_reference', 'supplier_id'],
            aggregates=['id:recordset'],
        )

        processed_count = 0
        processed_at = fields.Datetime.now()
        for _batch_reference, supplier, messages in grouped_messages:
            company = messages[0].company_id
            purchase_order = self.env['purchase.order'].with_company(company).create({
                'partner_id': supplier.id,
                'company_id': company.id,
            })

            self.env['purchase.order.line'].with_company(company).create([
                {
                    'order_id': purchase_order.id,
                    'product_id': message.product_id.id,
                    'product_qty': message.payload['toOrder'],
                }
                for message in messages
            ])

            messages.write({
                'status': 'processed',
                'processed_at': processed_at,
            })
            processed_count += len(messages)

        return processed_count
