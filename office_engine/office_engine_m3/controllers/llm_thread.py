"""在 Odoo 事务提交后再向客户端释放非流式 Office 生成事件。"""

import tempfile

from odoo import http
from odoo.http import request

from odoo.addons.llm_thread.controllers.main import LLMThreadController


def defer_sse_events_until_source_exhausted(events, *, spool_limit=1024 * 1024):
    """缓冲 SSE 事件，直至原生成器完成其数据库事务。

    参数：
        events: 上游 SSE 字节块迭代器；耗尽它会退出上游 Odoo Cursor 上下文。
        spool_limit: 内存缓冲上限；超出后由标准库临时文件承接。
    返回：
        一个按原顺序产出相同字节块的迭代器。上游正常结束并提交后才开始产出；
        上游异常时向调用方传播异常且不会发送未提交事件。
    """
    with tempfile.SpooledTemporaryFile(max_size=spool_limit, mode="w+b") as spool:
        for chunk in events:
            spool.write(chunk)
        spool.seek(0)
        while chunk := spool.read(64 * 1024):
            yield chunk


class OfficeM4LLMThreadController(LLMThreadController):
    """确保 M4 非流式 Office 路径的 SSE 不先于 Odoo 持久化提交。"""

    @http.route(
        "/llm/thread/generate",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=True,
    )
    def llm_thread_generate(
        self,
        thread_id,
        message=None,
        attachment_ids=None,
        **kwargs,
    ):
        """委派上游生成端点，并仅为非流式 Office 请求延后 SSE 发送。

        业务消息仍由上游原有生成器写入当前请求事务，Bus 仍由 Odoo 原生事务后
        通知发送。本方法只缓冲该路径的 HTTP SSE 字节，避免浏览器先看到尚未提交
        的 `mail.message`。其他 Thread 和流式路径保持上游时序。
        """
        thread = request.env["llm.thread"].browse(int(thread_id)).exists()
        parsed_attachment_ids = [
            int(value)
            for value in (attachment_ids or "").split(",")
            if value.strip().isdigit()
        ] if isinstance(attachment_ids, str) else (attachment_ids or [])
        defer_events = bool(
            thread
            and thread._office_m3_is_non_streaming_office_generation(
                message,
                parsed_attachment_ids,
            )
        )

        response = super().llm_thread_generate(
            thread_id,
            message=message,
            attachment_ids=attachment_ids,
            **kwargs,
        )
        if defer_events:
            response.response = defer_sse_events_until_source_exhausted(response.response)
        return response
