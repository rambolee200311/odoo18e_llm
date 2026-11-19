"""扩展 LLM Provider，在受限测试开关下记录真实 OpenAI SDK 请求与响应。"""
import contextvars
import json
import os
import uuid
from datetime import datetime, timezone

from odoo import models

from ..services.provider_request_audit import provider_audit_thread_id


_ACTIVE_PROVIDER_AUDIT = contextvars.ContextVar("office_m4_tv_provider_audit", default=None)


def _write_provider_audit(path, record):
    """以受限文件权限追加不含凭据的 Provider SDK 审计事件。

    参数：path 为可选审计文件路径；record 为 JSON 可序列化事件。
    返回：无；path 为空时不写入。
    """
    if not path:
        return
    encoded = (json.dumps(record, ensure_ascii=False, sort_keys=True, default=str) + "\n").encode("utf-8")
    fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, encoded)
    finally:
        os.close(fd)


class _AuditedCompletions:
    """包装 OpenAI completions 调用并按需审计请求边界。"""

    def __init__(self, target, path):
        self._target = target
        self._path = path

    def create(self, *args, **kwargs):
        """发送单次 completion 请求，并记录请求、响应或异常边界。

        审计仅记录 SDK 请求边界，不改变实际 Provider 参数。
        """
        audit = _ACTIVE_PROVIDER_AUDIT.get() or {}
        request_id = str(uuid.uuid4())
        _write_provider_audit(self._path, {
            "event": "sdk_request_submitted",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            **audit,
            "payload": kwargs,
        })
        try:
            response = self._target.create(*args, **kwargs)
        except Exception as exc:
            _write_provider_audit(self._path, {
                "event": "sdk_request_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id,
                **audit,
                "error_type": type(exc).__name__,
                "error": str(exc)[:1000],
            })
            raise
        if not kwargs.get("stream"):
            try:
                response_data = response.model_dump(mode="json")
            except Exception:
                response_data = {
                    "id": getattr(response, "id", None),
                    "model": getattr(response, "model", None),
                    "choices": [
                        {
                            "finish_reason": getattr(choice, "finish_reason", None),
                            "message": {
                                "content": getattr(getattr(choice, "message", None), "content", None),
                                "tool_calls": [
                                    {
                                        "id": getattr(call, "id", None),
                                        "name": getattr(getattr(call, "function", None), "name", None),
                                        "arguments": getattr(getattr(call, "function", None), "arguments", None),
                                    }
                                    for call in (getattr(getattr(choice, "message", None), "tool_calls", None) or [])
                                ],
                            },
                        }
                        for choice in (getattr(response, "choices", None) or [])
                    ],
                }
            _write_provider_audit(self._path, {
                "event": "provider_response_received",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id,
                **audit,
                "response": response_data,
            })
        else:
            _write_provider_audit(self._path, {
                "event": "provider_stream_opened",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id,
                **audit,
                "response_id": getattr(response, "response_id", None),
                "boundary": "SDK returned a stream; stream chunks are consumed by the upstream adapter.",
            })
            return _AuditedStream(response, self._path, request_id, audit)
        return response


class _AuditedStream:
    """逐块记录 OpenAI 流式响应，同时保留上游迭代接口。"""

    def __init__(self, target, path, request_id, audit):
        self._target = target
        self._path = path
        self._request_id = request_id
        self._audit = audit

    def __iter__(self):
        """记录并原样产出每个响应块。"""
        for index, chunk in enumerate(self._target):
            try:
                data = chunk.model_dump(mode="json")
            except Exception:
                data = str(chunk)[:4000]
            _write_provider_audit(self._path, {
                "event": "provider_stream_chunk",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": self._request_id,
                "chunk_index": index,
                **self._audit,
                "chunk": data,
            })
            yield chunk

    def __getattr__(self, name):
        return getattr(self._target, name)

    def close(self):
        """关闭上游流式响应对象；底层对象不支持 close 时不作处理。"""
        close = getattr(self._target, "close", None)
        if close:
            return close()
        return None


