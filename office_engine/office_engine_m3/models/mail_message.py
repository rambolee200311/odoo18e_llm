"""本模块实现 Office Engine 中 `mail_message` 对应的 Odoo 模型扩展与业务处理。"""
import re

from odoo import api, fields, models
from odoo.osv import expression

_ERROR_CODE_RE = re.compile(r"^(MODEL_NOT_FOUND|FIELD_NOT_FOUND|ACCESS_DENIED|INVALID_QUERY|QUERY_FAILED):")


class MailMessage(models.Model):
    """封装 `MailMessage` 对应的功能、状态或数据结构。"""
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
        """执行工具并保留 Retriever 错误的内部回执。

        参数：``thread_model`` 为关联的 LLM Thread。
        返回：上游工具执行器的生成结果；错误状态和诊断仍写入消息。

        纯 Retriever 消息在工具执行前已标记为内部消息。执行失败时保留该标记，
        让 Agent 在后续模型轮次读取错误；最终失败由 assistant 答复对用户说明，
        避免把尚未确定的中间错误提前作为业务结果展示。
        """
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
                self.write({
                    "body_json": updated,
                    "llm_silent_retrieval": was_silent,
                })
                if not was_silent:
                    yield {"type": "message_update", "message": self.to_store_format()}
        return result
