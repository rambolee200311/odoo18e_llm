"""验证静默 Retriever 消息的可见性边界及审计保留行为。"""

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from odoo import api
from odoo.exceptions import UserError
from odoo.http import Response
from odoo.modules.registry import Registry
from odoo.tests import TransactionCase

from odoo.addons.llm_thread.models.llm_thread import LLMThread as NativeThread
from odoo.addons.office_engine_m2.tests.support import (
    XLSX_MIMETYPE,
    WorkbookVersionFixtures,
    synthetic_xlsx,
)
from odoo.addons.office_engine_m3.controllers.llm_thread import (
    OfficeM4LLMThreadController,
    defer_sse_events_until_source_exhausted,
)
from odoo.addons.llm_thread.controllers.main import LLMThreadController


class TestSilentRetrieval(WorkbookVersionFixtures, TransactionCase):
    """验证 Retriever 静默可见性、当前任务指引与 M2/M3 附件兼容行为。"""
    @classmethod
    def setUpClass(cls):
        """创建非流式路径测试所用的 GPT-5 模型记录。"""
        super().setUpClass()
        cls.gpt5_model = cls.env["llm.model"].create(
            {
                "name": "gpt-5.6-cc-m3-03-test",
                "provider_id": cls.provider.id,
                "model_use": "chat",
            }
        )

    def _thread(self, *, gpt5=True):
        thread = self.env["llm.thread"].create(
            {
                "name": "M3 silent retrieval " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.gpt5_model.id if gpt5 else self.model.id,
            }
        )
        thread._office_bind_tools()
        return thread

    def test_non_stream_sse_waits_until_source_transaction_finishes(self):
        """确认 Odoo 提交 assistant 消息并运行 postcommit 后才释放 SSE。"""
        state = {"postcommit_called": False, "message_id": None}

        def source_events():
            """在独立 Odoo Cursor 中持久化消息，再注册提交回调并产生事件。"""
            with Registry(self.env.cr.dbname).cursor() as cursor:
                isolated_env = api.Environment(cursor, self.env.uid, {})
                message = isolated_env["mail.message"].create({
                    "model": "res.partner",
                    "res_id": self.env.user.partner_id.id,
                    "llm_role": "assistant",
                    "message_type": "comment",
                    "body": "Synthetic committed final answer.",
                })
                state["message_id"] = message.id
                cursor.postcommit.add(lambda: state.__setitem__("postcommit_called", True))
                yield f'data: {{"type":"message_create","message_id":{message.id}}}\n\n'.encode()

        try:
            deferred = defer_sse_events_until_source_exhausted(source_events())
            first_chunk = next(deferred)

            self.assertTrue(state["postcommit_called"])
            with Registry(self.env.cr.dbname).cursor() as cursor:
                isolated_env = api.Environment(cursor, self.env.uid, {})
                durable = isolated_env["mail.message"].browse(state["message_id"]).exists()
                self.assertTrue(durable)
                self.assertIn("Synthetic committed final answer.", str(durable.body))
            self.assertEqual(
                first_chunk,
                f'data: {{"type":"message_create","message_id":{state["message_id"]}}}\n\n'.encode(),
            )
        finally:
            if state["message_id"]:
                with Registry(self.env.cr.dbname).cursor() as cursor:
                    api.Environment(cursor, self.env.uid, {})["mail.message"].browse(
                        state["message_id"]
                    ).unlink()

    def test_non_stream_sse_discards_uncommitted_events_on_source_failure(self):
        """确认未提交消息回滚，postcommit 不触发且 SSE 丢弃暂存事件。"""
        state = {"postcommit_called": False, "message_id": None}

        def broken_events():
            """写入消息、注册提交回调，再抛错令实际 Cursor 上下文回滚。"""
            with Registry(self.env.cr.dbname).cursor() as cursor:
                isolated_env = api.Environment(cursor, self.env.uid, {})
                message = isolated_env["mail.message"].create({
                    "model": "res.partner",
                    "res_id": self.env.user.partner_id.id,
                    "llm_role": "assistant",
                    "message_type": "comment",
                    "body": "Synthetic answer must roll back.",
                })
                state["message_id"] = message.id
                cursor.postcommit.add(lambda: state.__setitem__("postcommit_called", True))
                yield f'data: {{"type":"message_create","message_id":{message.id}}}\n\n'.encode()
                raise RuntimeError("synthetic transaction failure")

        deferred = defer_sse_events_until_source_exhausted(broken_events())
        with self.assertRaisesRegex(RuntimeError, "synthetic transaction failure"):
            next(deferred)
        self.assertFalse(state["postcommit_called"])
        with Registry(self.env.cr.dbname).cursor() as cursor:
            isolated_env = api.Environment(cursor, self.env.uid, {})
            self.assertFalse(isolated_env["mail.message"].browse(state["message_id"]).exists())

    def test_postcommit_notification_failure_keeps_persisted_message_readable(self):
        """确认成功、澄清和失败消息在 postcommit 通知异常后均持久可读。"""
        message_ids = []

        def failing_notification():
            """模拟提交完成后由 Odoo postcommit 队列运行失败的通知。"""
            raise RuntimeError("synthetic postcommit notification failure")

        try:
            for body, is_error in (
                ("Synthetic successful final answer remains durable.", False),
                ("Synthetic clarification remains durable.", False),
                ("Synthetic final failure remains durable.", True),
            ):
                with self.subTest(body=body):
                    with self.assertRaisesRegex(RuntimeError, "postcommit notification failure"):
                        with Registry(self.env.cr.dbname).cursor() as cursor:
                            isolated_env = api.Environment(cursor, self.env.uid, {})
                            message = isolated_env["mail.message"].create({
                                "model": "res.partner",
                                "res_id": self.env.user.partner_id.id,
                                "llm_role": "assistant",
                                "message_type": "comment",
                                "body": body,
                                "is_error": is_error,
                            })
                            message_ids.append(message.id)
                            cursor.postcommit.add(failing_notification)

                    with Registry(self.env.cr.dbname).cursor() as cursor:
                        isolated_env = api.Environment(cursor, self.env.uid, {})
                        durable = isolated_env["mail.message"].browse(message_ids[-1]).exists()
                        self.assertTrue(durable)
                        self.assertIn(body, str(durable.body))
        finally:
            if message_ids:
                with Registry(self.env.cr.dbname).cursor() as cursor:
                    isolated_env = api.Environment(cursor, self.env.uid, {})
                    isolated_env["mail.message"].browse(message_ids).unlink()

    def test_handoff_failure_final_answer_persists_and_is_visible_after_refetch(self):
        """通过本地 Provider 替身验证 handoff 失败后的真实 Thread 消息循环。"""
        database = self.env.cr.dbname
        thread_id = None
        provider_id = None
        model_id = None
        partner_id = None
        user_id = self.env.uid
        before_bus_ids = set(self.env["bus.bus"].search([]).ids)

        with TemporaryDirectory() as directory:
            audit_path = Path(directory) / "faults.jsonl"
            with Registry(database).cursor() as cursor:
                isolated_env = api.Environment(cursor, user_id, {})
                provider = isolated_env["llm.provider"].create({
                    "name": "CC-M4-03 handoff component " + uuid4().hex,
                    "service": "openai",
                })
                model = isolated_env["llm.model"].create({
                    "name": "gpt-5.6-cc-m4-03-component-" + uuid4().hex,
                    "provider_id": provider.id,
                    "model_use": "chat",
                })
                partner = isolated_env["res.partner"].create({
                    "name": "Synthetic handoff component " + uuid4().hex,
                    "email": "handoff-component@example.invalid",
                })
                thread = isolated_env["llm.thread"].create({
                    "name": "CC-M4-03 handoff persistence " + uuid4().hex,
                    "provider_id": provider.id,
                    "model_id": model.id,
                    "tool_ids": [(6, 0, isolated_env["llm.tool"].search([
                        ("name", "in", ["odoo_record_retriever", "office"]),
                    ]).ids)],
                })
                thread_id, provider_id, model_id, partner_id = thread.id, provider.id, model.id, partner.id
                fault_parameter = isolated_env["ir.config_parameter"].sudo()
                prior_fault = fault_parameter.get_param("office_engine.m4_tv.test_fault")
                fault_parameter.set_param("office_engine.m4_tv.test_fault", json.dumps({
                    "fault": "handoff_interruption",
                    "thread_id": thread.id,
                }))
                assistant_call = {
                    "id": "call-cc-m4-03-handoff-" + uuid4().hex[:8],
                    "type": "function",
                    "function": {
                        "name": "office",
                        "arguments": json.dumps({
                            "action": "export_records",
                            "workbook_source": "new",
                            "source_query": {
                                "model": "res.partner",
                                "domain": [["id", "=", partner.id]],
                                "fields": ["name", "email"],
                                "order": "id asc",
                            },
                            "collections": [],
                            "tables": [{
                                "name": "Records",
                                "source": "root",
                                "columns": [
                                    {"label": "Name", "source_field": "name"},
                                    {"label": "Email", "source_field": "email"},
                                ],
                            }],
                            "verification_profile": "record_projection",
                            "confirmation_required": False,
                        }),
                    },
                }
                provider_calls = []

                def provider_stub(model_record, messages, **kwargs):
                    """依次返回受控 Office Tool Call 和一条最终失败答复。"""
                    provider_calls.append(messages)
                    if len(provider_calls) == 1:
                        return {"content": "", "tool_calls": [assistant_call]}
                    return {
                        "content": "Excel 未生成：数据交接在创建 Candidate 前失败。",
                        "tool_calls": [],
                    }

                with TemporaryDirectory() as fault_audit_directory:
                    fault_audit_path = Path(fault_audit_directory) / "faults.jsonl"
                    with (
                        patch.dict("os.environ", {
                            "OFFICE_M4_TV_TEST_HOOKS": "1",
                            "OFFICE_M4_TV_FAULT_AUDIT_PATH": str(fault_audit_path),
                        }),
                        patch.object(type(model), "supports_streaming", False, create=True),
                        patch.object(type(model), "chat", provider_stub),
                        patch(
                            "odoo.addons.office_engine_m3.services.export_orchestrator._provider_dependencies",
                            return_value=(SimpleNamespace(calls=[]), object(), "synthetic-route-b", SimpleNamespace()),
                        ),
                    ):
                        events = list(thread.generate(
                            user_message_body="Export this synthetic record to Excel.",
                            attachment_ids=[],
                        ))
                    fault_rows = [
                        json.loads(line)
                        for line in fault_audit_path.read_text(encoding="utf-8").splitlines()
                        if line.strip()
                    ]
                final_events = [event for event in events if event.get("type") == "message_create"]
                self.assertEqual(len(provider_calls), 2)
                self.assertTrue(final_events)
                cursor.commit()

            # 关闭原 Cursor 后重新读取，模拟用户刷新或重新打开 Thread。
            with Registry(database).cursor() as cursor:
                reopened_env = api.Environment(cursor, user_id, {})
                reopened_thread = reopened_env["llm.thread"].browse(thread_id).exists()
                history = reopened_env["mail.message"]._message_fetch(
                    [("model", "=", "llm.thread"), ("res_id", "=", thread_id)],
                    limit=100,
                )["messages"]
                final = history.filtered(
                    lambda message: message.llm_role == "assistant"
                    and "Excel 未生成" in str(message.body)
                )
                tool_results = reopened_env["mail.message"].search([
                    ("model", "=", "llm.thread"),
                    ("res_id", "=", thread_id),
                    ("llm_role", "=", "tool"),
                ])
                versions = reopened_env["office.workbook.version"].search([("thread_id", "=", thread_id)])
                sessions = reopened_env["office.mapping.session"].search([("thread_id", "=", thread_id)])
                self.assertTrue(reopened_thread)
                self.assertEqual(len(final), 1)
                self.assertFalse(final[0].is_error)
                self.assertIn(final[0].id, history.ids)
                self.assertTrue(any(
                    (message.body_json or {}).get("result", {}).get("error_code") == "export_plan_or_integrity_invalid"
                    for message in tool_results
                ))
                self.assertFalse(versions)
                self.assertFalse(sessions)
                self.assertEqual(len(fault_rows), 1)
                self.assertEqual(fault_rows[0]["thread_id"], thread_id)
                self.assertEqual(fault_rows[0]["stage"], "after_complete_collection_before_hosted_ci")

            with Registry(database).cursor() as cursor:
                cleanup_env = api.Environment(cursor, user_id, {})
                cleanup_env["ir.config_parameter"].sudo().set_param("office_engine.m4_tv.test_fault", prior_fault or "")
                cleanup_env["llm.thread"].browse(thread_id).unlink()
                cleanup_env["llm.model"].browse(model_id).unlink()
                cleanup_env["llm.provider"].browse(provider_id).unlink()
                cleanup_env["res.partner"].browse(partner_id).unlink()
                new_bus = cleanup_env["bus.bus"].search([
                    ("create_uid", "=", user_id),
                    ("id", "not in", list(before_bus_ids)),
                ]) if before_bus_ids else cleanup_env["bus.bus"].search([("create_uid", "=", user_id)])
                if new_bus:
                    new_bus.unlink()
                cursor.commit()

    def test_office_generation_endpoint_defers_sse_after_parent_transaction(self):
        """确认已绑定非流式 Office Thread 的原端点输出经事务结束后才释放。"""
        thread = self._thread()
        state = {"source_finished": False}

        def parent_endpoint(controller, thread_id, message=None, attachment_ids=None, **kwargs):
            """模拟上游端点：事件生成器关闭时代表其 Cursor 已结束。"""
            def source_events():
                """产出一个可见 assistant 消息事件并记录事务完成边界。"""
                try:
                    yield b'data: {"type":"message_create"}\n\n'
                finally:
                    state["source_finished"] = True

            return Response(source_events(), direct_passthrough=True)

        fake_request = SimpleNamespace(env=self.env)
        with (
            patch("odoo.addons.office_engine_m3.controllers.llm_thread.request", fake_request),
            patch.object(LLMThreadController, "llm_thread_generate", parent_endpoint),
        ):
            response = OfficeM4LLMThreadController().llm_thread_generate(
                thread.id,
                message="Create an Excel spreadsheet from Odoo records.",
                attachment_ids=[],
            )
            chunks = list(response.response)

        self.assertTrue(state["source_finished"])
        self.assertEqual(chunks, [b'data: {"type":"message_create"}\n\n'])

    def _unbound_thread(self):
        return self.env["llm.thread"].create(
            {
                "name": "M3 unbound export " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.gpt5_model.id,
            }
        )

    def _post_upload(self, thread, filename, body):
        attachment = self.env["ir.attachment"].create({
            "name": filename,
            "type": "binary",
            "mimetype": XLSX_MIMETYPE,
            "raw": synthetic_xlsx(filename),
            "company_id": self.env.company.id,
            "public": False,
        })
        message = thread.message_post(
            body=body,
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        return message, attachment

    @staticmethod
    def _retriever_call(call_id="call-retriever"):
        return {
            "id": call_id,
            "type": "function",
            "function": {"name": "odoo_record_retriever", "arguments": "{}"},
        }

    def test_only_pure_retriever_messages_on_non_stream_office_route_are_marked(self):
        """只将纯 Retriever 内部调用标记为静默消息，混合工具和解释消息保持可见。"""
        thread = self._thread()
        assistant = thread.message_post(
            body="",
            body_json={"tool_calls": [self._retriever_call()]},
            llm_role="assistant",
            author_id=False,
        )
        retrieval = thread.message_post(
            body="Executing odoo_record_retriever",
            body_json={
                "type": "tool_execution",
                "tool_name": "odoo_record_retriever",
                "status": "requested",
            },
            llm_role="tool",
            author_id=False,
        )
        mixed = thread.message_post(
            body="",
            body_json={"tool_calls": [self._retriever_call(), {
                "id": "call-office",
                "type": "function",
                "function": {"name": "office", "arguments": "{}"},
            }]},
            llm_role="assistant",
            author_id=False,
        )
        explanatory = thread.message_post(
            body="I am checking these records.",
            body_json={"tool_calls": [self._retriever_call("call-explained")]},
            llm_role="assistant",
            author_id=False,
        )
        error = thread.message_post(
            body="Retriever failed",
            body_json={
                "type": "tool_execution",
                "tool_name": "odoo_record_retriever",
                "status": "error",
                "error": "ACCESS_DENIED: synthetic",
            },
            llm_role="tool",
            author_id=False,
            is_error=True,
        )
        self.assertTrue(assistant.llm_silent_retrieval)
        self.assertTrue(retrieval.llm_silent_retrieval)
        self.assertEqual(thread._notify_thread(retrieval), [])
        self.assertEqual(
            thread._notify_thread(
                retrieval,
                msg_vals={
                    "llm_silent_retrieval": True,
                    "partner_ids": [self.env.user.partner_id.id],
                },
            ),
            [],
        )
        self.assertFalse(mixed.llm_silent_retrieval)
        self.assertFalse(explanatory.llm_silent_retrieval)
        self.assertFalse(error.llm_silent_retrieval)
        self.assertTrue(thread._office_m3_is_non_streaming_office_route())

        active_non_gpt_thread = self._thread(gpt5=False)
        active_non_gpt_thread.message_post(
            body="Create an Excel spreadsheet from the requested records.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        active_route = active_non_gpt_thread.message_post(
            body="",
            body_json={"tool_calls": [self._retriever_call("call-active-route")]},
            llm_role="assistant",
            author_id=False,
        )
        self.assertTrue(active_route.llm_silent_retrieval)
        self.assertTrue(active_non_gpt_thread._office_m3_is_non_streaming_office_route())

        streaming_thread = self._thread(gpt5=False)
        visible_route = streaming_thread.message_post(
            body="",
            body_json={"tool_calls": [self._retriever_call("call-visible-stream")]},
            llm_role="assistant",
            author_id=False,
        )
        self.assertFalse(visible_route.llm_silent_retrieval)
        self.assertFalse(streaming_thread._office_m3_is_non_streaming_office_route())

    def test_discuss_history_hides_only_marked_messages_and_keeps_rows(self):
        """确认 Discuss 历史隐藏静默内容时仍保留其记录行及其他可见消息。"""
        thread = self._thread()
        user_message = thread.message_post(
            body="Read the synthetic record.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        retrieval = thread.message_post(
            body="Executing odoo_record_retriever",
            body_json={
                "type": "tool_execution",
                "tool_name": "odoo_record_retriever",
                "status": "completed",
                "result": {"status": "success", "records": []},
            },
            llm_role="tool",
            author_id=False,
        )
        final = thread.message_post(
            body="No matching records were found.",
            llm_role="assistant",
            author_id=False,
        )
        self.assertTrue(retrieval.llm_silent_retrieval)
        self.assertTrue(retrieval.exists())
        self.assertEqual(retrieval.body_json["result"]["status"], "success")
        self.assertIn(retrieval, thread._get_context_messages())

        result = self.env["mail.message"]._message_fetch(
            [("model", "=", "llm.thread"), ("res_id", "=", thread.id)],
            limit=100,
        )
        visible_ids = result["messages"].ids
        self.assertIn(user_message.id, visible_ids)
        self.assertIn(final.id, visible_ids)
        self.assertNotIn(retrieval.id, visible_ids)

    def test_sse_filter_keeps_tool_events_errors_and_visible_messages(self):
        """确认 SSE 只过滤静默消息事件，工具状态、错误及最终答复仍然发出。"""
        thread = self._thread()
        silent = thread.message_post(
            body="Executing Retriever",
            body_json={
                "type": "tool_execution",
                "tool_name": "odoo_record_retriever",
                "status": "completed",
                "result": {"status": "success", "records": []},
            },
            llm_role="tool",
            author_id=False,
        )
        visible = thread.message_post(body="Done.", llm_role="assistant", author_id=False)

        def source_events():
            """依次产生静默 Retriever 与可见 assistant 消息事件，供 SSE 过滤测试使用。"""
            yield {"type": "message_create", "message": {"id": silent.id}}
            yield {"type": "tool_succeeded", "tool_data": {"tool_name": "odoo_record_retriever"}}
            yield {"type": "message_update", "message": {"id": silent.id}}
            yield {"type": "message_create", "message": {"id": visible.id}}
            return "generation-result"

        iterator = thread._office_m3_filter_silent_events(source_events())
        emitted = []
        while True:
            try:
                emitted.append(next(iterator))
            except StopIteration as stop:
                self.assertEqual(stop.value, "generation-result")
                break
        self.assertEqual([event["type"] for event in emitted], ["tool_succeeded", "message_create"])
        self.assertEqual(emitted[-1]["message"]["id"], visible.id)

    def test_complete_export_route_requires_registry_discovery_before_search(self):
        """确认完整导出指引要求先发现 Registry 模型，再依据描述执行查询。"""
        thread = self._thread()
        thread.message_post(
            body="Export all matching records to Excel.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )

        kwargs = thread._prepare_chat_kwargs([], use_streaming=False)
        system_text = "\n".join(
            message.get("content", "")
            for message in kwargs.get("prepend_messages", [])
            if message.get("role") == "system"
        )
        self.assertIn("operation=discover", system_text)
        self.assertIn("operation=describe", system_text)
        self.assertIn("do not guess a model", system_text)
        self.assertIn("natural business wording", system_text)
        self.assertIn("ranks registered model metadata semantically", system_text)
        self.assertIn("resolve technical uncertainty", system_text)
        self.assertIn("business meaning remains ambiguous", system_text)
        self.assertIn("before searching business records", system_text)
        self.assertIn("workbook_source=new", system_text)
        self.assertIn("never use Office action=create or action=edit", system_text)
        self.assertIn("Always use action=export_records", system_text)
        self.assertIn("at most two corrective retries after the original call", system_text)
        self.assertIn("a new legitimate planning step or the next page is not a retry", system_text)
        self.assertIn("If the same error repeats without new evidence, stop early", system_text)
        self.assertIn("On ACL or Record Rule denial, stop", system_text)
        self.assertIn("do not resubmit blindly", system_text)
        self.assertIn("source_query (model, domain, fields, order)", system_text)
        self.assertIn("tables (the requested output columns)", system_text)
        self.assertIn("set source to the exact schema value 'root'", system_text)
        self.assertIn("add a separate output table whose source is that collection's declared key", system_text)
        self.assertIn("never use dotted relation paths as table source fields", system_text)
        self.assertIn("validation rejection with operation_executed=false", system_text)
        self.assertIn("do not resend the same rejected parameters", system_text)
        self.assertIn("make one targeted correction only when the valid value is unambiguous", system_text)
        self.assertIn("do not add raw IDs, duplicate fields, or generic display_name columns", system_text)
        self.assertIn("Internal identity columns are added by the Collector", system_text)
        self.assertNotIn("world.depot.outbound.order", system_text)

    def test_current_task_rules_preserve_latest_user_instruction_and_unmodified_constraints(self):
        """确认当前 Provider 上下文包含任务原文，并声明最新指令仅覆盖冲突部分。"""
        thread = self._thread()
        original = thread.message_post(
            body="Find active companies under the synthetic parent in this country created today, with their contacts.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        thread.message_post(
            body="Change the status to inactive; keep the parent, country, date, and contact requirements.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )

        self.assertFalse(thread._office_is_active())
        history = thread.get_llm_messages()
        kwargs = thread._prepare_chat_kwargs(history, use_streaming=False)
        system_text = "\n".join(
            message.get("content", "")
            for message in kwargs.get("prepend_messages", [])
            if message.get("role") == "system"
        )

        self.assertIn(original, history)
        self.assertIn("Change the status to inactive", " ".join(message.body or "" for message in history))
        self.assertIn("latest explicit user instruction", system_text)
        self.assertIn("only where they conflict", system_text)
        self.assertIn("keep every unaffected constraint", system_text)
        self.assertIn("one Retriever tool call per assistant response", system_text)
        self.assertIn("wait for its corresponding result", system_text)
        self.assertIn("against every applicable user constraint", system_text)
        self.assertIn("returned by discover/describe", system_text)
        self.assertIn("Describe is paginated", system_text)
        self.assertIn("continue from next_offset", system_text)
        self.assertIn("business label by searching that model's rec_name field", system_text)
        self.assertIn("rec_name field with the label supplied by the user", system_text)
        self.assertIn("never substitute a display", system_text)
        self.assertIn("Do not probe arbitrary IDs or unrelated business records", system_text)
        self.assertIn("preserve each child's returned parent ID", system_text)
        self.assertIn("every page is collected through has_more=false", system_text)
        self.assertIn("never retry by silently dropping that condition", system_text)
        self.assertIn("Apply those filters before counting or claiming completion", system_text)
        self.assertIn("returned_count is not the requested count", system_text)
        self.assertIn("deterministically applied to the complete candidate set", system_text)
        self.assertIn("No search result, a failed search, or an incomplete page set is not a zero-result answer", system_text)
        self.assertIn("equivalent searchable field or relation", system_text)
        self.assertIn("without an explicit depth is a business-scope ambiguity", system_text)
        self.assertIn("After discovering this ambiguity, do not search target records", system_text)
        self.assertIn("Ask the user to choose between records directly attached", system_text)
        self.assertIn("does not override this clarification requirement", system_text)
        self.assertIn("self-referential relation", system_text)
        self.assertIn("Resume the scoped query only after the user specifies the depth", system_text)
        self.assertIn("Do not expose hidden reasoning", system_text)

    def test_new_fileless_export_is_filtered_before_m2_binds_tools(self):
        """确认无源文件的新建导出请求在 M2 绑定工具前仍能识别正确路由。"""
        thread = self._unbound_thread()
        request = "Export all requested Odoo records to Excel."

        self.assertFalse(thread.tool_ids)
        self.assertFalse(thread._office_m3_is_non_streaming_office_route())
        self.assertTrue(thread._office_m3_is_non_streaming_office_generation(request, []))
        self.assertFalse(thread._office_m3_is_non_streaming_office_generation("Find one record", []))

    def test_chinese_organize_into_excel_request_binds_m3_export_tools_without_upload(self):
        """确认中文自然语言数据导出请求可绑定 M3 导出工具而无需上传源文件。"""
        thread = self._unbound_thread()
        request = (
            "请把 WorldDepot 项目下所有 outbound orders（出库订单）及每单的产品和数量整理成一个 Excel，"
            "包含订单号、Reference 和日期，并保持每条产品明细属于正确订单。"
        )

        self.assertTrue(thread._office_requests_fileless_workbook(request))
        self.assertTrue(thread._office_m3_is_non_streaming_office_generation(request, []))
        with patch.object(NativeThread, "generate", autospec=True, return_value=iter(())):
            list(thread.generate(request, attachment_ids=[]))
        thread.message_post(
            body=request,
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        kwargs = thread._prepare_chat_kwargs(thread.get_llm_messages(), use_streaming=False)
        self.assertEqual(set(kwargs["tools"].mapped("name")), {"office", "odoo_record_retriever"})
        prompt = "\n".join(
            item.get("content", "")
            for item in kwargs["prepend_messages"]
            if item.get("role") == "system"
        )
        self.assertIn("does not require a source workbook or user upload", prompt)
        self.assertIn("workbook_source=new", prompt)
        self.assertIn("Always use action=export_records", prompt)
        self.assertIn("For a new workbook exporting Odoo records, use action=export_records", prompt)
        self.assertNotIn("call office(action='create') once", prompt)
        office_tool = kwargs["tools"].filtered(lambda tool: tool.name == "office")
        schema = office_tool.get_input_schema()
        self.assertIn("export_records", schema["properties"]["action"]["enum"])
        self.assertIn("workbook_source", schema["required"])
        self.assertNotIn("source_attachment_id", schema["properties"])

    def test_latest_upload_remains_available_after_more_than_100_user_messages(self):
        """确认附件上下文不受最近 25 条消息窗口限制。"""
        thread = self._unbound_thread()
        uploaded_message, attachment = self._post_upload(
            thread, "old-source.xlsx", "Please use this workbook."
        )
        for index in range(105):
            thread.message_post(
                body=f"Follow-up message {index}",
                llm_role="user",
                author_id=self.env.user.partner_id.id,
            )
        current_request = thread.message_post(
            body="Please continue editing this workbook.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )

        with patch.object(NativeThread, "generate", autospec=True, return_value=iter(())):
            list(thread.generate(current_request.body, attachment_ids=[]))

        found_message, found_attachment = thread._office_latest_upload()
        self.assertEqual(found_message, uploaded_message)
        self.assertEqual(found_attachment, attachment)
        self.assertNotIn(uploaded_message, thread.get_llm_messages())
        for _provider_turn in range(2):
            kwargs = thread._prepare_chat_kwargs(thread.get_llm_messages(), use_streaming=False)
            prompt = "\n".join(
                item.get("content", "")
                for item in kwargs["prepend_messages"]
                if item.get("role") == "system"
            )
            self.assertIn("old-source.xlsx", prompt)
            self.assertIn(f"message_id={uploaded_message.id}", prompt)
            self.assertIn(f"attachment_id={attachment.id}", prompt)
            self.assertIn("do not ask the user to upload it again", prompt)
            self.assertNotIn("base64", prompt.casefold())

    def test_explicit_historical_filename_overrides_latest_upload(self):
        """确认用户明确指定旧附件时优先使用该历史文件。"""
        thread = self._unbound_thread()
        old_message, old_attachment = self._post_upload(
            thread, "historical-source.xlsx", "Original upload."
        )
        latest_message, latest_attachment = self._post_upload(
            thread, "latest-source.xlsx", "Newer upload."
        )
        for index in range(105):
            thread.message_post(
                body=f"Follow-up message {index}",
                llm_role="user",
                author_id=self.env.user.partner_id.id,
            )
        request = thread.message_post(
            body="Use historical-source.xlsx for this edit, not the newer file.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )

        with patch.object(NativeThread, "generate", autospec=True, return_value=iter(())):
            list(thread.generate(request.body, attachment_ids=[]))

        found_message, found_attachment = thread._office_latest_upload()
        self.assertEqual(found_message, old_message)
        self.assertEqual(found_attachment, old_attachment)
        kwargs = thread._prepare_chat_kwargs(thread.get_llm_messages(), use_streaming=False)
        prompt = "\n".join(
            item.get("content", "")
            for item in kwargs["prepend_messages"]
            if item.get("role") == "system"
        )
        self.assertIn("Latest available attachment", prompt)
        self.assertIn("latest-source.xlsx", prompt)
        self.assertIn(f"message_id={latest_message.id}", prompt)
        self.assertIn(f"attachment_id={latest_attachment.id}", prompt)
        self.assertIn("User-selected historical attachment", prompt)
        self.assertIn("historical-source.xlsx", prompt)

    def test_silent_retrieval_messages_remain_in_provider_context(self):
        """确认静默只影响用户可见性，不会从后续 Provider 上下文删除工具记录。"""
        thread = self._thread()
        thread.message_post(
            body="Create an Excel workbook from Odoo records.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        assistant = thread.message_post(
            body="",
            body_json={"tool_calls": [self._retriever_call("call-context-check")]},
            llm_role="assistant",
            author_id=False,
        )
        tool_message = thread.message_post(
            body="Retriever result retained for the next model turn.",
            body_json={
                "type": "tool_execution",
                "tool_name": "odoo_record_retriever",
                "status": "requested",
            },
            llm_role="tool",
            author_id=False,
        )

        self.assertTrue(assistant.llm_silent_retrieval)
        self.assertTrue(tool_message.llm_silent_retrieval)
        context = thread.get_llm_messages()
        self.assertIn(assistant, context)
        self.assertIn(tool_message, context)

    def test_retriever_error_stays_internal_and_final_failure_is_visible(self):
        """确认错误回执留在上下文，最终 assistant 失败说明仍对用户可见。"""
        thread = self._thread()
        call = self._retriever_call("call-will-fail")
        assistant = thread.message_post(
            body="",
            body_json={"tool_calls": [call]},
            llm_role="assistant",
            author_id=False,
        )
        tool_message = self.env["mail.message"].post_tool_call(call, thread_model=thread)
        self.assertTrue(assistant.llm_silent_retrieval)
        self.assertTrue(tool_message.llm_silent_retrieval)

        with patch.object(
            type(tool_message),
            "_execute_tool_with_context",
            side_effect=UserError("ACCESS_DENIED: synthetic denial"),
        ):
            internal_events = list(tool_message.execute_tool_call(thread_model=thread))

        self.assertEqual(tool_message.get_tool_data()["status"], "error")
        self.assertEqual(tool_message.get_tool_data()["error_code"], "ACCESS_DENIED")
        self.assertTrue(tool_message.llm_silent_retrieval)
        self.assertTrue(assistant.llm_silent_retrieval)
        self.assertTrue(any(event["type"] == "tool_failed" for event in internal_events))
        self.assertTrue(
            all(event["type"] not in {"message_create", "message_update"} for event in
                thread._office_m3_filter_silent_events(internal_events))
        )
        context = thread.get_llm_messages()
        self.assertIn(assistant, context)
        self.assertIn(tool_message, context)

        final_failure = thread.message_post(
            body="当前用户无权读取这些记录，因此本次任务未完成。",
            llm_role="assistant",
            author_id=False,
            is_error=True,
        )
        history = self.env["mail.message"]._message_fetch(
            [("model", "=", "llm.thread"), ("res_id", "=", thread.id)],
            limit=100,
        )["messages"]
        self.assertNotIn(assistant, history)
        self.assertNotIn(tool_message, history)
        self.assertIn(final_failure, history)

    def test_visible_office_and_clarification_messages_are_never_marked(self):
        """确认 Office 操作、澄清问题和用户确认始终保持可见。"""
        thread = self._thread()
        for body, body_json, is_error in (
            ("Please confirm which records.", None, False),
            ("Candidate is ready for confirmation.", None, False),
            ("Provider failed.", None, True),
            (
                "Executing office",
                {"type": "tool_execution", "tool_name": "office", "status": "requested"},
                False,
            ),
        ):
            message = thread.message_post(
                body=body,
                body_json=body_json,
                llm_role="assistant" if body_json is None else "tool",
                author_id=False,
                is_error=is_error,
            )
            self.assertFalse(message.llm_silent_retrieval)
