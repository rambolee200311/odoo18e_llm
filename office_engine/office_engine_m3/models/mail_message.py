import re

from odoo import api, fields, models
from odoo.osv import expression

_ERROR_CODE_RE = re.compile(r"^(MODEL_NOT_FOUND|FIELD_NOT_FOUND|ACCESS_DENIED|INVALID_QUERY|QUERY_FAILED):")


class MailMessage(models.Model):
    _inherit = "mail.message"

    llm_silent_retrieval = fields.Boolean(
        string="Silent Retriever Message",
        default=False,
        copy=False,
        index=True,
        help="Internal successful Retriever messages are retained for audit and context, but hidden from the chat UI.",
    )

    @api.model
    def _message_fetch(
        self,
        domain,
        search_term=None,
        before=None,
        after=None,
        around=None,
        limit=30,
    ):
        """Hide successful Retriever audit rows from Discuss history, not from storage."""
        is_llm_thread = any(
            condition[0] == "model"
            and condition[1] == "="
            and condition[2] == "llm.thread"
            for condition in domain
            if isinstance(condition, (list, tuple)) and len(condition) == 3
        )
        if is_llm_thread:
            domain = expression.AND([domain, [("llm_silent_retrieval", "=", False)]])
        return super()._message_fetch(
            domain,
            search_term=search_term,
            before=before,
            after=after,
            around=around,
            limit=limit,
        )

    def execute_tool_call(self, thread_model=None):
        self.ensure_one()
        tool_data = self.get_tool_data() or {}
        tool_name = tool_data.get("tool_name") or (tool_data.get("tool_call", {}).get("function", {}) or {}).get("name")
        was_silent = bool(self.llm_silent_retrieval)
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
                self.write({"body_json": updated, "llm_silent_retrieval": False})
                if was_silent:
                    visible_messages = self._office_m3_reveal_retriever_failure(
                        thread_model=thread_model,
                        tool_call_id=updated.get("tool_call_id"),
                    )
                    for message in visible_messages:
                        if thread_model and thread_model._name == "llm.thread":
                            thread_model._notify_thread(message)
                        yield {"type": "message_create", "message": message.to_store_format()}
                else:
                    yield {"type": "message_update", "message": self.to_store_format()}
        return result

    def _office_m3_reveal_retriever_failure(self, thread_model=None, tool_call_id=None):
        """Make a failed retrieval and its formerly hidden assistant call visible."""
        self.ensure_one()
        messages = self
        if not thread_model or thread_model._name != "llm.thread" or not tool_call_id:
            return messages

        def has_call(message):
            body_json = message.body_json or {}
            for call in body_json.get("tool_calls", []):
                function = call.get("function") or {}
                if (
                    call.get("id") == tool_call_id
                    and function.get("name") == "odoo_record_retriever"
                ):
                    return True
            return False

        assistant_messages = thread_model.message_ids.filtered(
            lambda message: (
                message.llm_role == "assistant"
                and message.llm_silent_retrieval
                and has_call(message)
            )
        )
        if assistant_messages:
            assistant_messages.write({"llm_silent_retrieval": False})
            messages |= assistant_messages
        return messages
