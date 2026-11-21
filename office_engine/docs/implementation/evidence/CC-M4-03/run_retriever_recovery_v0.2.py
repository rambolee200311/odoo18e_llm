"""在隔离合成数据上验证真实 Provider 对 Retriever 结构化错误的只读恢复。"""

import hashlib
import json
import os
import re
import stat
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from odoo.tools import html2plaintext


EVIDENCE_DIR = Path("office_engine/docs/implementation/evidence/CC-M4-03").resolve()
DATABASE = "odoo18e_llm"
MODEL_NAME = "gpt-5.6-luna"
PROVIDER_NAME = "OpenAI GPT-5.6 Luna"
AUDIT_PARAMETER = "office_engine.m4_tv.audit_thread_ids"
RUN_TAG = datetime.now(timezone.utc).strftime("retriever_%Y%m%dT%H%M%SZ")
AUDIT_PATH = EVIDENCE_DIR / f"{RUN_TAG}_provider_sdk_audit.jsonl"
FAULT_PATH = EVIDENCE_DIR / f"{RUN_TAG}_fault_audit.jsonl"
RESULT_PATH = EVIDENCE_DIR / f"{RUN_TAG}_result.json"


def _as_dict(value):
    """把 Odoo 消息的 JSON 字段规范化为字典。"""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, dict) else {}
        except (TypeError, ValueError):
            return {}
    return {}


def _parse_arguments(value):
    """解析 Provider Tool Call 参数；无效参数保留为空字典以便记录原始回执。"""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, dict) else {}
        except (TypeError, ValueError):
            return {}
    return {}


def _tool_rows(messages):
    """提取 Tool Call 与执行回执，供验收逐步核对 Provider 和 Oracle。"""
    rows = []
    for message in messages:
        data = _as_dict(message.body_json)
        if message.llm_role == "assistant":
            for call in data.get("tool_calls", []):
                function = call.get("function") or {}
                rows.append({
                    "kind": "call",
                    "message_id": message.id,
                    "tool_call_id": call.get("id"),
                    "tool_name": function.get("name"),
                    "arguments": _parse_arguments(function.get("arguments")),
                })
        elif message.llm_role == "tool":
            tool_data = _as_dict(message.get_tool_data()) or data
            result = tool_data.get("result")
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except (TypeError, ValueError):
                    pass
            error = tool_data.get("error")
            error_match = re.match(r"^(INVALID_QUERY|FIELD_NOT_FOUND|ACCESS_DENIED|QUERY_FAILED):", str(error or ""))
            rows.append({
                "kind": "result",
                "message_id": message.id,
                "tool_call_id": tool_data.get("tool_call_id"),
                "tool_name": tool_data.get("tool_name"),
                "status": tool_data.get("status"),
                "error": error,
                "error_code": error_match.group(1) if error_match else None,
                "result": result,
                "silent": bool(getattr(message, "llm_silent_retrieval", False)),
            })
    return rows


def _sdk_events(path):
    """读取当前运行的脱敏 Provider 审计事件。"""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path, value):
    """以仅当前用户可读的权限保存测试证据。"""
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def _response_match(final_text, expected, excluded):
    """用独立 Oracle 检查最终答复是否列全目标记录并排除反例。"""
    contains_all = all(name in final_text and email in final_text for name, email in expected)
    excludes_all = all(name not in final_text and (not email or email not in final_text) for name, email in excluded)
    count_claimed = bool(re.search(r"(?:共|总人数|总数|数量|合计)[^\d两]{0,8}(?:2|两)(?:\D|$)", final_text))
    return {
        "all_expected_name_email_pairs_present": contains_all,
        "all_excluded_name_email_pairs_absent": excludes_all,
        "expected_count_two_stated": count_claimed,
        "matches_oracle": contains_all and excludes_all and count_claimed,
    }


