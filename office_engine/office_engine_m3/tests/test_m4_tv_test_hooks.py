"""验证 M4 TV 内部测试钩子的环境、数据库、Thread 白名单和故障类型限制。"""

import json
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from ..services.m4_tv_test_hooks import (
    CONFIG_PARAMETER,
    TEST_DATABASE,
    parse_fault_config,
    provider_audit_thread_id,
    raise_handoff_interruption,
)


class TestM4TVTestHooks(TransactionCase):
    """验证 M4 TV 故障注入和 Provider 审计入口只在受控测试条件下启用。"""
    def test_fault_requires_test_switch_development_database_and_exact_thread(self):
        """确认故障注入同时受测试开关、开发库名称和目标 Thread 限制。"""
        raw = json.dumps({"thread_id": 17, "fault": "handoff_interruption"})
        with patch.dict("os.environ", {"OFFICE_M4_TV_TEST_HOOKS": "0"}):
            disabled = parse_fault_config(TEST_DATABASE, False, raw, 17)
        wrong_database = parse_fault_config("production", True, raw, 17)
        wrong_thread = parse_fault_config(TEST_DATABASE, True, raw, 18)
        valid = parse_fault_config(TEST_DATABASE, True, raw, 17)
        self.assertIsNone(disabled)
        self.assertIsNone(wrong_database)
        self.assertIsNone(wrong_thread)
        self.assertEqual(valid["fault"], "handoff_interruption")

    def test_invalid_fault_and_page_size_are_rejected(self):
        """拒绝未登记的故障类型和超出允许范围的分页参数。"""
        invalid_mode = json.dumps({"thread_id": 17, "fault": "arbitrary"})
        invalid_size = json.dumps({"thread_id": 17, "fault": "collector_page_failure", "page_size": 21})
        self.assertIsNone(parse_fault_config(TEST_DATABASE, True, invalid_mode, 17))
        self.assertIsNone(parse_fault_config(TEST_DATABASE, True, invalid_size, 17))

    def test_fault_controls_are_not_accepted_from_untrusted_tool_payload(self):
        """确认普通 Office Tool Schema 不暴露内部故障注入控制项。"""
        import json as json_module

        tool = self.env["llm.tool"].search([("name", "=", "office")], limit=1)
        schema = tool.get_input_schema() if tool else {}
        if isinstance(schema, str):
            schema = json_module.loads(schema)
        self.assertNotIn("m4_tv_test_fault", schema.get("properties", {}))
        self.assertNotIn("fault", schema.get("properties", {}))

    def test_allowed_fault_values_are_explicit_and_bounded(self):
        """确认测试入口只接受明确列出的三种隔离故障场景。"""
        for fault in ("collector_page_failure", "handoff_interruption", "output_identity_mismatch"):
            parsed = parse_fault_config(TEST_DATABASE, True, json.dumps({"thread_id": 17, "fault": fault}), 17)
            self.assertEqual(parsed["fault"], fault)

    def test_handoff_fault_is_consumed_for_allowlisted_ordinary_user_thread(self):
        """确认普通业务用户执行时能读取并消费管理员配置的精确 Thread 故障。"""
        ordinary_user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "M4 handoff fault ordinary user",
            "login": "m4-handoff-fault-ordinary-user-test",
            "company_id": self.env.company.id,
            "company_ids": [(6, 0, [self.env.company.id])],
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        user_env = self.env(user=ordinary_user.id)
        params = self.env["ir.config_parameter"].sudo()
        params.set_param(CONFIG_PARAMETER, json.dumps({
            "fault": "handoff_interruption",
            "thread_id": 1703,
        }))

        with patch.dict("os.environ", {"OFFICE_M4_TV_TEST_HOOKS": "1"}):
            with self.assertRaisesRegex(ValidationError, "interrupted before Hosted Code Interpreter handoff"):
                raise_handoff_interruption(user_env, 1703)

        self.assertFalse(params.get_param(CONFIG_PARAMETER))

    def test_provider_audit_requires_test_switch_database_absolute_path_and_allowlisted_thread(self):
        """验证 Provider 审计受环境开关、绝对路径和 Thread 白名单约束，且普通用户可通过只读测试门禁。"""
        params = self.env["ir.config_parameter"]
        params.set_param("office_engine.m4_tv.audit_thread_ids", "17,18")
        with patch.dict("os.environ", {
            "OFFICE_M4_TV_OBSERVABILITY": "1",
            "OFFICE_M4_TV_PROVIDER_AUDIT_PATH": "/private/tmp/provider-audit.jsonl",
        }):
            self.assertEqual(provider_audit_thread_id(self.env, 17), 17)
            self.assertIsNone(provider_audit_thread_id(self.env, 19))
            ordinary_user = self.env["res.users"].with_context(no_reset_password=True).create({
                "name": "M4 audit allowlist reader",
                "login": "m4-audit-allowlist-reader-test",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            })
            self.assertEqual(
                provider_audit_thread_id(self.env(user=ordinary_user.id), 17),
                17,
                "A regular Odoo user must pass the test-only audit gate without reading system parameters directly.",
            )
        with patch.dict("os.environ", {
            "OFFICE_M4_TV_OBSERVABILITY": "0",
            "OFFICE_M4_TV_PROVIDER_AUDIT_PATH": "/private/tmp/provider-audit.jsonl",
        }):
            self.assertIsNone(provider_audit_thread_id(self.env, 17))
        with patch.dict("os.environ", {
            "OFFICE_M4_TV_OBSERVABILITY": "1",
            "OFFICE_M4_TV_PROVIDER_AUDIT_PATH": "relative.jsonl",
        }):
            self.assertIsNone(provider_audit_thread_id(self.env, 17))
