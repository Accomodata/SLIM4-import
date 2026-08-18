class Slim4InboundError(ValueError):
    """Base error raised by the inbound Slim4 request flow."""

    code = 'invalid_request'
    status = 400

    def __init__(self, message, context=None):
        super().__init__(message)
        self.context = context


class InvalidJsonError(Slim4InboundError):
    code = 'invalid_json'
    status = 400


class PayloadValidationError(Slim4InboundError):
    code = 'invalid_payload'
    status = 422


class UnknownOperationError(Slim4InboundError):
    code = 'unknown_operation'
    status = 404
