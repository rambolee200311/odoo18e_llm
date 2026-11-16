"""Deterministic collection, handoff, Candidate and lifecycle integration tests."""

import hashlib
import json
import re
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from odoo.tests import TransactionCase

from odoo.addons.office_engine_m2.services.edit_orchestrator import dispatch_office_action
from odoo.addons.office_engine_m2.tests.support import WorkbookVersionFixtures

from ..services.dataset_collector import _read_pages, collect_export_dataset
from ..services.export_verification import verify_export_workbook


MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class _HostedCIFixtureAdapter:
    def __init__(self, *, root_parent_identity=False, root_parent_value=None):
        self.calls = []
        self.root_parent_identity = root_parent_identity
        self.root_parent_value = root_parent_value

    def execute(self, **kwargs):
        self.calls.append(kwargs)
        self.asserted = True
        match = re.search(r"<office_export_handoff>(.*?)</office_export_handoff>", kwargs["instruction"], re.S)
        envelope = json.loads(match.group(1))
        payload = envelope["dataset"]
        workbook = Workbook()
        workbook.remove(workbook.active)
        for table in payload["tables"]:
            sheet = workbook.create_sheet(table["name"])
            labels = [column["label"] for column in table["columns"]]
            identity_headers = (["__office_parent_id", "__office_record_id"] if self.root_parent_identity else [
                "__office_record_id"
            ]) if table["source"] == "root" else [
                "__office_parent_id", "__office_record_id"
            ]
            sheet.append(labels + identity_headers)
            if table["source"] == "root":
                records = payload["root"]["records"]
                pairs = [(False, row["id"], row) for row in records]
            else:
                relation = payload["relations"][table["source"]]
                by_id = {row["id"]: row for row in relation["records"]}
                pairs = [(parent_id, record_id, by_id[record_id]) for parent_id, record_id in relation["pairs"]]
            for parent_id, record_id, record in pairs:
                visible = [record.get(column["source_field"]) for column in table["columns"]]
                if table["source"] == "root":
                    sheet.append(visible + ([self.root_parent_value, record_id] if self.root_parent_identity else [record_id]))
                else:
                    sheet.append(visible + [parent_id, record_id])
            for index in range(len(labels) + 1, len(labels) + len(identity_headers) + 1):
                sheet.column_dimensions[get_column_letter(index)].hidden = True
        stream = BytesIO()
        workbook.save(stream)
        workbook.close()
        content = stream.getvalue()
        return SimpleNamespace(
            operation_status="candidate_received",
            candidate_bytes=content,
            candidate_sha256=hashlib.sha256(content).hexdigest(),
            input_sha256=kwargs.get("input_sha256"),
            provider_response_id="synthetic-response",
            request_id="synthetic-request",
            tool_call_ids=("synthetic-tool-call",),
            provider_file_ids=("synthetic-file",),
            provider_filename="export.xlsx",
            usage={"input_tokens": 100, "output_tokens": 50},
            duration_ms=25,
            cleanup_state="completed",
            error=None,
            to_dict=lambda: {"operation_status": "candidate_received", "candidate_present": True},
        )


