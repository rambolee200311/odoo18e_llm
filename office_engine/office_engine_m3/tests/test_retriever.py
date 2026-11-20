"""验证 Retriever 的查询契约、Registry Discovery 和分页稳定性。"""
import json
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4
from types import SimpleNamespace

from odoo import fields
from odoo.tests import TransactionCase
from odoo.exceptions import AccessError

from ..models.retriever_errors import RetrieverToolError


class TestRetriever(TransactionCase):
    """覆盖 Retriever 的权限、兼容、发现排序和错误返回行为。"""
    @classmethod
    def setUpClass(cls):
        """创建当前用户 Retriever，并准备语义发现分页测试使用的 Provider 与模型。"""
        super().setUpClass()
        cls.tool = cls.env.ref("llm_tool.llm_tool_odoo_record_retriever")
        cls.provider = cls.env["llm.provider"].create(
            {"name": "M4 Retriever snapshot provider " + uuid4().hex, "service": "openai"}
        )
        cls.model = cls.env["llm.model"].create(
            {
                "name": "M4 Retriever snapshot model " + uuid4().hex,
                "provider_id": cls.provider.id,
                "model_use": "chat",
            }
        )

    def _discovery_thread(self):
        """创建绑定现有 Retriever 的隔离 Thread，供分页状态测试使用。"""
        thread = self.env["llm.thread"].create(
            {
                "name": "M4 Retriever pagination " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
                "tool_ids": [(6, 0, [self.tool.id])],
            }
        )
        return thread

    def _discovery_tool_message(self, thread, arguments):
        """创建真实 mail.message 工具调用记录，使快照沿实际 Thread 路径保存。"""
        return thread.message_post(
            body="Synthetic Retriever discovery call",
            body_json={
                "type": "tool_execution",
                "tool_name": "odoo_record_retriever",
                "arguments": arguments,
                "status": "executing",
            },
            llm_role="tool",
            author_id=False,
        )

    def _partners(self):
        suffix = uuid4().hex
        return self.env["res.partner"].create(
            [
                {"name": f"M3 Retriever {suffix}", "email": f"m3-{suffix}-{index}@example.invalid"}
                for index in range(3)
            ]
        )

    def test_legacy_search_shape_and_explicit_pagination_with_in_domain(self):
        """验证省略 operation 的旧调用形状，以及带 `in` Domain 的显式分页结果。"""
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
        """验证默认 ID 排序和显式排序均具有可重复的稳定次序。"""
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
        """验证 Registry 元数据发现不受业务记录 ACL 影响，而记录查询仍受 ACL 限制。"""
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

    def test_discover_preserves_public_metadata_shape_and_stable_pagination(self):
        """验证 Registry 发现响应的公开字段及连续分页顺序保持兼容。"""
        first = self.tool.execute({"operation": "discover", "limit": 2, "offset": 0})
        second = self.tool.execute({"operation": "discover", "limit": 2, "offset": 2})
        self.assertEqual(first["count"], len(self.env.registry.models))
        combined = [row["model"] for row in first["models"] + second["models"]]
        self.assertEqual(combined, sorted(self.env.registry.models)[:4])
        self.assertEqual(set(first["models"][0]), {"model", "description", "rec_name"})
        self.assertEqual(first["offset"], 0)
        self.assertEqual(second["offset"], 2)

    def test_semantic_discovery_ranks_stably_without_discarding_low_similarity_models(self):
        """验证语义发现会稳定排序，并保留较低相似度的 Registry 候选。"""
        class Provider:
            """返回测试指定的向量，用于验证相似度排序及同分模型名排序。"""
            id = 991

            def embedding(self, texts):
                """记录待嵌入文本，并返回用于排序测试的固定向量。"""
                self.texts = texts
                return [
                    [1.0, 0.0],
                    [0.8, 0.6],
                    [0.0, 1.0],
                    [0.8, 0.6],
                ]

        class ModelZ:
            """提供排序测试所需的合成模型元数据。"""
            _description = "Synthetic matching model"
            _rec_name = "name"

        class ModelLow:
            """提供低相似度合成模型，用于确认候选不会被阈值静默丢弃。"""
            _description = "Synthetic unrelated model"
            _rec_name = "title"

        class ModelA:
            """提供与 ModelZ 同分的合成模型，用于验证稳定排序。"""
            _description = "Synthetic matching model"
            _rec_name = "name"

        provider = Provider()
        with patch.object(type(self.tool), "_retriever_discovery_provider", return_value=provider):
            matches = self.tool._retriever_semantic_discovery(
                "synthetic user wording",
                [("z.synthetic", ModelZ), ("low.synthetic", ModelLow), ("a.synthetic", ModelA)],
            )
        self.assertEqual([row["model"] for row in matches], ["a.synthetic", "z.synthetic", "low.synthetic"])
        self.assertTrue(all({"model", "description", "rec_name"}.issubset(row) for row in matches))
        self.assertTrue(all("_discovery_score_bucket" in row for row in matches))
        self.assertEqual(provider.texts[0], "synthetic user wording")
        self.assertTrue(all(text.startswith("Odoo model:") for text in provider.texts[1:]))

    def test_semantic_discovery_provider_failure_is_query_failed_not_empty_success(self):
        """验证 embedding Provider 失败返回查询错误，而不是成功空结果。"""
        class Provider:
            """返回不完整向量结果，以触发并验证 Provider 错误处理。"""
            def embedding(self, _texts):
                """为错误分支测试返回一条固定向量。"""
                return [[1.0, 0.0]]

        thread = self._discovery_thread()
        arguments = {"operation": "discover", "query": "synthetic user wording", "limit": 2}
        message = self._discovery_tool_message(thread, arguments)
        with patch.object(type(self.tool), "_retriever_discovery_provider", return_value=Provider()):
            with self.assertRaises(RetrieverToolError) as caught:
                self.tool.with_context(message=message).execute(arguments)
        self.assertEqual(caught.exception.error_code, "QUERY_FAILED")
        self.assertTrue(caught.exception.diagnostic_id)

    def test_semantic_discovery_uses_full_registry_and_preserves_legacy_literal_discovery(self):
        """验证有 Thread 上下文时使用完整 Registry 语义发现，旧调用仍使用原字面发现。"""
        class Provider:
            """为全 Registry 输入返回相同向量，隔离验证分页快照逻辑。"""
            id = 991

            def embedding(self, texts):
                """记录完整 Registry 输入，并返回排序测试所需的固定向量。"""
                self.texts = texts
                return [[1.0, 0.0]] + [[1.0, 0.0] for _text in texts[1:]]

        provider = Provider()
        thread = self._discovery_thread()
        first_args = {"operation": "discover", "query": "natural language object request", "limit": 3, "offset": 0}
        first_call = self._discovery_tool_message(thread, first_args)
        with (
            patch.object(type(self.tool), "_retriever_discovery_thread_context", return_value=(thread, provider)),
            patch.object(type(self.tool), "_retriever_chat_rerank_discovery", side_effect=lambda _query, matches: matches),
        ):
            discovered = self.tool.with_context(message=first_call).execute(first_args)
            first_call.write({"body_json": {**first_call.body_json, "status": "completed", "result": discovered}})
            next_args = {**first_args, "offset": 3}
            next_call = self._discovery_tool_message(thread, next_args)
            next_page = self.tool.with_context(message=next_call).execute(next_args)
        self.assertEqual(discovered["count"], len(self.env.registry.models))
        self.assertEqual(len(provider.texts), len(self.env.registry.models) + 1)
        self.assertEqual(provider.texts[0], "natural language object request")
        self.assertTrue(all(set(row) == {"model", "description", "rec_name"} for row in discovered["models"]))
        combined = [row["model"] for row in discovered["models"] + next_page["models"]]
        self.assertEqual(combined, sorted(self.env.registry.models)[:6])

        legacy = self.tool.execute({"operation": "discover", "query": "ir.config_parameter"})
        self.assertIn("ir.config_parameter", [row["model"] for row in legacy["models"]])

    def test_semantic_pagination_reuses_persisted_order_across_provider_calls(self):
        """证明后续页与重复遍历复用首个完整排序，而不依赖 GPT 重复输出。"""
        thread = self._discovery_thread()
        query = "synthetic registry pagination query"
        profiles = [
            self.tool._retriever_discovery_profile(name, model_class)
            | {"_discovery_score_bucket": 1}
            for name, model_class in sorted(self.env.registry.models.items())
        ]
        first_order = [profiles[3], *profiles[:3], *profiles[4:]]
        rerank_results = [
            first_order,
            list(reversed(profiles)),
        ]
        with (
            patch.object(type(self.tool), "_retriever_semantic_discovery", return_value=profiles) as semantic,
            patch.object(type(self.tool), "_retriever_chat_rerank_discovery", side_effect=rerank_results) as rerank,
        ):
            first_args = {"operation": "discover", "query": query, "limit": 3, "offset": 0}
            first_call = self._discovery_tool_message(thread, first_args)
            first = self.tool.with_context(message=first_call).execute(first_args)
            first_call.write({"body_json": {**first_call.body_json, "status": "completed", "result": first}})

            next_args = {**first_args, "offset": 3}
            next_call = self._discovery_tool_message(thread, next_args)
            second = self.tool.with_context(message=next_call).execute(next_args)
            next_call.write({"body_json": {**next_call.body_json, "status": "completed", "result": second}})

            repeat_call = self._discovery_tool_message(thread, first_args)
            repeated_first = self.tool.with_context(message=repeat_call).execute(first_args)

        names = [row["model"] for row in first["models"] + second["models"]]
        repeated_names = [row["model"] for row in repeated_first["models"]]
        self.assertEqual(names, [row["model"] for row in first_order[:6]])
        self.assertEqual(repeated_names, names[:3])
        self.assertEqual(semantic.call_count, 1)
        self.assertEqual(rerank.call_count, 1)

        snapshots = self.env["mail.message"].search(
            [("model", "=", "llm.thread"), ("res_id", "=", thread.id),
             ("llm_role", "=", False), ("llm_silent_retrieval", "=", True)]
        )
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots.body_json["type"], "office_m4_discovery_order_snapshot")
        self.assertFalse(snapshots & thread._get_context_messages())

    def test_semantic_pagination_fails_closed_when_saved_order_is_missing(self):
        """缺少首轮分页顺序时拒绝返回可能错位的后续页。"""
        thread = self._discovery_thread()
        query = "synthetic registry pagination query"
        profiles = [
            self.tool._retriever_discovery_profile(name, model_class)
            | {"_discovery_score_bucket": 1}
            for name, model_class in sorted(self.env.registry.models.items())
        ]
        first_args = {"operation": "discover", "query": query, "limit": 1, "offset": 0}
        first_call = self._discovery_tool_message(thread, first_args)
        with (
            patch.object(type(self.tool), "_retriever_semantic_discovery", return_value=profiles),
            patch.object(type(self.tool), "_retriever_chat_rerank_discovery", return_value=profiles),
        ):
            first = self.tool.with_context(message=first_call).execute(first_args)
        first_call.write({"body_json": {**first_call.body_json, "status": "completed", "result": first}})
        snapshot = self.env["mail.message"].search(
            [("model", "=", "llm.thread"), ("res_id", "=", thread.id),
             ("llm_role", "=", False), ("llm_silent_retrieval", "=", True)], limit=1
        )
        snapshot.unlink()

        next_args = {**first_args, "offset": 1}
        next_call = self._discovery_tool_message(thread, next_args)
        with self.assertRaises(RetrieverToolError) as caught:
            self.tool.with_context(message=next_call).execute(next_args)
        self.assertEqual(caught.exception.error_code, "QUERY_FAILED")
        self.assertIn("restart at offset 0", str(caught.exception))

    def test_chat_reranker_uses_only_query_and_full_registry_metadata(self):
        """验证 GPT 重排输入仅含当前查询与完整 Registry 元数据。"""
        profiles = [
            {"model": f"synthetic.{name}", "description": f"Description {name}", "rec_name": "name"}
            for name in ("alpha", "beta", "gamma", "delta", "epsilon", "zeta")
        ]

        class Provider:
            """记录聊天重排参数并返回固定候选 ID，供请求隔离断言使用。"""
            service = "openai"

            def chat(self, **kwargs):
                """记录重排请求参数，并返回固定的候选排序结果。"""
                self.kwargs = kwargs
                return {"content": '{"ranked_candidate_ids":["C005","C002","C001","C003"]}'}

        provider = Provider()
        model = SimpleNamespace(provider_id=provider)
        thread = SimpleNamespace(id=17, model_id=model)
        with patch.object(type(self.tool), "_retriever_discovery_thread_context", return_value=(thread, provider)):
            ranked = self.tool._retriever_chat_rerank_discovery("find the zeta business object", profiles)

        self.assertEqual([item["model"] for item in ranked[:5]], [
            "synthetic.zeta", "synthetic.beta", "synthetic.delta", "synthetic.epsilon", "synthetic.alpha"
        ])
        self.assertEqual(len(ranked), len(profiles))
        self.assertEqual(set(item["model"] for item in ranked), {item["model"] for item in profiles})
        self.assertEqual(provider.kwargs["model"], model)
        self.assertFalse(provider.kwargs["messages"], "The reranker must not inherit Thread message history.")
        self.assertFalse(provider.kwargs.get("tools"))
        user_payload = json.loads(provider.kwargs["prepend_messages"][1]["content"])
        self.assertEqual(user_payload["business_request"], "find the zeta business object")
        self.assertEqual(len(user_payload["candidates"]), len(profiles))
        self.assertEqual(
            {row["model"] for row in user_payload["candidates"]},
            {item["model"] for item in profiles},
        )
        self.assertTrue(all(set(row) == {"candidate_id", "model", "description", "rec_name"} for row in user_payload["candidates"]))

    def test_chat_reranker_accepts_empty_match_and_rejects_unknown_or_malformed_ids(self):
        """允许重排器返回空候选，并拒绝未知、重复、过多或格式错误的候选 ID。"""
        self.assertEqual(self.tool._retriever_parse_ranked_candidate_ids('{"ranked_candidate_ids":[]}'), [])
        for response in (
            "not json",
            '{"ranked_candidate_ids":["C000","C000"]}',
            '{"ranked_candidate_ids":["C000","C001","C002","C003","C004","C005"]}',
        ):
            with self.subTest(response=response), self.assertRaises(ValueError):
                self.tool._retriever_parse_ranked_candidate_ids(response)

    def test_relation_and_selection_metadata_are_reported(self):
        """验证 describe 返回字段 Selection 选项和关系模型等 Registry 元数据。"""
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
        """验证有效零结果与模型、字段、权限及 Domain 错误采用不同结果语义。"""
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

    def test_domain_rejects_nonsearchable_computed_field_before_orm(self):
        """验证 ORM 会静默忽略的非搜索计算字段在查询前返回 INVALID_QUERY。"""
        Partner = self.env["res.partner"]
        field = Partner._fields["company_type"]
        self.assertFalse(field.store)
        self.assertFalse(field.search)

        with (
            patch.object(type(Partner), "search_read", side_effect=AssertionError("ORM search_read must not run")),
            patch.object(type(Partner), "search_count", side_effect=AssertionError("ORM search_count must not run")),
        ):
            for arguments in (
                {
                    "operation": "search",
                    "model": "res.partner",
                    "domain": [["company_type", "=", "person"]],
                },
                {
                    "model": "res.partner",
                    "domain": [["company_type", "=", "company"]],
                },
            ):
                with self.subTest(arguments=arguments), self.assertRaises(RetrieverToolError) as caught:
                    self.tool.execute(arguments)
                self.assertEqual(caught.exception.error_code, "INVALID_QUERY")
                self.assertIn("company_type", str(caught.exception))

    def test_domain_accepts_stored_custom_search_and_related_search_fields_for_ordinary_user(self):
        """验证存储字段、自定义计算 search 和 related search 字段仍可精确查询。"""
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "CC-M4-02 Domain Search User",
                "login": f"cc-m4-02-domain-{uuid4().hex}",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "groups_id": [(6, 0, [
                    self.env.ref("base.group_user").id,
                    self.env.ref("base.group_partner_manager").id,
                ])],
            }
        )
        Partner = self.env["res.partner"].with_user(user)
        Country = self.env["res.country"].with_user(user)
        country = Country.search([], order="id", limit=1)
        self.assertTrue(country)
        self.assertTrue(country.code)
        suffix = uuid4().hex
        names = [f"CC-M4-02 searchable {suffix}-{index}" for index in range(2)]
        records = Partner.create([
            {"name": name, "is_company": index == 1, "country_id": country.id}
            for index, name in enumerate(names)
        ])

        display_name = Partner._fields["display_name"]
        country_code = Partner._fields["country_code"]
        self.assertFalse(display_name.store)
        self.assertTrue(display_name.search)
        self.assertFalse(country_code.store)
        self.assertTrue(country_code.search)

        # 直接 ORM 对照证明 Odoo 会忽略 company_type 谓词；Retriever 必须在调用 ORM 前失败关闭。
        silently_broadened = Partner.search(
            [("name", "ilike", suffix), ("company_type", "=", "person")]
        )
        expected_people = records.filtered(lambda record: record.company_type == "person")
        self.assertEqual(set(silently_broadened.ids), set(records.ids))
        self.assertEqual(expected_people.ids, [records[0].id])
        with self.assertRaises(RetrieverToolError) as caught:
            self.tool.with_user(user).execute(
                {
                    "operation": "search",
                    "model": "res.partner",
                    "domain": [
                        ["name", "ilike", suffix],
                        ["company_type", "=", "person"],
                    ],
                    "fields": ["id"],
                }
            )
        self.assertEqual(caught.exception.error_code, "INVALID_QUERY")
        self.assertIn("company_type", str(caught.exception))

        stored_result = self.tool.with_user(user).execute(
            {
                "operation": "search",
                "model": "res.partner",
                "domain": [["is_company", "=", True], ["name", "ilike", suffix]],
                "fields": ["id"],
            }
        )
        self.assertEqual([row["id"] for row in stored_result["records"]], [records[1].id])

        computed_result = self.tool.with_user(user).execute(
            {
                "operation": "search",
                "model": "res.partner",
                "domain": [["display_name", "=", names[0]]],
                "fields": ["id"],
            }
        )
        self.assertEqual([row["id"] for row in computed_result["records"]], [records[0].id])

        legacy_result = self.tool.with_user(user).execute(
            {
                "model": "res.partner",
                "domain": [["display_name", "=", names[0]]],
                "fields": ["id"],
            }
        )
        self.assertEqual([row["id"] for row in legacy_result], [records[0].id])

        related_result = self.tool.with_user(user).execute(
            {
                "operation": "search",
                "model": "res.partner",
                "domain": [["country_code", "=", country.code], ["name", "ilike", suffix]],
                "fields": ["id"],
            }
        )
        self.assertEqual({row["id"] for row in related_result["records"]}, set(records.ids))

    def test_discovery_query_is_rejected_for_describe_search_and_legacy_before_orm(self):
        """确认 discovery 专用 query 在其他操作和旧 search 中先报错，不触达 ORM 查询。"""
        invalid_calls = [
            {"operation": "search", "model": "res.partner", "query": "synthetic request"},
            {"operation": "describe", "model": "res.partner", "query": "synthetic request"},
            {"model": "res.partner", "query": "synthetic request"},
        ]
        with (
            patch.object(type(self.tool), "_retriever_search") as search,
            patch.object(type(self.tool), "_retriever_model") as resolve_model,
        ):
            for arguments in invalid_calls:
                with self.subTest(arguments=arguments), self.assertRaises(RetrieverToolError) as caught:
                    self.tool.execute(arguments)
                self.assertEqual(caught.exception.error_code, "INVALID_QUERY")
            search.assert_not_called()
            resolve_model.assert_not_called()

        discovered = self.tool.execute({"operation": "discover", "query": "res.partner"})
        self.assertIn("res.partner", [item["model"] for item in discovered["models"]])

    def test_ordinary_user_retrieves_synthetic_parent_country_date_and_child_data(self):
        """用普通用户和 ORM 合成数据验证跨模型条件及父子关联查询。"""
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "CC-M4-02 Synthetic Reader",
                "login": f"cc-m4-02-{uuid4().hex}",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                # 仅授予 Odoo 原生联系人业务角色以便创建自己的合成夹具；查询仍走该用户 ORM 权限。
                "groups_id": [(6, 0, [
                    self.env.ref("base.group_user").id,
                    self.env.ref("base.group_partner_manager").id,
                ])],
            }
        )
        suffix = uuid4().hex
        Partner = self.env["res.partner"].with_user(user)
        Country = self.env["res.country"].with_user(user)
        parent_name = f"CC-M4-02 parent {suffix}"
        country = Country.search([], order="id", limit=1)
        self.assertTrue(country, "The ordinary test user must be able to read a country for this relation test.")
        parent = Partner.create({
            "name": parent_name,
            "is_company": True,
            "country_id": country.id,
        })
        matches = Partner.create([
            {
                "name": f"CC-M4-02 match {suffix}-{index}",
                "is_company": True,
                "parent_id": parent.id,
                "country_id": country.id,
                "email": f"m4-02-{suffix}-{index}@example.invalid",
            }
            for index in range(2)
        ])
        Partner.create({
            "name": f"CC-M4-02 wrong object type {suffix}",
            "is_company": False,
            "parent_id": parent.id,
            "country_id": country.id,
            "email": f"m4-02-object-type-{suffix}@example.invalid",
        })
        other_parent = Partner.create({"name": f"CC-M4-02 other parent {suffix}", "is_company": True})
        Partner.create({
            "name": f"CC-M4-02 wrong parent {suffix}",
            "is_company": True,
            "parent_id": other_parent.id,
            "country_id": country.id,
            "email": f"m4-02-other-{suffix}@example.invalid",
        })
        contacts = Partner.create([
            {
                "name": f"CC-M4-02 contact {suffix}-{index}",
                "parent_id": company.id,
                "type": "contact",
                "country_id": country.id,
                "email": f"m4-02-contact-{suffix}-{index}@example.invalid",
            }
            for index, company in enumerate(matches, start=1)
        ])

        now = fields.Datetime.now()
        domain = [
            ["parent_id.name", "=", parent_name],
            ["country_id.name", "=", country.name],
            ["is_company", "=", True],
            ["active", "=", True],
            ["create_date", ">=", fields.Datetime.to_string(now - timedelta(minutes=5))],
            ["create_date", "<=", fields.Datetime.to_string(now + timedelta(minutes=5))],
        ]
        orders = self.tool.with_user(user).execute(
            {
                "operation": "search",
                "model": "res.partner",
                "domain": domain,
                "fields": ["id", "name", "parent_id", "country_id", "email", "create_date"],
                "order": "name asc",
            }
        )
        self.assertEqual(orders["status"], "success")
        self.assertEqual([row["id"] for row in orders["records"]], sorted(matches.ids, key=lambda item: Partner.browse(item).name))

        children = self.tool.with_user(user).execute(
            {
                "operation": "search",
                "model": "res.partner",
                "domain": [["parent_id", "in", matches.ids], ["type", "=", "contact"]],
                "fields": ["id", "name", "parent_id", "email"],
                "order": "name asc",
            }
        )
        returned_contacts = children["records"]
        self.assertEqual({row["id"] for row in returned_contacts}, set(contacts.ids))
        self.assertEqual(
            {row["parent_id"][0] for row in returned_contacts},
            set(matches.ids),
        )
        self.assertEqual(
            {row["email"] for row in returned_contacts},
            set(contacts.mapped("email")),
        )

    def test_unexpected_orm_failure_is_sanitized_and_has_diagnostic_id(self):
        """验证意外 ORM 异常被脱敏，并返回可供内部排查的诊断 ID。"""
        model_class = type(self.env["res.partner"])
        with patch.object(model_class, "search_count", side_effect=RuntimeError("synthetic secret detail")):
            with self.assertRaises(RetrieverToolError) as caught:
                self.tool.execute({"operation": "search", "model": "res.partner", "domain": []})
        self.assertEqual(caught.exception.error_code, "QUERY_FAILED")
        self.assertTrue(caught.exception.diagnostic_id)
        self.assertNotIn("synthetic secret detail", str(caught.exception))

    def test_tool_schema_exposes_array_valued_domain(self):
        """验证公开 Tool Schema 接受 `in` / `not in` 所需的数组 Domain 值。"""
        schema = self.tool.get_input_schema()
        value_schema = schema["properties"]["domain"]["anyOf"][0]["items"]["oneOf"][1]["prefixItems"][2]
        self.assertEqual(value_schema["oneOf"][1]["type"], "array")
        self.assertEqual(value_schema["oneOf"][1]["maxItems"], 1000)

    def test_retriever_error_message_retains_error_code_and_diagnostic_id(self):
        """验证 Retriever 错误消息保留稳定错误码与诊断 ID。"""
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
