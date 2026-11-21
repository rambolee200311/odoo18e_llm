"""恢复 CC-M4-03 已完成 Provider 运行的证据记录并清理隔离夹具。"""

import json
import os
import re
import stat
from pathlib import Path

from odoo.tools import html2plaintext


EVIDENCE_DIR = Path("office_engine/docs/implementation/evidence/CC-M4-03").resolve()
AUDIT_PATH = next(EVIDENCE_DIR.glob("run_*_provider_sdk_audit.jsonl"))
RUN_TAG = AUDIT_PATH.name.removesuffix("_provider_sdk_audit.jsonl")
RESULT_PATH = EVIDENCE_DIR / f"{RUN_TAG}_result.json"
RECOVERY_PATH = EVIDENCE_DIR / f"{RUN_TAG}_cleanup_recovery.json"
AUDIT_PARAMETER = "office_engine.m4_tv.audit_thread_ids"
FAULT_PARAMETER = "office_engine.m4_tv.test_fault"


def _events():
    """读取本轮不含凭据的 Provider SDK 审计轨迹。"""
    return [json.loads(line) for line in AUDIT_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def _message_data(message):
    """抽取消息持久化、静默标记和回执字段。"""
    return {
        "id": message.id,
        "role": message.llm_role or None,
        "body": html2plaintext(message.body or ""),
        "is_error": bool(message.is_error),
        "silent": bool(getattr(message, "llm_silent_retrieval", False)),
        "body_json": message.body_json or {},
    }


def _tool_data(messages):
    """按消息记录 Tool Call 参数与真实执行回执。"""
    rows = []
    for message in messages:
        data = message.body_json or {}
        if message.llm_role == "assistant" and isinstance(data, dict):
            for call in data.get("tool_calls", []):
                rows.append({
                    "kind": "call",
                    "message_id": message.id,
                    "tool_call_id": call.get("id"),
                    "tool_name": (call.get("function") or {}).get("name"),
                    "arguments": (call.get("function") or {}).get("arguments"),
                })
        elif message.llm_role == "tool" and isinstance(data, dict):
            rows.append({
                "kind": "result",
                "message_id": message.id,
                "tool_call_id": data.get("tool_call_id"),
                "tool_name": data.get("tool_name"),
                "status": data.get("status"),
                "error_code": data.get("error_code"),
                "error": data.get("error"),
                "result": data.get("result"),
                "silent": bool(message.llm_silent_retrieval),
            })
    return rows


def _candidate_case_id(text):
    """从本轮合成用户文本提取隔离标记，不读取其他业务记录。"""
    match = re.search(r"CCM403-[a-z_]+-([0-9a-f]{12})", text or "")
    return match.group(1) if match else None


def _current_parameter(env, key):
    """只通过 ORM 读取当前测试开关值。"""
    row = env["ir.config_parameter"].sudo().search([("key", "=", key)], limit=1)
    return {"exists": bool(row), "value": row.value if row else None}


def _disable_parameter(env, key):
    """将本轮测试专用 allowlist / 故障配置清空。"""
    parameter = env["ir.config_parameter"].sudo()
    row = parameter.search([("key", "=", key)], limit=1)
    if row:
        row.write({"value": ""})
    else:
        parameter.create({"key": key, "value": ""})


def run(env):
    """核对 Provider 轨迹与 ORM 结果，随后清理唯一匹配的合成夹具。"""
    if env.cr.dbname != "odoo18e_llm":
        raise RuntimeError(f"拒绝在非授权数据库运行：{env.cr.dbname}")
    sdk = _events()
    thread_ids = sorted({
        thread_id
        for event in sdk
        for thread_id in (event.get("thread_ids") or [])
    })
    threads = env["llm.thread"].browse(thread_ids).exists()
    if len(threads) != 3 or set(threads.ids) != set(thread_ids):
        raise RuntimeError(f"Provider 审计中的 Thread 与开发库不一致：{thread_ids}")

    current_parameters = {
        AUDIT_PARAMETER: _current_parameter(env, AUDIT_PARAMETER),
        FAULT_PARAMETER: _current_parameter(env, FAULT_PARAMETER),
    }
    run_suffix = None
    for event in sdk:
        if event.get("event") != "sdk_request_submitted":
            continue
        for message in event.get("payload", {}).get("messages", []):
            if message.get("role") == "user":
                run_suffix = _candidate_case_id(str(message.get("content") or "")) or run_suffix
    if not run_suffix:
        raise RuntimeError("无法从本轮合成用户消息确认唯一清理标记；停止 ORM 清理。")

    cases = []
    partner_oracle = []
    for thread in threads:
        messages = env["mail.message"].search(
            [("model", "=", "llm.thread"), ("res_id", "=", thread.id)],
            order="id",
        )
        visible_messages = env["mail.message"]._message_fetch(
            [("model", "=", "llm.thread"), ("res_id", "=", thread.id)],
            limit=300,
        )["messages"]
        final = messages.filtered(
            lambda message: message.llm_role == "assistant" and bool(html2plaintext(message.body or "").strip())
        )[-1:]
        request_rows = [
            event for event in sdk
            if event.get("event") == "sdk_request_submitted" and thread.id in (event.get("thread_ids") or [])
        ]
        response_rows = [
            event for event in sdk
            if event.get("event") == "provider_response_received" and thread.id in (event.get("thread_ids") or [])
        ]
        first_user_message = next((
            message
            for event in request_rows
            for message in event.get("payload", {}).get("messages", [])
            if message.get("role") == "user"
        ), {})
        user_text = str(first_user_message.get("content") or "")
        case_match = re.search(r"CCM403-(query_error|access_denial|handoff_failure)-", user_text)
        case_name = case_match.group(1) if case_match else "unknown"
        company_name_match = re.search(r"Synthetic CCM403-[a-z_]+-[0-9a-f]{12} Company", user_text)
        company_name = company_name_match.group(0) if company_name_match else None
        company = env["res.partner"].search([("name", "=", company_name)], limit=1) if company_name else env["res.partner"]
        contacts = env["res.partner"].search(
            [("parent_id", "=", company.id), ("name", "ilike", f"Synthetic CCM403-{case_name}-{run_suffix} Contact")],
            order="id",
        ) if company else env["res.partner"]
        decoy = env["res.partner"].search(
            [("name", "=", f"Synthetic CCM403-{case_name}-{run_suffix} Unrelated Contact")],
            limit=1,
        )
        versions = env["office.workbook.version"].search([("thread_id", "=", thread.id)])
        sessions = env["office.mapping.session"].search([("thread_id", "=", thread.id)])
        tool_rows = _tool_data(messages)
        error_rows = [row for row in tool_rows if row["kind"] == "result" and row["status"] == "error"]
        final_text = html2plaintext(final.body or "") if final else ""
        expected_values = [value for contact in contacts for value in (contact.name, contact.email)]
        cases.append({
            "case": case_name,
            "thread_id": thread.id,
            "user_id": thread.create_uid.id,
            "selected_tool_names": sorted(thread.tool_ids.mapped("name")),
            "provider_request_count": len(request_rows),
            "provider_response_count": len(response_rows),
            "provider_finish_reasons": [
                event.get("response", {}).get("choices", [{}])[0].get("finish_reason")
                for event in response_rows
            ],
            "messages": [_message_data(message) for message in messages],
            "tool_calls_and_results": tool_rows,
            "search_call_count": sum(
                1 for row in tool_rows
                if row["kind"] == "call" and row["tool_name"] == "odoo_record_retriever"
            ),
            "final_assistant_text": final_text,
            "final_assistant_message_id": final.id if final else None,
            "final_assistant_persisted_and_visible_after_refetch": bool(final and final.id in visible_messages.ids),
            "final_answer_contains_expected_values": {value: value in final_text for value in expected_values},
            "retriever_error_ids_visible_as_chat_messages": [
                row["message_id"] for row in error_rows if row["message_id"] in visible_messages.ids
            ],
            "session_ids": sessions.ids,
            "version_ids": versions.ids,
            "oracle": {
                "company_id": company.id if company else None,
                "company_name": company_name,
                "expected_contact_ids": contacts.ids,
                "expected_values": expected_values,
                "decoy_id": decoy.id if decoy else None,
                "decoy_absent_from_final": not decoy or decoy.name not in final_text,
            },
        })
        partner_oracle.extend([record.id for record in (company | contacts | decoy)])

    thread_user_ids = sorted(set(threads.mapped("create_uid").ids))
    users = env["res.users"].browse(thread_user_ids).exists()
    synthetic_partners = env["res.partner"].search([("name", "ilike", f"Synthetic CCM403-%-{run_suffix}%")])
    versions_by_thread = {
        thread.id: env["office.workbook.version"].search([("thread_id", "=", thread.id)]).ids
        for thread in threads
    }
    cleanup = {
        "thread_ids_removed": False,
        "synthetic_partner_ids_removed": False,
        "test_user_ids_removed": False,
        "test_bus_rows_removed": False,
        "audit_allowlist_disabled": False,
        "test_fault_disabled": False,
        "residual_versions_by_thread": versions_by_thread,
        "original_allowlist_value_before_failed_cleanup": "UNKNOWN; runner lost its in-memory snapshot before saving it",
    }
    # 若意外产生版本，不删除其父 Thread，先保留 Candidate / Current 以免丢失副作用证据。
    has_versions = any(versions_by_thread.values())
    if not has_versions:
        threads.unlink()
        sessions = env["office.mapping.session"].search([("thread_id", "in", thread_ids)])
        if sessions:
            sessions.unlink()
        if synthetic_partners:
            synthetic_partners.unlink()
        bus_rows = env["bus.bus"].search([("create_uid", "in", thread_user_ids)])
        if bus_rows:
            bus_rows.unlink()
        for user in users:
            if user.exists():
                user.unlink()
        _disable_parameter(env, AUDIT_PARAMETER)
        _disable_parameter(env, FAULT_PARAMETER)
        env.cr.flush()
        env.cr.commit()
        cleanup.update({
            "thread_ids_removed": not env["llm.thread"].browse(thread_ids).exists(),
            "synthetic_partner_ids_removed": not env["res.partner"].browse(synthetic_partners.ids).exists(),
            "test_user_ids_removed": not env["res.users"].browse(thread_user_ids).exists(),
            "test_bus_rows_removed": not bus_rows.exists(),
            "audit_allowlist_disabled": not _current_parameter(env, AUDIT_PARAMETER)["value"],
            "test_fault_disabled": not _current_parameter(env, FAULT_PARAMETER)["value"],
        })

    sdk_requests = [event for event in sdk if event.get("event") == "sdk_request_submitted"]
    sdk_responses = [event for event in sdk if event.get("event") == "provider_response_received"]
    sdk_errors = [event for event in sdk if event.get("event") == "sdk_request_error"]
    result = {
        "run_tag": RUN_TAG,
        "database": env.cr.dbname,
        "provider": "OpenAI GPT-5.6 Luna",
        "model": "gpt-5.6-luna",
        "thread_ids": thread_ids,
        "provider_request_count": len(sdk_requests),
        "provider_response_count": len(sdk_responses),
        "provider_error_count": len(sdk_errors),
        "provider_sdk_audit_path": str(AUDIT_PATH),
        "fault_audit_path": str(EVIDENCE_DIR / f"{RUN_TAG}_fault_audit.jsonl"),
        "fault_audit_event_count": sum(1 for line in (EVIDENCE_DIR / f"{RUN_TAG}_fault_audit.jsonl").read_text().splitlines() if line.strip()),
        "reported_cases": cases,
        "fault_injection_result": "handoff_interruption hook was not recorded; check exact Tool result and controller path before attributing the final timeout",
        "cleanup": cleanup,
        "harness_issue": "first runner completed Provider calls but raised ValueError while unpacking an auxiliary thread-id list in prior-parameter cleanup; no Provider call was repeated during this analysis",
    }
    RECOVERY_PATH.write_text(json.dumps({
        "run_tag": RUN_TAG,
        "pre_cleanup_parameters": current_parameters,
        "thread_ids": thread_ids,
        "run_suffix": run_suffix,
        "cleanup": cleanup,
    }, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    os.chmod(RECOVERY_PATH, stat.S_IRUSR | stat.S_IWUSR)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    os.chmod(RESULT_PATH, stat.S_IRUSR | stat.S_IWUSR)
    return result


result = run(env)
print(json.dumps({
    "run_tag": result["run_tag"],
    "database": result["database"],
    "provider_request_count": result["provider_request_count"],
    "cases": [
        {
            "case": case["case"],
            "thread_id": case["thread_id"],
            "search_call_count": case["search_call_count"],
            "final_assistant_persisted_and_visible_after_refetch": case["final_assistant_persisted_and_visible_after_refetch"],
            "version_ids": case["version_ids"],
        }
        for case in result["reported_cases"]
    ],
    "cleanup": result["cleanup"],
}, ensure_ascii=False))
