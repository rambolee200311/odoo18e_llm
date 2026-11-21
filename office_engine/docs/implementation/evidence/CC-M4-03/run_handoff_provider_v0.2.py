"""用单个隔离 Thread 复验真实 Provider 的 handoff 故障恢复。"""

import json
import os
import stat
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from odoo.tools import html2plaintext


EVIDENCE_DIR = Path("office_engine/docs/implementation/evidence/CC-M4-03").resolve()
DATABASE = "odoo18e_llm"
MODEL_NAME = "gpt-5.6-luna"
AUDIT_PARAMETER = "office_engine.m4_tv.audit_thread_ids"
FAULT_PARAMETER = "office_engine.m4_tv.test_fault"
RUN_TAG = datetime.now(timezone.utc).strftime("handoff_%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
AUDIT_PATH = EVIDENCE_DIR / f"{RUN_TAG}_provider_sdk_audit.jsonl"
FAULT_AUDIT_PATH = EVIDENCE_DIR / f"{RUN_TAG}_fault_audit.jsonl"
RESULT_PATH = EVIDENCE_DIR / f"{RUN_TAG}_result.json"


def _message_row(message):
    """提取 Thread 消息、静默标记和内部工具回执。"""
    body_json = message.body_json or {}
    row = {
        "id": message.id,
        "role": message.llm_role or None,
        "body": html2plaintext(message.body or ""),
        "is_error": bool(message.is_error),
        "silent": bool(getattr(message, "llm_silent_retrieval", False)),
    }
    if isinstance(body_json, dict):
        for key in ("status", "error_code", "error", "tool_call_id", "tool_name", "result"):
            if key in body_json:
                row[key] = body_json[key]
        row["tool_calls"] = body_json.get("tool_calls", [])
    return row


def _events(path):
    """读取本次生成的 Provider 审计 JSONL。"""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run(env):
    """创建隔离业务数据，完成一次真实 Provider 交互并可靠收尾。"""
    if env.cr.dbname != DATABASE:
        raise RuntimeError(f"拒绝在未授权数据库运行：{env.cr.dbname}")
    model = env["llm.model"].search([("name", "=", MODEL_NAME)], limit=2)
    if len(model) != 1 or model.provider_id.service != "openai":
        raise RuntimeError("现有开发库中没有唯一的 GPT-5.6 Luna OpenAI Model。")
    retriever = env["llm.tool"].search([("name", "=", "odoo_record_retriever"), ("active", "=", True)], limit=2)
    office = env["llm.tool"].search([("name", "=", "office"), ("active", "=", True)], limit=2)
    if len(retriever) != 1 or len(office) != 1:
        raise RuntimeError("Retriever / Office 公开工具不存在或不唯一。")

    suffix = uuid4().hex[:12]
    marker = f"CCM403-handoff-{suffix}"
    params = env["ir.config_parameter"].sudo()
    prior_params = {
        key: params.get_param(key)
        for key in (AUDIT_PARAMETER, FAULT_PARAMETER)
    }
    old_environment = {
        key: os.environ.get(key)
        for key in (
            "OFFICE_M4_TV_OBSERVABILITY",
            "OFFICE_M4_TV_PROVIDER_AUDIT_PATH",
            "OFFICE_M4_TV_TEST_HOOKS",
            "OFFICE_M4_TV_FAULT_AUDIT_PATH",
        )
    }
    user = env["res.users"].browse()
    partners = env["res.partner"].browse()
    thread = env["llm.thread"].browse()
    thread_id = None
    kept_for_side_effect = False
    record = None

    try:
        user = env["res.users"].with_context(no_reset_password=True).create({
            "name": f"CC-M4-03 synthetic reader {suffix}",
            "login": f"cc-m4-03-{suffix}@example.invalid",
            "email": f"cc-m4-03-{suffix}@example.invalid",
            "company_id": env.company.id,
            "company_ids": [(6, 0, [env.company.id])],
            "groups_id": [(6, 0, [env.ref("base.group_user").id, env.ref("llm.group_llm_manager").id])],
            "tz": "UTC",
        })
        company = env["res.partner"].create({
            "name": f"Synthetic {marker} Company",
            "is_company": True,
            "active": True,
        })
        contacts = env["res.partner"].create([
            {
                "name": f"Synthetic {marker} Contact {index}",
                "parent_id": company.id,
                "is_company": False,
                "active": True,
                "email": f"{marker.lower()}-{index}@example.invalid",
            }
            for index in (1, 2)
        ])
        decoy = env["res.partner"].create({
            "name": f"Synthetic {marker} Unrelated Contact",
            "is_company": False,
            "active": True,
            "email": f"{marker.lower()}-decoy@example.invalid",
        })
        partners = company | contacts | decoy
        if set(env["res.partner"].with_user(user).browse(partners.ids).exists().ids) != set(partners.ids):
            raise RuntimeError("普通测试用户无权读取隔离夹具；不调用 Provider。")

        thread = env["llm.thread"].with_user(user).create({
            "name": f"CC-M4-03 handoff interruption {suffix}",
            "provider_id": model.provider_id.id,
            "model_id": model.id,
            "tool_ids": [(6, 0, (retriever | office).ids)],
        })
        thread_id = thread.id
        request_text = (
            f"请将公司 Synthetic {marker} Company 名下直接联系人的姓名和邮箱导出为 Excel，"
            "只包含直接隶属的联系人，不要包含无关联系人。"
        )

        # 提交隔离夹具后，按唯一 Thread 配置一次性故障；测试脚本独立保存原值以便恢复。
        params.set_param(AUDIT_PARAMETER, str(thread_id))
        params.set_param(FAULT_PARAMETER, json.dumps({"fault": "handoff_interruption", "thread_id": thread_id}))
        AUDIT_PATH.write_text("", encoding="utf-8")
        FAULT_AUDIT_PATH.write_text("", encoding="utf-8")
        for path in (AUDIT_PATH, FAULT_AUDIT_PATH):
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        os.environ["OFFICE_M4_TV_OBSERVABILITY"] = "1"
        os.environ["OFFICE_M4_TV_PROVIDER_AUDIT_PATH"] = str(AUDIT_PATH)
        os.environ["OFFICE_M4_TV_TEST_HOOKS"] = "1"
        os.environ["OFFICE_M4_TV_FAULT_AUDIT_PATH"] = str(FAULT_AUDIT_PATH)
        env.cr.commit()

        started = time.perf_counter()
        sse_events = list(thread.generate(user_message_body=request_text, attachment_ids=[]))
        elapsed = round(time.perf_counter() - started, 3)
        # 模拟完整请求正常结束：显式测试事务提交确保最终 mail.message 不被脚本清理阶段回滚。
        env.cr.commit()

        thread.invalidate_recordset()
        messages = env["mail.message"].search(
            [("model", "=", "llm.thread"), ("res_id", "=", thread.id)], order="id"
        )
        visible = env["mail.message"]._message_fetch(
            [("model", "=", "llm.thread"), ("res_id", "=", thread.id)], limit=300
        )["messages"]
        versions = env["office.workbook.version"].search([("thread_id", "=", thread.id)])
        sdk = _events(AUDIT_PATH)
        fault_events = [line for line in FAULT_AUDIT_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        final = messages.filtered(
            lambda message: message.llm_role == "assistant" and bool(html2plaintext(message.body or "").strip())
        )[-1:]
        tool_rows = [
            _message_row(message)
            for message in messages
            if message.llm_role == "tool"
        ]
        record = {
            "run_tag": RUN_TAG,
            "database": env.cr.dbname,
            "provider": model.provider_id.name,
            "model": model.name,
            "thread_id": thread.id,
            "user_id": user.id,
            "selected_tools": sorted(thread.tool_ids.mapped("name")),
            "elapsed_seconds": elapsed,
            "sse_event_types": [event.get("type") for event in sse_events if isinstance(event, dict)],
            "provider_request_count": sum(event.get("event") == "sdk_request_submitted" for event in sdk),
            "provider_response_count": sum(event.get("event") == "provider_response_received" for event in sdk),
            "provider_error_count": sum(event.get("event") == "sdk_request_error" for event in sdk),
            "prior_test_parameters": prior_params,
            "provider_audit_path": str(AUDIT_PATH),
            "fault_audit_path": str(FAULT_AUDIT_PATH),
            "fault_audit_events": [json.loads(line) for line in fault_events],
            "tool_results": tool_rows,
            "final_message": _message_row(final) if final else None,
            "final_assistant_message_persisted_and_visible_after_refetch": bool(final and final.id in visible.ids),
            "version_rows": [
                {"id": version.id, "state": version.state, "output_attachment_id": version.output_attachment_id.id,
                 "final_attachment_id": version.final_attachment_id.id, "delivery_state": version.delivery_state}
                for version in versions
            ],
            "oracle": {
                "company_id": company.id,
                "expected_contact_ids": contacts.ids,
                "expected_contact_count": len(contacts),
                "decoy_id": decoy.id,
                "decoy_not_requested": True,
            },
            "result": "RECORDED; determine PASS/FAIL against CC-M4-03-TEST-006 and TEST-001 from actual records",
        }
        RESULT_PATH.write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        os.chmod(RESULT_PATH, stat.S_IRUSR | stat.S_IWUSR)
        if versions:
            kept_for_side_effect = True
        return record
    finally:
        # 先恢复服务器开关；绝不把测试 allowlist 或故障留给后续业务请求。
        for key, value in prior_params.items():
            params.set_param(key, value or "")
        for key, value in old_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        env.cr.commit()

        # 只有确认未产生 Office 版本副作用时才删除本次隔离 Thread 和记录。
        if thread_id and not kept_for_side_effect:
            version_rows = env["office.workbook.version"].search([("thread_id", "=", thread_id)])
            if not version_rows:
                thread = env["llm.thread"].browse(thread_id).exists()
                if thread:
                    thread.unlink()
                if partners.exists():
                    partners.filtered(lambda partner: partner.parent_id).unlink()
                    partners.exists().unlink()
                bus_rows = env["bus.bus"].search([("create_uid", "=", user.id)])
                if bus_rows:
                    bus_rows.unlink()
                if user.exists():
                    # Provider 使用量保留 owner 外键；停用本轮合成用户，不删除使用量记录。
                    user.write({"active": False})
                    user.partner_id.write({"active": False})
                env.cr.commit()
                if record is not None:
                    record["cleanup"] = {
                        "thread_removed": not env["llm.thread"].browse(thread_id).exists(),
                        "synthetic_partners_removed": not partners.exists(),
                        "test_user_deactivated": bool(user and not user.active),
                        "test_user_partner_deactivated": bool(user and not user.partner_id.active),
                    }
                    RESULT_PATH.write_text(
                        json.dumps(record, ensure_ascii=False, indent=2, default=str) + "\n",
                        encoding="utf-8",
                    )
                    os.chmod(RESULT_PATH, stat.S_IRUSR | stat.S_IWUSR)
        elif record is not None:
            record["cleanup"] = {
                "thread_preserved_for_side_effect": True,
                "synthetic_partners_preserved": True,
                "test_user_deactivated": bool(user and not user.active),
            }
            if user.exists() and user.active:
                user.write({"active": False})
            if user.exists() and user.partner_id.active:
                user.partner_id.write({"active": False})
            if user.exists():
                env.cr.commit()
            record["cleanup"]["test_user_deactivated"] = bool(user and not user.active)
            record["cleanup"]["test_user_partner_deactivated"] = bool(user and not user.partner_id.active)
            RESULT_PATH.write_text(
                json.dumps(record, ensure_ascii=False, indent=2, default=str) + "\n",
                encoding="utf-8",
            )
            os.chmod(RESULT_PATH, stat.S_IRUSR | stat.S_IWUSR)


result = run(env)
print(json.dumps({
    "run_tag": result["run_tag"],
    "database": result["database"],
    "thread_id": result["thread_id"],
    "provider_requests": result["provider_request_count"],
    "provider_responses": result["provider_response_count"],
    "fault_audit_events": result["fault_audit_events"],
    "final_persisted_and_visible": result["final_assistant_message_persisted_and_visible_after_refetch"],
    "versions": result["version_rows"],
}, ensure_ascii=False, default=str))
