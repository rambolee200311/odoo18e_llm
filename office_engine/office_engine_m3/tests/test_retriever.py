import json
from unittest.mock import patch
from uuid import uuid4

from odoo.tests import TransactionCase
from odoo.exceptions import AccessError

from ..models.retriever_errors import RetrieverToolError


class TestRetriever(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tool = cls.env.ref("llm_tool.llm_tool_odoo_record_retriever")

    def _partners(self):
        suffix = uuid4().hex
        return self.env["res.partner"].create(
            [
                {"name": f"M3 Retriever {suffix}", "email": f"m3-{suffix}-{index}@example.invalid"}
                for index in range(3)
            ]
        )

    def test_legacy_search_shape_and_explicit_pagination_with_in_domain(self):
        partners = self._partners()
        emails = partners.mapped("email")
        arguments = {
            "operation": "search",
            "model": "res.partner",
            "domain": [["email", "in", emails]],
            "fields": ["name", "email"],
            "limit": 2,
        }
        first = self.tool.execute(arguments)
        self.assertEqual(first["status"], "success")
        self.assertEqual(first["count"], 3)
        self.assertEqual(first["returned_count"], 2)
        self.assertTrue(first["has_more"])
        self.assertEqual(first["next_offset"], 2)
        self.assertEqual([row["id"] for row in first["records"]], partners.ids[:2])

        last = self.tool.execute({**arguments, "offset": first["next_offset"]})
        self.assertEqual([row["id"] for row in last["records"]], partners.ids[2:])
        self.assertEqual(last["returned_count"], 1)
        self.assertFalse(last["has_more"])
        self.assertIsNone(last["next_offset"])

        excluded = self.tool.execute(
            {
                "operation": "search",
                "model": "res.partner",
                "domain": [
                    ["email", "in", partners.mapped("email")],
                    ["id", "not in", partners.ids[:2]],
                ],
                "fields": ["email"],
                "limit": 500,
            }
        )
        self.assertEqual([row["id"] for row in excluded["records"]], partners.ids[2:])
        self.assertEqual(excluded["limit"], 500)

        old_list = self.tool.execute({"model": "res.partner", "domain": [["email", "in", emails]], "limit": 3})
        self.assertIsInstance(old_list, list)

        legacy = self.tool.execute(
            {
                "model": "res.partner",
                "domain": [["email", "in", emails]],
                "fields": ["name", "email"],
                "order": None,
                "include_pagination": True,
            }
        )
        self.assertEqual(set(legacy), {"records", "count", "offset", "limit", "has_more"})
        self.assertEqual(legacy["count"], 3)

    def test_default_and_explicit_sorting_are_stable(self):
        partners = self._partners()
        email_domain = [["email", "in", partners.mapped("email")]]
        default_page = self.tool.execute(
            {"operation": "search", "model": "res.partner", "domain": email_domain, "limit": 3}
        )
        explicit_page = self.tool.execute(
            {
                "operation": "search",
                "model": "res.partner",
                "domain": email_domain,
                "limit": 3,
                "order": "name asc",
            }
        )
        self.assertEqual([row["id"] for row in default_page["records"]], partners.ids)
        self.assertEqual([row["id"] for row in explicit_page["records"]], partners.ids)
        self.assertEqual(self.tool._retriever_stable_order("parent_id.id asc"), "parent_id.id asc, id asc")
        self.assertEqual(self.tool._retriever_stable_order("id desc"), "id desc")

    def test_registry_discovery_and_description_ignore_business_acl(self):
        user = self.env["res.users"].create(
            {
                "name": "M3 Retriever Limited User",
                "login": f"m3-limited-{uuid4().hex}",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        tool = self.tool.with_user(user)
        discovered = tool.execute({"operation": "discover", "query": "ir.config_parameter"})
        self.assertIn("ir.config_parameter", [item["model"] for item in discovered["models"]])
        described = tool.execute(
            {"operation": "describe", "model": "ir.config_parameter", "fields": ["key", "value"]}
        )
        self.assertEqual([item["name"] for item in described["fields"]], ["key", "value"])
        restricted_field = tool.execute(
            {"operation": "describe", "model": "res.users", "fields": ["password"]}
        )
        self.assertEqual(restricted_field["fields"][0]["name"], "password")

        with self.assertRaises(AccessError) as caught:
            tool.execute({"operation": "search", "model": "ir.config_parameter", "fields": ["key"], "limit": 1})
        self.assertEqual(caught.exception.error_code, "ACCESS_DENIED")

    def test_relation_and_selection_metadata_are_reported(self):
        described = self.tool.execute(
            {
                "operation": "describe",
                "model": "res.partner",
                "fields": ["parent_id", "child_ids", "category_id", "company_type"],
            }
        )
        fields_by_name = {item["name"]: item for item in described["fields"]}
        self.assertEqual(fields_by_name["parent_id"]["relation"], "res.partner")
        self.assertEqual(fields_by_name["child_ids"]["inverse_field"], "parent_id")
        self.assertEqual(fields_by_name["category_id"]["type"], "many2many")
        self.assertIn("selection", fields_by_name["company_type"])
        json.dumps(described)

    def test_structured_query_errors_and_empty_results(self):
        cases = [
            ({"operation": "search", "model": "office.m3.model.missing"}, "MODEL_NOT_FOUND"),
            ({"operation": "search", "model": "res.partner", "fields": ["m3_missing_field"]}, "FIELD_NOT_FOUND"),
            ({"operation": "search", "model": "res.partner", "order": "m3_missing_field asc"}, "FIELD_NOT_FOUND"),
            ({"operation": "search", "model": "res.partner", "domain": [["id", "in", 1]]}, "INVALID_QUERY"),
            ({"operation": "search", "model": "res.partner", "limit": 501}, "INVALID_QUERY"),
            ({"operation": "unknown", "model": "res.partner"}, "INVALID_QUERY"),
        ]
        for arguments, expected in cases:
            with self.subTest(expected=expected, arguments=arguments):
                with self.assertRaises(RetrieverToolError) as caught:
                    self.tool.execute(arguments)
                self.assertEqual(caught.exception.error_code, expected)

        empty = self.tool.execute(
            {"operation": "search", "model": "res.partner", "domain": [["id", "=", -987654321]]}
        )
        self.assertEqual(empty["status"], "success")
        self.assertEqual(empty["records"], [])
        self.assertEqual(empty["count"], 0)

    def test_unexpected_orm_failure_is_sanitized_and_has_diagnostic_id(self):
        model_class = type(self.env["res.partner"])
        with patch.object(model_class, "search_count", side_effect=RuntimeError("synthetic secret detail")):
            with self.assertRaises(RetrieverToolError) as caught:
                self.tool.execute({"operation": "search", "model": "res.partner", "domain": []})
        self.assertEqual(caught.exception.error_code, "QUERY_FAILED")
        self.assertTrue(caught.exception.diagnostic_id)
        self.assertNotIn("synthetic secret detail", str(caught.exception))

    def test_tool_schema_exposes_array_valued_domain(self):
        schema = self.tool.get_input_schema()
        value_schema = schema["properties"]["domain"]["anyOf"][0]["items"]["oneOf"][1]["prefixItems"][2]
        self.assertEqual(value_schema["oneOf"][1]["type"], "array")
        self.assertEqual(value_schema["oneOf"][1]["maxItems"], 1000)

    def test_retriever_error_message_retains_error_code_and_diagnostic_id(self):
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "M3 Retriever Error User",
                "login": f"m3-error-{uuid4().hex}",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        provider = self.env["llm.provider"].create(
            {"name": "M3 Retriever Test Provider " + uuid4().hex, "service": "openai"}
        )
        model = self.env["llm.model"].create(
            {
                "name": "M3 Retriever Test Model " + uuid4().hex,
                "provider_id": provider.id,
                "model_use": "chat",
            }
        )
        thread = self.env["llm.thread"].create(
            {
                "name": "M3 Retriever Error Thread " + uuid4().hex,
                "provider_id": provider.id,
                "model_id": model.id,
                "user_id": user.id,
                "tool_ids": [(6, 0, [self.tool.id])],
            }
        )
        tool_call = {
            "id": "call-m3-retriever-access-denied",
            "type": "function",
            "function": {
                "name": "odoo_record_retriever",
                "arguments": {"operation": "search", "model": "ir.config_parameter", "fields": ["key"], "limit": 1},
            },
        }
        message = self.env["mail.message"].post_tool_call(tool_call, thread_model=thread)
        limited_thread = thread.with_user(user)
        limited_message = message.with_user(user)
        events = list(limited_message.execute_tool_call(thread_model=limited_thread))
        limited_message.invalidate_recordset(["body_json"])
        self.assertEqual(limited_message.body_json["status"], "error")
        self.assertEqual(limited_message.body_json["error_code"], "ACCESS_DENIED")
        self.assertTrue(limited_message.body_json["diagnostic_id"])
        self.assertEqual(events[-1]["type"], "message_update")
