import re

from odoo import models

_ERROR_CODE_RE = re.compile(r"^(MODEL_NOT_FOUND|FIELD_NOT_FOUND|ACCESS_DENIED|INVALID_QUERY|QUERY_FAILED):")


class MailMessage(models.Model):
    _inherit = "mail.message"

    def execute_tool_call(self, thread_model=None):
        self.ensure_one()
        tool_data = self.get_tool_data() or {}
        tool_name = tool_data.get("tool_name") or (tool_data.get("tool_call", {}).get("function", {}) or {}).get("name")
        result = yield from super().execute_tool_call(thread_model=thread_model)
        if tool_name == "odoo_record_retriever":
            updated = self.get_tool_data() or {}
            if updated.get("status") == "error":
                error_text = updated.get("error", "")
                match = _ERROR_CODE_RE.match(error_text)
                if match:
                    updated["error_code"] = match.group(1)
                    diagnostic = re.search(r"diagnostic_id=([0-9a-f]+)", error_text)
                    if diagnostic:
                        updated["diagnostic_id"] = diagnostic.group(1)
                    self.write({"body_json": updated})
                    yield {"type": "message_update", "message": self.to_store_format()}
        return result