class _AuditedChat:
    """为 Chat Completions 建立可选审计包装。"""

    def __init__(self, target, path):
        self.completions = _AuditedCompletions(target.completions, path)


class _AuditedOpenAIClient:
    """转发 OpenAI 客户端属性，并包装 Chat Completions 请求。"""

    def __init__(self, target, path):
        self._target = target
        self.chat = _AuditedChat(target.chat, path)

    def __getattr__(self, name):
        return getattr(self._target, name)


class LLMProvider(models.Model):
    """为现有 Provider SDK 调用增加受限的测试请求审计能力。"""

    _inherit = "llm.provider"

    def openai_chat(
        self,
        messages,
        model=None,
        stream=False,
        tools=None,
        prepend_messages=None,
        _office_m4_tv_audit_thread_id=None,
        **kwargs,
    ):
        """委派现有 OpenAI Chat 调用，并按测试开关记录请求 Thread。

        参数：沿用上游消息、模型、流式、工具和前置消息参数；
        ``_office_m4_tv_audit_thread_id`` 仅用于测试审计关联。
        返回：上游 Provider 的标准响应或流式迭代器。
        """
        thread_ids = sorted({
            int(message.res_id)
            for message in messages
            if getattr(message, "model", None) == "llm.thread"
            and str(getattr(message, "res_id", "")).isdigit()
        }) if getattr(messages, "_name", None) == "mail.message" else []
        if _office_m4_tv_audit_thread_id:
            audited_id = provider_audit_thread_id(self.env, _office_m4_tv_audit_thread_id)
            if audited_id:
                thread_ids = [audited_id]
        audit_path = self._office_m4_provider_audit_path(thread_ids)
        if not audit_path:
            return super().openai_chat(
                messages, model=model, stream=stream, tools=tools, prepend_messages=prepend_messages, **kwargs
            )
        tool_records = list(tools) if tools else []
        token = _ACTIVE_PROVIDER_AUDIT.set({
            "provider_id": self.id,
            "provider_name": self.name,
            "service": self.service,
            "model": getattr(model, "name", model),
            "thread_ids": thread_ids,
            "tool_ids": [tool.id for tool in tool_records],
            "tool_names": [tool.name for tool in tool_records],
        })
        try:
            return super().openai_chat(
                messages, model=model, stream=stream, tools=tools, prepend_messages=prepend_messages, **kwargs
            )
        finally:
            _ACTIVE_PROVIDER_AUDIT.reset(token)

    def openai_get_client(self):
        """根据当前调用上下文返回普通客户端或带选项的轻量包装器。"""
        client = super().openai_get_client()
        audit = _ACTIVE_PROVIDER_AUDIT.get() or {}
        audit_path = self._office_m4_provider_audit_path(audit.get("thread_ids", []))
        if audit_path:
            return _AuditedOpenAIClient(client, audit_path)
        return client

    def _office_m4_provider_audit_path(self, thread_ids):
        """确认测试审计是否允许写入指定路径。

        参数：thread_ids 为当前请求关联的 Thread ID。返回：仅在环境变量配置了
        审计路径且所有 Thread 均通过测试开关与 allowlist 核验时返回该路径，否则返回 None。
        """
        path = os.environ.get("OFFICE_M4_TV_PROVIDER_AUDIT_PATH")
        if not path or not thread_ids:
            return None
        return path if all(provider_audit_thread_id(self.env, thread_id) for thread_id in thread_ids) else None

    def _openai_format_tool(self, tool):
        """Send the downstream M3 schema, not the stored M2 base schema.

        The OpenAI adapter prefers ``llm.tool.input_schema`` when populated,
        which bypasses ``get_input_schema()`` and its M3 extension. Resolve the
        effective schema here so Provider Tool Calling receives the same
        contract that Odoo validates during execution.
        """
        if self.service == "openai" and tool.name == "office":
            return self._create_openai_tool_from_schema(tool.get_input_schema(), tool)
        return super()._openai_format_tool(tool)
