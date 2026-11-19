"""CC-M3-03 visibility and audit-boundary tests."""

from unittest.mock import patch
from uuid import uuid4

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from odoo.addons.llm_thread.models.llm_thread import LLMThread as NativeThread
from odoo.addons.office_engine_m2.tests.support import (
    XLSX_MIMETYPE,
    WorkbookVersionFixtures,
    synthetic_xlsx,
)


class TestSilentRetrieval(WorkbookVersionFixtures, TransactionCase):
    @classmethod
    def setUpClass(cls):
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
        self.assertIn("source_query (model, domain, fields, order)", system_text)
        self.assertIn("tables (the requested output columns)", system_text)
        self.assertIn("add a separate output table whose source is that collection's key", system_text)
        self.assertIn("never use dotted relation paths as table source fields", system_text)
        self.assertIn("do not add raw IDs, duplicate fields, or generic display_name columns", system_text)
        self.assertIn("Internal identity columns are added by the Collector", system_text)
        self.assertNotIn("world.depot.outbound.order", system_text)

    def test_new_fileless_export_is_filtered_before_m2_binds_tools(self):
        thread = self._unbound_thread()
        request = "Export all requested Odoo records to Excel."

        self.assertFalse(thread.tool_ids)
        self.assertFalse(thread._office_m3_is_non_streaming_office_route())
        self.assertTrue(thread._office_m3_is_non_streaming_office_generation(request, []))
        self.assertFalse(thread._office_m3_is_non_streaming_office_generation("Find one record", []))

    def test_chinese_organize_into_excel_request_binds_m3_export_tools_without_upload(self):
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

    def test_failed_retrieval_reveals_tool_and_assistant_messages(self):
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
            events = list(tool_message.execute_tool_call(thread_model=thread))

        self.assertEqual(tool_message.get_tool_data()["status"], "error")
        self.assertFalse(tool_message.llm_silent_retrieval)
        self.assertFalse(assistant.llm_silent_retrieval)
        surfaced = [
            event["message"]["id"]
            for event in events
            if event.get("type") == "message_create"
        ]
        self.assertEqual(set(surfaced), {assistant.id, tool_message.id})
        history = self.env["mail.message"]._message_fetch(
            [("model", "=", "llm.thread"), ("res_id", "=", thread.id)],
            limit=100,
        )["messages"]
        self.assertIn(assistant, history)
        self.assertIn(tool_message, history)

    def test_visible_office_and_clarification_messages_are_never_marked(self):
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