def run(env):
    """运行三条相互独立的真实 Provider Thread，并清理其合成业务记录。"""
    if env.cr.dbname != DATABASE:
        raise RuntimeError(f"拒绝在非授权开发库运行：{env.cr.dbname}")
    if any(path.exists() for path in (AUDIT_PATH, FAULT_PATH, RESULT_PATH)):
        raise RuntimeError("拒绝覆盖已经存在的 CC-M4-03 证据文件。")

    case_specs = (
        ("invalid_query_once", "INVALID_QUERY", "once"),
        ("field_not_found_once", "FIELD_NOT_FOUND", "once"),
        ("invalid_query_repeated", "INVALID_QUERY", "persistent"),
    )
    requested_cases = {
        name.strip()
        for name in os.environ.get("OFFICE_M4_TV_RECOVERY_CASES", ",".join(item[0] for item in case_specs)).split(",")
        if name.strip()
    }
    unknown_cases = requested_cases - {item[0] for item in case_specs}
    if unknown_cases or not requested_cases:
        raise RuntimeError(f"未识别或为空的测试分支：{sorted(unknown_cases or requested_cases)}")
    selected_specs = [item for item in case_specs if item[0] in requested_cases]

    model = env["llm.model"].search([("name", "=", MODEL_NAME)], limit=2)
    if len(model) != 1 or model.provider_id.name != PROVIDER_NAME or model.provider_id.service != "openai":
        raise RuntimeError("现有开发库中没有唯一且已配置的 OpenAI GPT-5.6 Luna 模型。")
    retriever = env["llm.tool"].search([("name", "=", "odoo_record_retriever"), ("active", "=", True)], limit=2)
    if len(retriever) != 1:
        raise RuntimeError("现有 Retriever Tool 不唯一或未启用。")

    params = env["ir.config_parameter"].sudo()
    prior_audit = params.search([("key", "=", AUDIT_PARAMETER)], limit=1)
    prior_audit_state = (bool(prior_audit), prior_audit.value if prior_audit else None)
    user = env["res.users"].browse()
    test_partners = env["res.partner"].browse()
    threads = env["llm.thread"].browse()
    cases = []
    result = {
        "run_tag": RUN_TAG,
        "database": env.cr.dbname,
        "provider": PROVIDER_NAME,
        "model": MODEL_NAME,
        "test_design": "Controlled Retriever error cases selected for this run; each uses an independent Thread.",
        "selected_cases": [item[0] for item in selected_specs],
        "oracle_visible_to_provider": False,
        "cases": [],
        "provider_request_count": 0,
        "provider_response_count": 0,
        "provider_error_count": 0,
        "cleanup": None,
    }

    old_environment = {
        key: os.environ.get(key)
        for key in (
            "OFFICE_M4_TV_OBSERVABILITY",
            "OFFICE_M4_TV_PROVIDER_AUDIT_PATH",
        )
    }
    try:
        suffix = uuid4().hex[:12]
        user = env["res.users"].with_context(no_reset_password=True).create({
            "name": f"CC-M4-03 recovery reader {suffix}",
            "login": f"cc-m4-03-recovery-{suffix}@example.invalid",
            "email": f"cc-m4-03-recovery-{suffix}@example.invalid",
            "company_id": env.company.id,
            "company_ids": [(6, 0, [env.company.id])],
            "groups_id": [(6, 0, [env.ref("base.group_user").id, env.ref("llm.group_llm_manager").id])],
            "tz": "UTC",
        })
        for case_name, error_code, mode in selected_specs:
            # 业务名称只用自然的短横线分隔，避免让模型把技术测试标识误当字段值改写。
            marker = f"CCM403-{case_name.replace('_', '-')}-{suffix}"
            company = env["res.partner"].create({"name": f"Synthetic {marker} Company", "is_company": True, "active": True})
            other_company = env["res.partner"].create({"name": f"Synthetic {marker} Other Company", "is_company": True, "active": True})
            matches = env["res.partner"].create([
                {"name": f"Synthetic {marker} Alpha", "parent_id": company.id, "is_company": False, "active": True, "email": f"{marker.lower()}-alpha@example.invalid"},
                {"name": f"Synthetic {marker} Beta", "parent_id": company.id, "is_company": False, "active": True, "email": f"{marker.lower()}-beta@example.invalid"},
            ])
            excluded = env["res.partner"].create([
                {"name": f"Synthetic {marker} No Email", "parent_id": company.id, "is_company": False, "active": True, "email": False},
                {"name": f"Synthetic {marker} Archived", "parent_id": company.id, "is_company": False, "active": False, "email": f"{marker.lower()}-archived@example.invalid"},
                {"name": f"Synthetic {marker} Other Parent", "parent_id": other_company.id, "is_company": False, "active": True, "email": f"{marker.lower()}-other@example.invalid"},
            ])
            test_partners |= company | other_company | matches | excluded
            read_env = env(user=user.id)
            oracle_domain = [
                ("parent_id", "=", company.id),
                ("is_company", "=", False),
                ("active", "=", True),
                ("email", "!=", False),
            ]
            oracle_records = read_env["res.partner"].search(oracle_domain, order="id asc")
            if set(oracle_records.ids) != set(matches.ids):
                raise RuntimeError(f"合成数据 Oracle 不匹配；未调用 Provider：{case_name}")
            expected_pairs = [(record.name, record.email) for record in matches]
            excluded_pairs = [(record.name, record.email or "") for record in excluded]
            thread = env["llm.thread"].with_user(user).create({
                "name": f"CC-M4-03 Retriever recovery {case_name} {suffix}",
                "provider_id": model.provider_id.id,
                "model_id": model.id,
                "tool_ids": [(6, 0, retriever.ids)],
            })
            threads |= thread
            cases.append({
                "case": case_name,
                "error_code": error_code,
                "injection_mode": mode,
                "thread": thread,
                "company_id": company.id,
                "company_name": company.name,
                "expected_ids": matches.ids,
                "expected_pairs": expected_pairs,
                "excluded_ids": excluded.ids,
                "excluded_pairs": excluded_pairs,
                "injected_error_count": 0,
            })

        AUDIT_PATH.write_text("", encoding="utf-8")
        FAULT_PATH.write_text("", encoding="utf-8")
        os.chmod(AUDIT_PATH, stat.S_IRUSR | stat.S_IWUSR)
        os.chmod(FAULT_PATH, stat.S_IRUSR | stat.S_IWUSR)
        os.environ["OFFICE_M4_TV_OBSERVABILITY"] = "1"
        os.environ["OFFICE_M4_TV_PROVIDER_AUDIT_PATH"] = str(AUDIT_PATH)
        env.cr.commit()

        original_execute = type(env["mail.message"])._execute_tool_with_context
        current_case = {"value": None}

        def guarded_execute(message, tool_name, arguments_str, thread_model=None):
            """仅对本轮 Retriever search 调用追加一次性或持续性测试错误参数。"""
            case = current_case["value"]
            if not case or tool_name != "odoo_record_retriever":
                return original_execute(message, tool_name, arguments_str, thread_model=thread_model)
            try:
                arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else dict(arguments_str or {})
            except (TypeError, ValueError):
                arguments = {}
            is_search = arguments.get("operation") == "search" or (
                arguments.get("operation") is None and isinstance(arguments.get("model"), str)
            )
            if not is_search:
                return original_execute(message, tool_name, arguments_str, thread_model=thread_model)
            if case["injection_mode"] == "once" and case["injected_error_count"]:
                return original_execute(message, tool_name, arguments_str, thread_model=thread_model)

            injected = dict(arguments)
            if case["error_code"] == "INVALID_QUERY":
                # 让真实 Retriever 校验器因 search 收到 discover 专属参数而返回原生 INVALID_QUERY。
                injected["query"] = f"controlled-test-invalid-query-{case['case']}"
            else:
                # 追加仅在本次执行中出现的随机不存在字段，触发真实字段校验而不触碰 ORM 记录。
                injected["fields"] = list(injected.get("fields") or []) + [f"cc_m4_missing_{uuid4().hex[:10]}"]
            case["injected_error_count"] += 1
            fault = {
                "case": case["case"],
                "thread_id": thread_model.id if thread_model else None,
                "tool_call_id": (message.get_tool_data() or {}).get("tool_call_id"),
                "error_code": case["error_code"],
                "provider_arguments_sha256": hashlib.sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest(),
                "injected_arguments_sha256": hashlib.sha256(json.dumps(injected, sort_keys=True).encode()).hexdigest(),
                "provider_arguments": arguments,
                "retriever_execution_arguments": injected,
                "injection_index": case["injected_error_count"],
                "mode": case["injection_mode"],
                "orm_business_query_executed": False,
            }
            with FAULT_PATH.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(fault, ensure_ascii=False, sort_keys=True) + "\n")
            os.chmod(FAULT_PATH, stat.S_IRUSR | stat.S_IWUSR)
            return original_execute(
                message,
                tool_name,
                json.dumps(injected, ensure_ascii=False),
                thread_model=thread_model,
            )

        with patch.object(type(env["mail.message"]), "_execute_tool_with_context", guarded_execute):
            for case in cases:
                thread = case["thread"]
                params.set_param(AUDIT_PARAMETER, str(thread.id))
                env.cr.commit()
                current_case["value"] = case
                prompt = (
                    f"请查找公司《{case['company_name']}》名下的直接联系人，只列出仍启用且填写了邮箱的联系人，"
                    "给出总人数以及每个人的姓名和邮箱；不要包含没有邮箱或已归档的记录。"
                )
                started = time.perf_counter()
                execution_error = None
                try:
                    events = list(thread.generate(user_message_body=prompt, attachment_ids=[]))
                    env.cr.commit()
                except Exception as exc:
                    execution_error = {"type": type(exc).__name__, "message": str(exc)[:800]}
                    events = []
                    env.cr.rollback()
                elapsed = round(time.perf_counter() - started, 3)
                thread.invalidate_recordset()
                messages = env["mail.message"].search([("model", "=", "llm.thread"), ("res_id", "=", thread.id)], order="id")
                visible = env["mail.message"]._message_fetch(
                    [("model", "=", "llm.thread"), ("res_id", "=", thread.id)], limit=300
                )["messages"]
                final = messages.filtered(
                    lambda item: item.llm_role == "assistant" and bool(html2plaintext(item.body or "").strip())
                )[-1:]
                final_text = html2plaintext(final.body or "") if final else ""
                rows = _tool_rows(messages)
                search_calls = [
                    row for row in rows
                    if row["kind"] == "call" and row["tool_name"] == "odoo_record_retriever"
                    and (
                        row["arguments"].get("operation") == "search"
                        or (row["arguments"].get("operation") is None and isinstance(row["arguments"].get("model"), str))
                    )
                ]
                injected_errors = [
                    row for row in rows
                    if row["kind"] == "result" and row["tool_name"] == "odoo_record_retriever"
                    and row["error_code"] == case["error_code"]
                ]
                successful_search_results = [
                    row for row in rows
                    if row["kind"] == "result"
                    and row["tool_name"] == "odoo_record_retriever"
                    and row["status"] == "completed"
                    and isinstance(row.get("result"), dict)
                    and (
                        row["result"].get("operation") == "search"
                        or ("records" in row["result"] and "count" in row["result"])
                    )
                ]
                sdk_events = [
                    event for event in _sdk_events(AUDIT_PATH)
                    if thread.id in (event.get("thread_ids") or [])
                ]
                sdk_requests = [event for event in sdk_events if event.get("event") == "sdk_request_submitted"]
                sdk_responses = [event for event in sdk_events if event.get("event") == "provider_response_received"]
                case_result = {
                    "case": case["case"],
                    "thread_id": thread.id,
                    "user_id": user.id,
                    "tools": sorted(thread.tool_ids.mapped("name")),
                    "prompt": prompt,
                    "elapsed_seconds": elapsed,
                    "execution_error": execution_error,
                    "event_types": [event.get("type") for event in events if isinstance(event, dict)],
                    "provider_request_count": len(sdk_requests),
                    "provider_response_count": len(sdk_responses),
                    "provider_error_events": [
                        {key: event.get(key) for key in ("event", "request_id", "error_type", "error") if key in event}
                        for event in sdk_events if event.get("event") == "sdk_request_error"
                    ],
                    "provider_request_ids": [event.get("request_id") for event in sdk_requests],
                    "provider_response_ids": [event.get("request_id") for event in sdk_responses],
                    "tool_calls_and_results": rows,
                    "retriever_search_call_count": len(search_calls),
                    "injected_error_count": case["injected_error_count"],
                    "retriever_error_codes_returned": [row["error_code"] for row in injected_errors],
                    "successful_retriever_search_result_count": len(successful_search_results),
                    "final_assistant_text": final_text,
                    "final_assistant_message_id": final.id if final else None,
                    "final_assistant_persisted_and_visible_after_refetch": bool(final and final.id in visible.ids),
                    "oracle_check": _response_match(final_text, case["expected_pairs"], case["excluded_pairs"]),
                    "oracle": {
                        "expected_ids": case["expected_ids"],
                        "excluded_ids": case["excluded_ids"],
                        "expected_pairs": case["expected_pairs"],
                    },
                    "query_argument_review_required": True,
                }
                case_result["status"] = "PASS" if (
                    execution_error is None
                    and case["injected_error_count"] >= 1
                    and case_result["oracle_check"]["matches_oracle"]
                    and case_result["final_assistant_persisted_and_visible_after_refetch"]
                ) else "FAIL"
                if len(sdk_responses) < len(sdk_requests):
                    case_result["status"] = "BLOCKED"
                    case_result["blocked_reason"] = "Provider request timed out or disconnected before a response; Agent decision not fully observable."
                if case["case"] == "invalid_query_repeated":
                    stopped_with_failure = bool(re.search(
                        r"(无法|未能|不能|失败|未完成|无法确认|unable|cannot|can't|could not|failed|not completed)",
                        final_text,
                        re.IGNORECASE,
                    ))
                    case_result["retry_bound_check"] = {
                        "initial_error_plus_max_two_corrections": case["injected_error_count"] <= 3,
                        "stopped_after_repeated_invalid_query": bool(injected_errors and stopped_with_failure),
                        "no_business_search_succeeded_after_persistent_injection": len(successful_search_results) == 0,
                        "search_call_count": len(search_calls),
                        "injected_error_count": case["injected_error_count"],
                    }
                    if not all(case_result["retry_bound_check"].values()):
                        case_result["status"] = "FAIL"
                    else:
                        case_result["status"] = "PASS"
                case["result"] = case_result
                result["cases"].append(case_result)
                _write_json(RESULT_PATH, result)

        sdk_events = _sdk_events(AUDIT_PATH)
        result["provider_request_count"] = sum(event.get("event") == "sdk_request_submitted" for event in sdk_events)
        result["provider_response_count"] = sum(event.get("event") == "provider_response_received" for event in sdk_events)
        result["provider_error_count"] = sum(event.get("event") == "sdk_request_error" for event in sdk_events)
        result["provider_sdk_audit_path"] = str(AUDIT_PATH)
        result["fault_audit_path"] = str(FAULT_PATH)
        statuses = [case.get("result", {}).get("status") for case in cases]
        if statuses and all(status == "PASS" for status in statuses):
            result["status"] = "PASS"
        elif "BLOCKED" in statuses:
            result["status"] = "BLOCKED"
        else:
            result["status"] = "FAIL"
    finally:
        current_case = {"value": None}
        if prior_audit_state[0]:
            params.set_param(AUDIT_PARAMETER, prior_audit_state[1] or "")
        else:
            prior_audit.unlink()
        for key, value in old_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        env.cr.commit()

        # 仅清理本脚本创建的 Thread 与合成业务数据；测试用户因用量审计外键而停用保留。
        unexpected_versions = env["office.workbook.version"].search([("thread_id", "in", threads.ids)])
        unexpected_sessions = env["office.mapping.session"].search([("thread_id", "in", threads.ids)])
        if not unexpected_versions and not unexpected_sessions:
            if threads:
                threads.unlink()
            if test_partners:
                test_partners.filtered(lambda partner: bool(partner.parent_id)).unlink()
                test_partners.exists().unlink()
            if user and user.active:
                user.write({"active": False})
                user.partner_id.write({"active": False})
            env.cr.commit()
            cleanup = {
                "threads_removed": not threads.exists(),
                "synthetic_business_partners_removed": not test_partners.exists(),
                "synthetic_user_deactivated": bool(user and not user.active),
                "test_versions": unexpected_versions.ids,
                "test_sessions": unexpected_sessions.ids,
                "retriever_audit_allowlist_restored": True,
            }
        else:
            cleanup = {
                "threads_preserved_due_to_unexpected_office_state": threads.ids,
                "synthetic_business_partners_preserved": test_partners.ids,
                "synthetic_user_deactivated": False,
                "test_versions": unexpected_versions.ids,
                "test_sessions": unexpected_sessions.ids,
                "retriever_audit_allowlist_restored": True,
            }
        result["cleanup"] = cleanup
        _write_json(RESULT_PATH, result)
    return result


if __name__ == "__main__":
    print(json.dumps(run(env), ensure_ascii=False, indent=2, default=str))
