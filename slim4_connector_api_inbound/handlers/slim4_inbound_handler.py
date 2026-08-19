from odoo import api, models


class Slim4InboundHandler(models.AbstractModel):
    _name = 'slim4.inbound.handler'
    _description = 'Slim4 Inbound Handler'

    @api.model
    def handle_payload(self, payload):
        """Validate and process one inbound payload."""
        validated_payload = self._validate_payload(payload)
        return self._process_payload(validated_payload)

    @api.model
    def _validate_payload(self, payload):
        raise NotImplementedError()

    @api.model
    def _process_payload(self, validated_payload):
        raise NotImplementedError()
