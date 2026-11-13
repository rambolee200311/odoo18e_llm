import uuid

from odoo.exceptions import AccessError, UserError


class _RetrieverErrorMetadata:
    def __init__(self, error_code, message, diagnostic_id=None):
        self.error_code = error_code
        self.diagnostic_id = diagnostic_id or uuid.uuid4().hex
        self._retriever_message = f"{error_code}: {message} (diagnostic_id={self.diagnostic_id})"


class RetrieverToolError(_RetrieverErrorMetadata, UserError):
    """Sanitized non-permission Retriever error with a stable error code."""

    def __init__(self, error_code, message, diagnostic_id=None):
        _RetrieverErrorMetadata.__init__(self, error_code, message, diagnostic_id)
        UserError.__init__(self, self._retriever_message)


class RetrieverAccessError(_RetrieverErrorMetadata, AccessError):
    """Keep Odoo's AccessError semantics while exposing a stable Retriever code."""

    def __init__(self, message="The current user cannot read the requested records.", diagnostic_id=None):
        _RetrieverErrorMetadata.__init__(self, "ACCESS_DENIED", message, diagnostic_id)
        AccessError.__init__(self, self._retriever_message)