class TestM3Export(WorkbookVersionFixtures, TransactionCase):
    def _owner_env(self):
        return self.env(user=self.owner.id, context={"allowed_company_ids": [self.owner.company_id.id]})

    def _make_thread(self, env):
        return env["llm.thread"].create({
            "name": "M3 export " + uuid4().hex,
            "provider_id": self.provider.id,
            "model_id": self.model.id,
        })

    def _user(self, thread, text):
        return thread.message_post(body=text, llm_role="user", author_id=thread.env.user.partner_id.id)

    def _tool(self, thread):
        return thread.message_post(
            body="office",
            llm_role="tool",
            author_id=False,
            body_json={"type": "tool_execution", "tool_name": "office", "status": "completed"},
        )

    def _store_result(self, tool_message, result):
        tool_message.write({"body_json": {
            "type": "tool_execution",
            "tool_name": "office",
            "status": "completed",
            "result": result,
        }})

    @staticmethod
    def _root_plan(record_ids, *, page_size=100):
        return {
            "source_query": {
                "model": "res.partner",
                "domain": [["id", "in", record_ids]],
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
            "page_size": page_size,
        }

    def test_existing_office_tool_schema_adds_export_records(self):
        office_tools = self.env["llm.tool"].search([("name", "=", "office")])
        self.assertEqual(len(office_tools), 1)
        schema = office_tools.get_input_schema()
        self.assertEqual(
            schema["properties"]["action"]["enum"],
            ["status", "create", "edit", "accept", "reject", "finalize", "export_records"],
        )
        for name in ("workbook_source", "source_query", "collections", "tables", "verification_profile"):
            self.assertIn(name, schema["properties"])
            self.assertIn(name, schema["required"])

    def test_paging_count_drift_and_duplicate_identity_are_rejected(self):
        from odoo.exceptions import ValidationError

        class _PagedModel:
            def __init__(self, pages):
                self.pages = pages

            def search_count(self, domain):
                return 3

            def search_read(self, domain, *, fields, limit, offset, order):
                return self.pages.get(offset, [])

        cases = [
            (
                _PagedModel({0: [{"id": 1}, {"id": 2}], 2: []}),
                "no progress",
            ),
            (
                _PagedModel({0: [{"id": 1}, {"id": 2}], 2: [{"id": 2}, {"id": 3}]}),
                "missing or duplicate record identity",
            ),
        ]
        for model, error in cases:
            with self.subTest(error=error), self.assertRaisesRegex(ValidationError, error):
                _read_pages(model, [], ["name"], "id asc", page_size=2, max_rows=10)

    def test_148_records_are_collected_as_100_plus_48(self):
        records = self.env["res.partner"].create([
            {"name": f"M3 synthetic partner {index:03d}", "email": f"m3-{uuid4().hex}@example.invalid"}
            for index in range(148)
        ])
        plan = self._root_plan(records.ids)
        collected = collect_export_dataset(
            self.env,
            plan["source_query"],
            plan["collections"],
            plan["tables"],
            plan["verification_profile"],
            page_size=100,
        )
        self.assertEqual(collected["root_count"], 148)
        self.assertEqual(collected["root_page_count"], 2)
        self.assertEqual([len(collected["dataset"]["root"]["records"][:100]), len(collected["dataset"]["root"]["records"][100:])], [100, 48])
        self.assertEqual(len({row["id"] for row in collected["dataset"]["root"]["records"]}), 148)
        self.assertEqual(len(collected["handoff_sha256"]), 64)
        self.assertEqual(collected["source_view"], "single_odoo_transaction")
        self.assertEqual(collected["read_consistency"], "repeatable_read")
        self.assertLessEqual(collected["collection_started_at"], collected["collection_completed_at"])
        self.assertEqual(len(collected["security_scope_sha256"]), 64)

    def test_larger_bounded_dataset_spans_more_than_two_pages(self):
        records = self.env["res.partner"].create([
            {"name": f"M3 larger synthetic partner {index:03d} {uuid4().hex[:8]}"}
            for index in range(251)
        ])
        plan = self._root_plan(records.ids)
        collected = collect_export_dataset(
            self.env, plan["source_query"], plan["collections"], plan["tables"],
            plan["verification_profile"], page_size=100,
        )
        identities = [row["id"] for row in collected["dataset"]["root"]["records"]]
        self.assertEqual(collected["root_count"], 251)
        self.assertEqual(collected["root_page_count"], 3)
        self.assertEqual(len(identities), 251)
        self.assertEqual(len(set(identities)), 251)

    def test_many2many_and_one2many_relations_are_batch_collected_with_parent_pairs(self):
        env = self._owner_env()
        category_model = self.env["res.partner.category"]
        categories = category_model.create([{"name": "M3 Cat A " + uuid4().hex}, {"name": "M3 Cat B " + uuid4().hex}])
        parents = self.env["res.partner"].create([
            {"name": "M3 Parent A " + uuid4().hex},
            {"name": "M3 Parent B " + uuid4().hex},
        ])
        parents[0].write({"category_id": [(6, 0, categories.ids)]})
        parents[1].write({"category_id": [(6, 0, categories[:1].ids)]})
        parents.write({"user_id": self.owner.id})
        children = self.env["res.partner"].create([
            {"name": "M3 Child " + uuid4().hex, "parent_id": parents[0].id},
        ])
        source_query = {
            "model": "res.partner",
            "domain": [["id", "in", parents.ids]],
            "fields": ["name"],
            "order": "id asc",
        }
        collections = [
            {
                "key": "categories",
                "relation_field": "category_id",
                "relation_model": "res.partner.category",
                "inverse_field": None,
                "fields": ["name"],
                "order": "id asc",
            },
            {
                "key": "children",
                "relation_field": "child_ids",
                "relation_model": "res.partner",
                "inverse_field": "parent_id",
                "fields": ["name"],
                "order": "id asc",
            },
            {
                "key": "salesperson",
                "relation_field": "user_id",
                "relation_model": "res.users",
                "inverse_field": None,
                "fields": ["name"],
                "order": "id asc",
            },
        ]
        tables = [
            {"name": "Parents", "source": "root", "columns": [{"label": "Name", "source_field": "name"}]},
            {"name": "Categories", "source": "categories", "columns": [{"label": "Name", "source_field": "name"}]},
            {"name": "Children", "source": "children", "columns": [{"label": "Name", "source_field": "name"}]},
            {"name": "Salespersons", "source": "salesperson", "columns": [{"label": "Name", "source_field": "name"}]},
        ]
        collected = collect_export_dataset(env, source_query, collections, tables, "record_projection", page_size=2)
        self.assertEqual(collected["relation_pair_count"], 6)
        self.assertEqual(
            {tuple(pair) for pair in collected["dataset"]["relations"]["categories"]["pairs"]},
            {(parents[0].id, categories[0].id), (parents[0].id, categories[1].id), (parents[1].id, categories[0].id)},
        )
        self.assertEqual(collected["dataset"]["relations"]["children"]["pairs"], [[parents[0].id, children.id]])
        self.assertEqual(
            collected["dataset"]["relations"]["salesperson"]["pairs"],
            [[parents[0].id, self.owner.id], [parents[1].id, self.owner.id]],
        )

    def test_new_export_candidate_waits_for_accept_then_finalize(self):
        partners = self.env["res.partner"].create([
            {"name": f"M3 lifecycle partner {index:03d}", "email": f"m3-life-{uuid4().hex}@example.invalid"}
            for index in range(148)
        ])
        env = self._owner_env()
        thread = self._make_thread(env)
        intent = self._user(thread, "Export all 148 synthetic partners with their names and emails.")
        tool_message = self._tool(thread)
        plan = self._root_plan(partners.ids)
        adapter = _HostedCIFixtureAdapter()
        office_tool = env["llm.tool"].search([("name", "=", "office")], limit=1)
        with patch(
            "odoo.addons.office_engine_m3.services.export_orchestrator._provider_dependencies",
            return_value=(adapter, object(), "synthetic-route-b", SimpleNamespace()),
        ):
            result = office_tool.with_context(message=tool_message).execute({
                "action": "export_records",
                "candidate_version_id": None,
                "confirmation_required": None,
                "confirmation_reason": None,
                "workbook_source": "new",
                "source_query": plan["source_query"],
                "collections": plan["collections"],
                "tables": plan["tables"],
                "verification_profile": plan["verification_profile"],
            })
        self._store_result(tool_message, result)
        session = env["office.mapping.session"].search([("thread_id", "=", thread.id)], limit=1)
        candidate = env["office.workbook.version"].browse(result["candidate_version_id"])
        self.assertEqual(result["operation_status"], "candidate_review_required", result)
        self.assertEqual(result["workbook_source"], "new")
        self.assertEqual(result["source_record_count"], 148)
        self.assertEqual(result["projection_verification"]["projected_rows"], 148)
        self.assertFalse(session.current_version_id)
        self.assertFalse(session.last_valid_version_id)
        self.assertEqual(session.document_revision, 0)
        self.assertEqual(candidate.state, "partially_verified")
        self.assertFalse(candidate.input_attachment_id)
        self.assertFalse(candidate.input_sha256)
        self.assertEqual(candidate.intent_message_id, intent)
        receipt = json.loads(candidate.data_integrity_receipt_json)
        self.assertEqual(receipt["schema_version"], "office.data-handoff-receipt.v3")
        self.assertEqual(receipt["source"]["kind"], "new")
        self.assertEqual(receipt["source"]["root_count"], 148)
        self.assertEqual(receipt["source"]["collected_count"], 148)
        self.assertEqual(receipt["workbook"]["expected_records"], 148)
        self.assertEqual(receipt["workbook"]["matched_records"], 148)
        self.assertEqual(receipt["output_sha256"], candidate.output_sha256)
        self.assertEqual(receipt["freshness"], {"checked_at_collection": True, "requeried_before_accept": False})
        self.assertEqual(receipt["collection_window"]["source_view"], "single_odoo_transaction")
        self.assertEqual(receipt["handoff"]["profile"], "hosted_ci_instruction_json_v1")
        self.assertEqual(adapter.calls[0]["operation"], "edit")
        envelope = json.loads(re.search(
            r"<office_export_handoff>(.*?)</office_export_handoff>", adapter.calls[0]["instruction"], re.S
        ).group(1))
        self.assertEqual(envelope["carrier_sha256"], hashlib.sha256(adapter.calls[0]["input_xlsx"]).hexdigest())
        self.assertEqual(receipt["handoff"]["provider_input_sha256"], envelope["carrier_sha256"])
        self.assertEqual(result["provider_input_sha256"], envelope["carrier_sha256"])
        carrier = load_workbook(BytesIO(adapter.calls[0]["input_xlsx"]), read_only=True)
        self.assertEqual(carrier.sheetnames, ["Sheet1"])
        self.assertIsNone(next(carrier["Sheet1"].iter_rows(values_only=True), None))
        carrier.close()

        accept_intent = self._user(thread, "接受")
        accept_tool = self._tool(thread)
        accepted = dispatch_office_action(
            env, thread, accept_tool, "accept", candidate_version_id=candidate.id
        )
        self._store_result(accept_tool, accepted)
        session.invalidate_recordset()
        candidate.invalidate_recordset()
        self.assertEqual(accepted["operation_status"], "accepted_current", accepted)
        self.assertEqual(candidate.state, "accepted_current")
        self.assertEqual(session.current_version_id, candidate)
        self.assertEqual(session.last_valid_version_id, candidate)
        self.assertEqual(candidate.acceptance_authorization_message_id, accept_intent)
        self.assertEqual(session.document_revision, 1)
        self._user(thread, "交付最终文件")
        finalize_tool = self._tool(thread)
        finalized = dispatch_office_action(env, thread, finalize_tool, "finalize")
        session.invalidate_recordset()
        candidate.invalidate_recordset()
        self.assertEqual(finalized["operation_status"], "finalized", finalized)
        self.assertEqual(candidate.state, "finalized")
        self.assertEqual(candidate.final_attachment_id, candidate.output_attachment_id)
        self.assertEqual(hashlib.sha256(candidate.final_attachment_id.raw).hexdigest(), candidate.output_sha256)
        self.assertEqual(session.current_version_id, candidate)
        self.assertEqual(session.last_valid_version_id, candidate)
        self.assertEqual(session.document_revision, 1)

    def test_current_export_uses_m2_edit_candidate_and_keeps_current_until_accept(self):
        env, session, thread, _source_message, _source, _request, _output, parent = self._versioned_session_fixture()
        partners = self.env["res.partner"].create([
            {"name": f"M3 current export contact {i:03d} {uuid4().hex[:8]}", "email": f"m3-cur-{uuid4().hex}@example.invalid"}
            for i in range(3)
        ])
        self._user(thread, "Add all three synthetic contacts to the current workbook.")
        tool_message = self._tool(thread)
        plan = self._root_plan(partners.ids)
        adapter = _HostedCIFixtureAdapter()
        office_tool = env["llm.tool"].search([("name", "=", "office")], limit=1)
        with patch(
            "odoo.addons.office_engine_m3.services.export_orchestrator._provider_dependencies",
            return_value=(adapter, object(), "synthetic-route-b", SimpleNamespace()),
        ):
            result = office_tool.with_context(message=tool_message).execute({
                "action": "export_records",
                "candidate_version_id": None,
                "confirmation_required": None,
                "confirmation_reason": None,
                "workbook_source": "current",
                "source_query": plan["source_query"],
                "collections": plan["collections"],
                "tables": plan["tables"],
                "verification_profile": plan["verification_profile"],
            })
        self._store_result(tool_message, result)
        session.invalidate_recordset()
        candidate = env["office.workbook.version"].browse(result["candidate_version_id"])
        self.assertEqual(result["operation_status"], "candidate_review_required", result)
        self.assertEqual(candidate.version_kind, "edit")
        self.assertEqual(candidate.parent_version_id, parent)
        self.assertEqual(candidate.input_attachment_id, parent.output_attachment_id)
        self.assertEqual(candidate.input_sha256, parent.output_sha256)
        receipt = json.loads(candidate.data_integrity_receipt_json)
        self.assertEqual(receipt["source"]["kind"], "current")
        self.assertEqual(receipt["handoff"]["provider_input_sha256"], parent.output_sha256)
        self.assertEqual(session.current_version_id, parent)
        self.assertEqual(session.document_revision, 1)

        self._user(thread, "接受")
        accept_tool = self._tool(thread)
        accepted = dispatch_office_action(
            env, thread, accept_tool, "accept", candidate_version_id=candidate.id
        )
        self._store_result(accept_tool, accepted)
        session.invalidate_recordset()
        candidate.invalidate_recordset()
        self.assertEqual(accepted["operation_status"], "accepted_current", accepted)
        self.assertEqual(session.current_version_id, candidate)
        self.assertEqual(session.document_revision, 2)
        self._user(thread, "交付最终文件")
        finalize_tool = self._tool(thread)
        finalized = dispatch_office_action(env, thread, finalize_tool, "finalize")
        session.invalidate_recordset()
        candidate.invalidate_recordset()
        self.assertEqual(finalized["operation_status"], "finalized", finalized)
        self.assertEqual(candidate.state, "finalized")
        self.assertEqual(candidate.final_attachment_id, candidate.output_attachment_id)
        self.assertEqual(hashlib.sha256(candidate.final_attachment_id.raw).hexdigest(), candidate.output_sha256)
        self.assertEqual(session.current_version_id, candidate)
        self.assertEqual(session.last_valid_version_id, candidate)
        self.assertEqual(session.document_revision, 2)

    def test_reject_new_export_candidate_keeps_session_unmodified(self):
        partner = self.env["res.partner"].create({
            "name": "M3 rejected export contact " + uuid4().hex,
            "email": f"m3-reject-{uuid4().hex}@example.invalid",
        })
        env = self._owner_env()
        thread = self._make_thread(env)
        self._user(thread, "Export the synthetic contact.")
        tool_message = self._tool(thread)
        plan = self._root_plan([partner.id])
        adapter = _HostedCIFixtureAdapter()
        office_tool = env["llm.tool"].search([("name", "=", "office")], limit=1)
        with patch(
            "odoo.addons.office_engine_m3.services.export_orchestrator._provider_dependencies",
            return_value=(adapter, object(), "synthetic-route-b", SimpleNamespace()),
        ):
            result = office_tool.with_context(message=tool_message).execute({
                "action": "export_records",
                "candidate_version_id": None,
                "confirmation_required": None,
                "confirmation_reason": None,
                "workbook_source": "new",
                "source_query": plan["source_query"],
                "collections": plan["collections"],
                "tables": plan["tables"],
                "verification_profile": plan["verification_profile"],
            })
        self._store_result(tool_message, result)
        session = env["office.mapping.session"].search([("thread_id", "=", thread.id)], limit=1)
        candidate = env["office.workbook.version"].browse(result["candidate_version_id"])
        self.assertEqual(result["operation_status"], "candidate_review_required", result)
        self.assertEqual(candidate.state, "partially_verified")
        before = (session.current_version_id.id, session.last_valid_version_id.id, session.document_revision)
        self.assertEqual(before, (False, False, 0))

        self._user(thread, "拒绝")
        reject_tool = self._tool(thread)
        rejected = dispatch_office_action(
            env, thread, reject_tool, "reject", candidate_version_id=candidate.id
        )
        self._store_result(reject_tool, rejected)
        session.invalidate_recordset()
        candidate.invalidate_recordset()
        self.assertEqual(rejected["operation_status"], "candidate_rejected", rejected)
        self.assertEqual(candidate.state, "rejected")
        self.assertEqual(
            (session.current_version_id.id, session.last_valid_version_id.id, session.document_revision),
            before,
        )

    def test_resource_limit_fails_before_session_or_provider_dispatch(self):
        partners = self.env["res.partner"].create([
            {"name": "M3 over-limit " + uuid4().hex},
            {"name": "M3 over-limit " + uuid4().hex},
        ])
        env = self._owner_env()
        thread = self._make_thread(env)
        self._user(thread, "Export the bounded synthetic contacts.")
        tool_message = self._tool(thread)
        plan = self._root_plan(partners.ids)
        adapter = _HostedCIFixtureAdapter()
        office_tool = env["llm.tool"].search([("name", "=", "office")], limit=1)
        with (
            patch("odoo.addons.office_engine_m3.services.dataset_collector._MAX_ROOT_ROWS", 1),
            patch(
                "odoo.addons.office_engine_m3.services.export_orchestrator._provider_dependencies",
                return_value=(adapter, object(), "synthetic-route-b", SimpleNamespace()),
            ),
        ):
            result = office_tool.with_context(message=tool_message).execute({
                "action": "export_records",
                "candidate_version_id": None,
                "confirmation_required": None,
                "confirmation_reason": None,
                "workbook_source": "new",
                "source_query": plan["source_query"],
                "collections": plan["collections"],
                "tables": plan["tables"],
                "verification_profile": plan["verification_profile"],
            })
        self.assertEqual(result["operation_status"], "export_rejected", result)
        self.assertFalse(adapter.calls)
        self.assertFalse(env["office.mapping.session"].search([("thread_id", "=", thread.id)]))

        byte_thread = self._make_thread(env)
        self._user(byte_thread, "Export the contacts within the payload budget.")
        byte_tool_message = self._tool(byte_thread)
        byte_adapter = _HostedCIFixtureAdapter()
        with (
            patch("odoo.addons.office_engine_m3.services.dataset_collector._MAX_HANDOFF_BYTES", 1),
            patch(
                "odoo.addons.office_engine_m3.services.export_orchestrator._provider_dependencies",
                return_value=(byte_adapter, object(), "synthetic-route-b", SimpleNamespace()),
            ),
        ):
            byte_result = office_tool.with_context(message=byte_tool_message).execute({
                "action": "export_records",
                "candidate_version_id": None,
                "confirmation_required": None,
                "confirmation_reason": None,
                "workbook_source": "new",
                "source_query": plan["source_query"],
                "collections": plan["collections"],
                "tables": plan["tables"],
                "verification_profile": plan["verification_profile"],
            })
        self.assertEqual(byte_result["operation_status"], "export_rejected", byte_result)
        self.assertFalse(byte_adapter.calls)
        self.assertFalse(env["office.mapping.session"].search([("thread_id", "=", byte_thread.id)]))

    def test_query_page_failure_is_reported_without_candidate_creation(self):
        from odoo.exceptions import ValidationError

        partner = self.env["res.partner"].create({"name": "M3 query failure " + uuid4().hex})
        env = self._owner_env()
        thread = self._make_thread(env)
        self._user(thread, "Export the synthetic contact.")
        tool_message = self._tool(thread)
        plan = self._root_plan([partner.id])
        adapter = _HostedCIFixtureAdapter()
        office_tool = env["llm.tool"].search([("name", "=", "office")], limit=1)
        with (
            patch("odoo.addons.office_engine_m3.services.dataset_collector._read_pages", side_effect=ValidationError("Synthetic page failure")),
            patch(
                "odoo.addons.office_engine_m3.services.export_orchestrator._provider_dependencies",
                return_value=(adapter, object(), "synthetic-route-b", SimpleNamespace()),
            ),
        ):
            result = office_tool.with_context(message=tool_message).execute({
                "action": "export_records",
                "candidate_version_id": None,
                "confirmation_required": None,
                "confirmation_reason": None,
                "workbook_source": "new",
                "source_query": plan["source_query"],
                "collections": plan["collections"],
                "tables": plan["tables"],
                "verification_profile": plan["verification_profile"],
            })
        self.assertEqual(result["operation_status"], "export_rejected", result)
        self.assertFalse(adapter.calls)
        self.assertFalse(env["office.mapping.session"].search([("thread_id", "=", thread.id)]))

    def test_relation_row_limit_fails_before_provider_dispatch(self):
        categories = self.env["res.partner.category"].create([
            {"name": "M3 relation cap A " + uuid4().hex},
            {"name": "M3 relation cap B " + uuid4().hex},
        ])
        partners = self.env["res.partner"].create([
            {"name": "M3 relation cap parent A " + uuid4().hex},
            {"name": "M3 relation cap parent B " + uuid4().hex},
        ])
        partners[0].write({"category_id": [(6, 0, categories.ids)]})
        partners[1].write({"category_id": [(6, 0, categories[:1].ids)]})
        source_query = {
            "model": "res.partner",
            "domain": [["id", "in", partners.ids]],
            "fields": ["name"],
            "order": "id asc",
        }
        collections = [{
            "key": "categories",
            "relation_field": "category_id",
            "relation_model": "res.partner.category",
            "inverse_field": None,
            "fields": ["name"],
            "order": "id asc",
        }]
        tables = [
            {"name": "Parents", "source": "root", "columns": [{"label": "Name", "source_field": "name"}]},
            {"name": "Categories", "source": "categories", "columns": [{"label": "Name", "source_field": "name"}]},
        ]
        env = self._owner_env()
        thread = self._make_thread(env)
        self._user(thread, "Export the synthetic parents and related categories.")
        tool_message = self._tool(thread)
        adapter = _HostedCIFixtureAdapter()
        office_tool = env["llm.tool"].search([("name", "=", "office")], limit=1)
        with (
            patch("odoo.addons.office_engine_m3.services.dataset_collector._MAX_RELATION_ROWS", 1),
            patch(
                "odoo.addons.office_engine_m3.services.export_orchestrator._provider_dependencies",
                return_value=(adapter, object(), "synthetic-route-b", SimpleNamespace()),
            ),
        ):
            result = office_tool.with_context(message=tool_message).execute({
                "action": "export_records",
                "candidate_version_id": None,
                "confirmation_required": None,
                "confirmation_reason": None,
                "workbook_source": "new",
                "source_query": source_query,
                "collections": collections,
                "tables": tables,
                "verification_profile": "record_projection",
            })
        self.assertEqual(result["operation_status"], "export_rejected", result)
        self.assertFalse(adapter.calls)
        self.assertFalse(env["office.mapping.session"].search([("thread_id", "=", thread.id)]))

    def test_indeterminate_provider_attempt_is_not_silently_replayed(self):
        partner = self.env["res.partner"].create({"name": "M3 indeterminate provider " + uuid4().hex})
        env = self._owner_env()
        thread = self._make_thread(env)
        self._user(thread, "Export the synthetic contact.")
        plan = self._root_plan([partner.id])

        class _IndeterminateAdapter:
            def __init__(self):
                self.calls = []

            def execute(self, **kwargs):
                self.calls.append(kwargs)
                result = SimpleNamespace(
                    operation_status="indeterminate",
                    candidate_bytes=None,
                    error=SimpleNamespace(category="provider_connection_or_timeout", retry_decision="not_automatic"),
                    to_dict=lambda: {"operation_status": "indeterminate", "candidate_present": False},
                )
                return result

        adapter = _IndeterminateAdapter()
        office_tool = env["llm.tool"].search([("name", "=", "office")], limit=1)
        with patch(
            "odoo.addons.office_engine_m3.services.export_orchestrator._provider_dependencies",
            return_value=(adapter, object(), "synthetic-route-b", SimpleNamespace()),
        ):
            first_tool_message = self._tool(thread)
            first = office_tool.with_context(message=first_tool_message).execute({
                "action": "export_records",
                "candidate_version_id": None,
                "confirmation_required": None,
                "confirmation_reason": None,
                "workbook_source": "new",
                "source_query": plan["source_query"],
                "collections": plan["collections"],
                "tables": plan["tables"],
                "verification_profile": plan["verification_profile"],
            })
            second_tool_message = self._tool(thread)
            second = office_tool.with_context(message=second_tool_message).execute({
                "action": "export_records",
                "candidate_version_id": None,
                "confirmation_required": None,
                "confirmation_reason": None,
                "workbook_source": "new",
                "source_query": plan["source_query"],
                "collections": plan["collections"],
                "tables": plan["tables"],
                "verification_profile": plan["verification_profile"],
            })
        self.assertEqual(first["operation_status"], "provider_export_unavailable", first)
        self.assertEqual(second["operation_status"], "provider_outcome_unknown", second)
        self.assertEqual(len(adapter.calls), 1)
        session = env["office.mapping.session"].search([("thread_id", "=", thread.id)], limit=1)
        version = env["office.workbook.version"].search([("session_id", "=", session.id)], limit=1)
        self.assertEqual(version.state, "verifying")
        self.assertFalse(session.current_version_id)
        self.assertFalse(session.last_valid_version_id)
        self.assertEqual(session.document_revision, 0)

    def test_invalid_provider_projection_is_failed_without_advancing_current(self):
        partner = self.env["res.partner"].create({"name": "M3 invalid projection " + uuid4().hex})
        env = self._owner_env()
        thread = self._make_thread(env)
        self._user(thread, "Export the synthetic contact.")
        tool_message = self._tool(thread)
        plan = self._root_plan([partner.id])
        adapter = _HostedCIFixtureAdapter(root_parent_identity=True, root_parent_value=partner.id)
        office_tool = env["llm.tool"].search([("name", "=", "office")], limit=1)
        with patch(
            "odoo.addons.office_engine_m3.services.export_orchestrator._provider_dependencies",
            return_value=(adapter, object(), "synthetic-route-b", SimpleNamespace()),
        ):
            result = office_tool.with_context(message=tool_message).execute({
                "action": "export_records",
                "candidate_version_id": None,
                "confirmation_required": None,
                "confirmation_reason": None,
                "workbook_source": "new",
                "source_query": plan["source_query"],
                "collections": plan["collections"],
                "tables": plan["tables"],
                "verification_profile": plan["verification_profile"],
            })
        self.assertEqual(result["operation_status"], "export_integrity_failed", result)
        self.assertEqual(len(adapter.calls), 1)
        candidate = env["office.workbook.version"].browse(result["version_id"])
        session = candidate.session_id
        self.assertEqual(candidate.state, "failed")
        self.assertFalse(session.current_version_id)
        self.assertFalse(session.last_valid_version_id)
        self.assertEqual(session.document_revision, 0)

    def test_projection_verifier_rejects_missing_or_duplicate_identity(self):
        records = self.env["res.partner"].create([
            {"name": "M3 verify A " + uuid4().hex},
            {"name": "M3 verify B " + uuid4().hex},
        ])
        plan = self._root_plan(records.ids)
        collected = collect_export_dataset(
            self.env, plan["source_query"], plan["collections"], plan["tables"], plan["verification_profile"]
        )
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Records"
        sheet.append(["Name", "Email", "__office_record_id"])
        for row in collected["dataset"]["root"]["records"]:
            sheet.append([row["name"], row["email"], row["id"]])
        sheet.append([collected["dataset"]["root"]["records"][0]["name"], None, records[0].id])
        stream = BytesIO()
        workbook.save(stream)
        workbook.close()
        with self.assertRaisesRegex(Exception, "missing or extra data row"):
            verify_export_workbook(stream.getvalue(), "candidate.xlsx", collected)

    def test_projection_verifier_accepts_blank_auxiliary_columns_without_weakening_data_checks(self):
        records = self.env["res.partner"].create([
            {"name": "M3 aux-column A " + uuid4().hex, "email": f"aux-a-{uuid4().hex}@example.invalid"},
            {"name": "M3 aux-column B " + uuid4().hex, "email": f"aux-b-{uuid4().hex}@example.invalid"},
        ])
        plan = self._root_plan(records.ids)
        collected = collect_export_dataset(
            self.env, plan["source_query"], plan["collections"], plan["tables"], plan["verification_profile"]
        )

        def build_book(*, parent_value=None, helper_value=None, duplicate_identity=False, wrong_email=False):
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Records"
            sheet.append(["__office_parent_id", "Name", "Trace helper", "__office_record_id", "Email"])
            for index, row in enumerate(collected["dataset"]["root"]["records"]):
                email = row["email"] + ".wrong" if wrong_email and index == 0 else row["email"]
                sheet.append([
                    parent_value,
                    row["name"],
                    helper_value,
                    records[0].id if duplicate_identity and index == 1 else row["id"],
                    email,
                ])
            stream = BytesIO()
            workbook.save(stream)
            workbook.close()
            return stream.getvalue()

        result = verify_export_workbook(build_book(), "candidate.xlsx", collected)
        self.assertTrue(result["identity_verified"])
        self.assertEqual(result["projected_rows"], 2)
        with self.assertRaisesRegex(Exception, "unplanned helper columns"):
            verify_export_workbook(build_book(helper_value="unexpected"), "candidate.xlsx", collected)
        with self.assertRaisesRegex(Exception, "parent identity column must be blank"):
            verify_export_workbook(build_book(parent_value=records[0].id), "candidate.xlsx", collected)
        with self.assertRaisesRegex(Exception, "missing, duplicate, or misassociated identity"):
            verify_export_workbook(build_book(duplicate_identity=True), "candidate.xlsx", collected)
        with self.assertRaisesRegex(Exception, "selected source value"):
            verify_export_workbook(build_book(wrong_email=True), "candidate.xlsx", collected)

    def test_relation_projection_rejects_missing_or_misassociated_child_rows(self):
        categories = self.env["res.partner.category"].create([
            {"name": "M3 relation verifier A " + uuid4().hex},
            {"name": "M3 relation verifier B " + uuid4().hex},
        ])
        parents = self.env["res.partner"].create([
            {"name": "M3 relation verifier parent A " + uuid4().hex},
            {"name": "M3 relation verifier parent B " + uuid4().hex},
        ])
        parents[0].write({"category_id": [(6, 0, categories.ids)]})
        parents[1].write({"category_id": [(6, 0, categories[:1].ids)]})
        source_query = {
            "model": "res.partner",
            "domain": [["id", "in", parents.ids]],
            "fields": ["name"],
            "order": "id asc",
        }
        collections = [{
            "key": "categories",
            "relation_field": "category_id",
            "relation_model": "res.partner.category",
            "inverse_field": None,
            "fields": ["name"],
            "order": "id asc",
        }]
        tables = [
            {"name": "Parents", "source": "root", "columns": [{"label": "Name", "source_field": "name"}]},
            {"name": "Categories", "source": "categories", "columns": [{"label": "Category", "source_field": "name"}]},
        ]
        with patch("odoo.addons.office_engine_m3.services.dataset_collector._MAX_RELATION_ROWS", 3):
            collected = collect_export_dataset(
                self.env, source_query, collections, tables, "record_projection"
            )
        dataset = collected["dataset"]
        self.assertEqual(dataset["relations"]["categories"]["record_count"], 2)
        self.assertEqual(dataset["relations"]["categories"]["pair_count"], 3)

        def workbook_bytes(*, omit_pair=False, misassociate=False):
            workbook = Workbook()
            root_sheet = workbook.active
            root_sheet.title = "Parents"
            root_sheet.append(["Name", "__office_record_id"])
            for row in dataset["root"]["records"]:
                root_sheet.append([row["name"], row["id"]])
            relation_sheet = workbook.create_sheet("Categories")
            relation_sheet.append(["Category", "__office_parent_id", "__office_record_id"])
            child_by_id = {row["id"]: row for row in dataset["relations"]["categories"]["records"]}
            pairs = dataset["relations"]["categories"]["pairs"]
            for index, (parent_id, child_id) in enumerate(pairs):
                if omit_pair and index == len(pairs) - 1:
                    continue
                if misassociate and index == 0:
                    parent_id = parents[1].id
                relation_sheet.append([child_by_id[child_id]["name"], parent_id, child_id])
            stream = BytesIO()
            workbook.save(stream)
            workbook.close()
            return stream.getvalue()

        self.assertEqual(verify_export_workbook(workbook_bytes(), "relations.xlsx", collected)["projected_rows"], 5)
        with self.assertRaisesRegex(Exception, "missing or extra data row"):
            verify_export_workbook(workbook_bytes(omit_pair=True), "relations.xlsx", collected)
        with self.assertRaisesRegex(Exception, "misassociated identity"):
            verify_export_workbook(workbook_bytes(misassociate=True), "relations.xlsx", collected)

    def test_handoff_digest_mismatch_stops_before_provider_and_candidate_creation(self):
        from odoo.exceptions import ValidationError
        from ..services.export_orchestrator import execute_export_records

        partner = self.env["res.partner"].create({"name": "M3 bad handoff digest " + uuid4().hex})
        env = self._owner_env()
        thread = self._make_thread(env)
        self._user(thread, "Export the synthetic contact.")
        tool_message = self._tool(thread)
        plan = self._root_plan([partner.id])
        collected = collect_export_dataset(
            env, plan["source_query"], plan["collections"], plan["tables"], plan["verification_profile"]
        )
        tampered = dict(collected, handoff_sha256="0" * 64)
        adapter = _HostedCIFixtureAdapter()
        with (
            patch("odoo.addons.office_engine_m3.services.export_orchestrator.collect_export_dataset", return_value=tampered),
            self.assertRaisesRegex(ValidationError, "handoff digest"),
        ):
            execute_export_records(
                env, thread, tool_message,
                workbook_source="new",
                source_query=plan["source_query"],
                collections=plan["collections"],
                tables=plan["tables"],
                verification_profile=plan["verification_profile"],
                adapter=adapter,
                provider_client=object(),
                model="synthetic-route-b",
                limits=SimpleNamespace(),
            )
        session = env["office.mapping.session"].search([("thread_id", "=", thread.id)], limit=1)
        self.assertTrue(session)
        self.assertFalse(env["office.workbook.version"].search([("session_id", "=", session.id)]))
        self.assertFalse(session.current_version_id)
        self.assertFalse(session.last_valid_version_id)
        self.assertEqual(session.document_revision, 0)
        self.assertFalse(adapter.calls)

    def test_provider_without_usable_candidate_is_failed_without_advancing_current(self):
        partner = self.env["res.partner"].create({"name": "M3 provider no output " + uuid4().hex})
        env = self._owner_env()
        thread = self._make_thread(env)
        self._user(thread, "Export the synthetic contact.")
        tool_message = self._tool(thread)
        plan = self._root_plan([partner.id])

        class _NoOutputAdapter:
            def execute(self, **_kwargs):
                return SimpleNamespace(
                    operation_status="failed",
                    candidate_bytes=None,
                    error=SimpleNamespace(category="xlsx_output_missing_or_ambiguous"),
                    to_dict=lambda: {"operation_status": "failed", "candidate_present": False},
                )

        office_tool = env["llm.tool"].search([("name", "=", "office")], limit=1)
        with patch(
            "odoo.addons.office_engine_m3.services.export_orchestrator._provider_dependencies",
            return_value=(_NoOutputAdapter(), object(), "synthetic-route-b", SimpleNamespace()),
        ):
            result = office_tool.with_context(message=tool_message).execute({
                "action": "export_records",
                "candidate_version_id": None,
                "confirmation_required": None,
                "confirmation_reason": None,
                "workbook_source": "new",
                "source_query": plan["source_query"],
                "collections": plan["collections"],
                "tables": plan["tables"],
                "verification_profile": plan["verification_profile"],
            })
        self.assertEqual(result["operation_status"], "provider_export_unavailable", result)
        version = env["office.workbook.version"].browse(result["version_id"])
        session = version.session_id
        self.assertEqual(version.state, "failed")
        self.assertFalse(version.output_attachment_id)
        self.assertFalse(session.current_version_id)
        self.assertFalse(session.last_valid_version_id)
        self.assertEqual(session.document_revision, 0)

    def test_root_and_handoff_resource_limits_accept_exact_boundary(self):
        from odoo.exceptions import ValidationError

        partners = self.env["res.partner"].create([
            {"name": "M3 resource boundary A " + uuid4().hex},
            {"name": "M3 resource boundary B " + uuid4().hex},
        ])
        plan = self._root_plan(partners.ids)
        initial = collect_export_dataset(
            self.env, plan["source_query"], plan["collections"], plan["tables"], plan["verification_profile"]
        )
        with patch("odoo.addons.office_engine_m3.services.dataset_collector._MAX_ROOT_ROWS", 2):
            at_root_limit = collect_export_dataset(
                self.env, plan["source_query"], plan["collections"], plan["tables"], plan["verification_profile"]
            )
        self.assertEqual(at_root_limit["root_count"], 2)
        with patch(
            "odoo.addons.office_engine_m3.services.dataset_collector._MAX_HANDOFF_BYTES",
            initial["payload_bytes"],
        ):
            at_payload_limit = collect_export_dataset(
                self.env, plan["source_query"], plan["collections"], plan["tables"], plan["verification_profile"]
            )
        self.assertEqual(at_payload_limit["payload_bytes"], initial["payload_bytes"])
        with patch(
            "odoo.addons.office_engine_m3.services.dataset_collector._MAX_HANDOFF_BYTES",
            initial["payload_bytes"] - 1,
        ), self.assertRaisesRegex(ValidationError, "configured handoff byte limit"):
            collect_export_dataset(
                self.env, plan["source_query"], plan["collections"], plan["tables"], plan["verification_profile"]
            )

    def test_collector_fails_closed_for_missing_related_rows_and_wrong_inverse(self):
        from odoo.exceptions import ValidationError
        from ..services import dataset_collector

        category = self.env["res.partner.category"].create({"name": "M3 inaccessible category " + uuid4().hex})
        m2m_parent = self.env["res.partner"].create({"name": "M3 invisible relation parent " + uuid4().hex})
        m2m_parent.write({"category_id": [(6, 0, category.ids)]})
        m2m_query = {
            "model": "res.partner", "domain": [["id", "in", m2m_parent.ids]],
            "fields": ["name"], "order": "id asc",
        }
        m2m_collections = [{
            "key": "categories", "relation_field": "category_id", "relation_model": "res.partner.category",
            "inverse_field": None, "fields": ["name"], "order": "id asc",
        }]
        m2m_tables = [
            {"name": "Parents", "source": "root", "columns": [{"label": "Name", "source_field": "name"}]},
            {"name": "Categories", "source": "categories", "columns": [{"label": "Name", "source_field": "name"}]},
        ]
        original_read_pages = dataset_collector._read_pages

        def hide_related_rows(model, domain, fields, order, **kwargs):
            if model._name == "res.partner.category":
                return [], 0, 1
            return original_read_pages(model, domain, fields, order, **kwargs)

        with patch("odoo.addons.office_engine_m3.services.dataset_collector._read_pages", side_effect=hide_related_rows):
            with self.assertRaisesRegex(ValidationError, "related records visible to this user"):
                collect_export_dataset(self.env, m2m_query, m2m_collections, m2m_tables, "record_projection")

        o2m_parent = self.env["res.partner"].create({"name": "M3 inverse parent " + uuid4().hex})
        outsider = self.env["res.partner"].create({"name": "M3 inverse outsider " + uuid4().hex})
        self.env["res.partner"].create({
            "name": "M3 inverse child " + uuid4().hex,
            "parent_id": o2m_parent.id,
        })
        o2m_query = {
            "model": "res.partner", "domain": [["id", "in", o2m_parent.ids]],
            "fields": ["name"], "order": "id asc",
        }
        o2m_collections = [{
            "key": "children", "relation_field": "child_ids", "relation_model": "res.partner",
            "inverse_field": "parent_id", "fields": ["name"], "order": "id asc",
        }]
        o2m_tables = [
            {"name": "Parents", "source": "root", "columns": [{"label": "Name", "source_field": "name"}]},
            {"name": "Children", "source": "children", "columns": [{"label": "Name", "source_field": "name"}]},
        ]
        calls = 0

        def corrupt_inverse(model, domain, fields, order, **kwargs):
            nonlocal calls
            calls += 1
            rows, count, pages = original_read_pages(model, domain, fields, order, **kwargs)
            if calls == 2:
                rows = [dict(row, parent_id=[outsider.id, outsider.name]) for row in rows]
            return rows, count, pages

        with patch("odoo.addons.office_engine_m3.services.dataset_collector._read_pages", side_effect=corrupt_inverse):
            with self.assertRaisesRegex(ValidationError, "points outside the selected root dataset"):
                collect_export_dataset(self.env, o2m_query, o2m_collections, o2m_tables, "record_projection")
