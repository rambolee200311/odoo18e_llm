"""在现有开发库用真实 GPT-5.6 Luna 验证最终失败交付与只读错误处置。"""

import json
import os
import re
import stat
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from odoo.exceptions import UserError
from odoo.tools import html2plaintext


EVIDENCE_DIR = Path("office_engine/docs/implementation/evidence/CC-M4-03").resolve()
DATABASE = "odoo18e_llm"
PROVIDER_NAME = "OpenAI GPT-5.6 Luna"
MODEL_NAME = "gpt-5.6-luna"
AUDIT_PARAMETER = "office_engine.m4_tv.audit_thread_ids"
FAULT_PARAMETER = "office_engine.m4_tv.test_fault"
RUN_TAG = datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
AUDIT_PATH = EVIDENCE_DIR / f"{RUN_TAG}_provider_sdk_audit.jsonl"
RESULT_PATH = EVIDENCE_DIR / f"{RUN_TAG}_result.json"
RECOVERY_PATH = EVIDENCE_DIR / f"{RUN_TAG}_recovery.json"


def _record_snapshot(message):
    """提取合成 Thread 消息，以核对内部回执和用户可见最终答复。"""
    return {
        "id": message.id,
        "role": message.llm_role or None,
        "body": html2plaintext(message.body or ""),
        "is_error": bool(message.is_error),
        "silent": bool(getattr(message, "llm_silent_retrieval", False)),
        "body_json": message.body_json or {},
    }


def _tool_rows(messages):
    """从持久化消息收集 Tool Call、执行参数和实际回执。"""
    rows = []
    for message in messages:
        data = message.body_json or {}
        if message.llm_role == "assistant":
            for call in data.get("tool_calls", []) if isinstance(data, dict) else []:
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


def _sdk_events(path):
    """读取此轮脱敏 Provider SDK 审计事件。"""
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run(env):
    """创建合成夹具、运行三条独立 Provider Thread，并在 finally 中清理。"""
    if env.cr.dbname != DATABASE:
        raise RuntimeError(f"拒绝在非授权数据库运行：{env.cr.dbname}")
    if AUDIT_PATH.exists() or RESULT_PATH.exists():
        raise RuntimeError("拒绝覆盖已存在的 CC-M4-03 Provider 证据。")

    model = env["llm.model"].search([("name", "=", MODEL_NAME)], limit=2)
    if (
        len(model) != 1
        or model.provider_id.name != PROVIDER_NAME
        or model.provider_id.service != "openai"
    ):
        raise RuntimeError("现有开发库中未找到唯一获批的 GPT-5.6 Luna Provider。")
    provider = model.provider_id
    retriever = env["llm.tool"].search([("name", "=", "odoo_record_retriever"), ("active", "=", True)], limit=2)
    office = env["llm.tool"].search([("name", "=", "office"), ("active", "=", True)], limit=2)
    if len(retriever) != 1 or len(office) != 1:
        raise RuntimeError("现有 Retriever 或 Office 工具不唯一 / 未启用。")

    suffix = uuid4().hex[:12]
    created = {
        "user": env["res.users"].browse(),
        "user_partner": env["res.partner"].browse(),
        "partners": env["res.partner"].browse(),
        "threads": env["llm.thread"].browse(),
        "bus_ids_before": set(env["bus.bus"].search([]).ids),
        "prior_params": {},
    }
    parameter_model = env["ir.config_parameter"].sudo()
    for key in (AUDIT_PARAMETER, FAULT_PARAMETER):
        record = parameter_model.search([("key", "=", key)], limit=1)
        created["prior_params"][key] = (bool(record), record.value if record else None)

    user = env["res.users"].with_context(no_reset_password=True).create({
        "name": f"CC-M4-03 synthetic reader {suffix}",
        "login": f"cc-m4-03-{suffix}@example.invalid",
        "email": f"cc-m4-03-{suffix}@example.invalid",
        "company_id": env.company.id,
        "company_ids": [(6, 0, [env.company.id])],
        "groups_id": [(6, 0, [
            env.ref("base.group_user").id,
            env.ref("llm.group_llm_manager").id,
        ])],
        "tz": "UTC",
    })
    created["user"] = user
    created["user_partner"] = user.partner_id
    FixturePartner = env["res.partner"]
    ReadPartner = FixturePartner.with_user(user)
    cases = []
    for case_name in ("query_error", "access_denial", "handoff_failure"):
        marker = f"CCM403-{case_name}-{suffix}"
        company = FixturePartner.create({
            "name": f"Synthetic {marker} Company",
            "is_company": True,
            "active": True,
        })
        contacts = FixturePartner.create([
            {
                "name": f"Synthetic {marker} Contact {index}",
                "parent_id": company.id,
                "is_company": False,
                "active": True,
                "email": f"{marker.lower()}-{index}@example.invalid",
            }
            for index in (1, 2)
        ])
        decoy = FixturePartner.create({
            "name": f"Synthetic {marker} Unrelated Contact",
            "is_company": False,
            "active": True,
            "email": f"{marker.lower()}-decoy@example.invalid",
        })
        created["partners"] |= company | contacts | decoy
        if set(ReadPartner.browse((company | contacts | decoy).ids).exists().ids) != set((company | contacts | decoy).ids):
            raise RuntimeError("普通内部测试用户不能读取全部合成夹具；拒绝启动 Provider。")
        tools = retriever | (office if case_name == "handoff_failure" else env["llm.tool"].browse())
        thread = env["llm.thread"].with_user(user).create({
            "name": f"CC-M4-03 {case_name} {suffix}",
            "provider_id": provider.id,
            "model_id": model.id,
            "tool_ids": [(6, 0, tools.ids)],
        })
        created["threads"] |= thread
        cases.append({
            "case": case_name,
            "marker": marker,
            "company_id": company.id,
            "company_name": company.name,
            "expected_contact_ids": contacts.ids,
            "expected_values": [value for contact in contacts for value in (contact.name, contact.email)],
            "decoy_id": decoy.id,
            "thread": thread,
            "inject": case_name,
        })

    thread_ids = [case["thread"].id for case in cases]
    parameter_model.set_param(AUDIT_PARAMETER, ",".join(map(str, thread_ids)))
    parameter_model.set_param(FAULT_PARAMETER, "")
    RECOVERY_PATH.write_text(json.dumps({
        "run_tag": RUN_TAG,
        "database": env.cr.dbname,
        "thread_ids": thread_ids,
        "user_id": user.id,
        "prior_parameters": {
            key: {"existed": existed, "value": value}
            for key, (existed, value) in created["prior_params"].items()
        },
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(RECOVERY_PATH, stat.S_IRUSR | stat.S_IWUSR)

    old_env = {
        key: os.environ.get(key)
        for key in (
            "OFFICE_M4_TV_OBSERVABILITY",
            "OFFICE_M4_TV_PROVIDER_AUDIT_PATH",
            "OFFICE_M4_TV_TEST_HOOKS",
            "OFFICE_M4_TV_FAULT_AUDIT_PATH",
        )
    }
    os.environ["OFFICE_M4_TV_OBSERVABILITY"] = "1"
    os.environ["OFFICE_M4_TV_PROVIDER_AUDIT_PATH"] = str(AUDIT_PATH)
    os.environ["OFFICE_M4_TV_TEST_HOOKS"] = "1"
    fault_audit_path = EVIDENCE_DIR / f"{RUN_TAG}_fault_audit.jsonl"
    os.environ["OFFICE_M4_TV_FAULT_AUDIT_PATH"] = str(fault_audit_path)
    AUDIT_PATH.write_text("", encoding="utf-8")
    fault_audit_path.write_text("", encoding="utf-8")
    os.chmod(AUDIT_PATH, stat.S_IRUSR | stat.S_IWUSR)
    os.chmod(fault_audit_path, stat.S_IRUSR | stat.S_IWUSR)

    original_execute = type(env["mail.message"])._execute_tool_with_context
    injected_calls = {case["thread"].id: 0 for case in cases}
    results = []
    failure = None

    def guarded_execute(message, tool_name, arguments_str, thread_model=None):
        """仅对指定 Thread 的首个 Retriever search 注入一次受控错误。"""
        thread_id = thread_model.id if thread_model and thread_model._name == "llm.thread" else None
        case = next((item for item in cases if item["thread"].id == thread_id), None)
        if case and tool_name == "odoo_record_retriever":
            try:
                args = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
            except (TypeError, ValueError):
                args = {}
            if args.get("operation") == "search":
                if case["case"] == "query_error" and injected_calls[thread_id] == 0:
                    injected_calls[thread_id] += 1
                    raise UserError(
                        "QUERY_FAILED: CC-M4-03 isolated one-shot read interruption; no ORM query was executed."
                    )
                if case["case"] == "access_denial" and injected_calls[thread_id] == 0:
                    injected_calls[thread_id] += 1
                    raise UserError("ACCESS_DENIED: CC-M4-03 isolated read denial for this test Thread.")
        return original_execute(message, tool_name, arguments_str, thread_model=thread_model)

    try:
        # 夹具与 allowlist 先提交；后续 Provider / Tool 事务可能按上游行为提交。
        env.cr.commit()
        with patch.object(type(env["mail.message"]), "_execute_tool_with_context", guarded_execute):
            for case in cases:
                thread = case["thread"]
                if case["case"] == "query_error":
                    prompt = (
                        f"请只统计公司 {case['company_name']} 名下直接联系人的数量，并列出每个人的姓名和邮箱；"
                        "不要创建或修改文件。"
                    )
                elif case["case"] == "access_denial":
                    prompt = (
                        f"请只列出公司 {case['company_name']} 名下直接联系人的姓名和邮箱；"
                        "不要创建或修改文件。"
                    )
                else:
                    prompt = (
                        f"请将公司 {case['company_name']} 名下直接联系人的姓名和邮箱导出为 Excel，"
                        "只包含直接隶属的联系人，不要包含无关联系人。"
                    )
                    parameter_model.set_param(FAULT_PARAMETER, json.dumps({
                        "fault": "handoff_interruption",
                        "thread_id": thread.id,
                    }))
                    env.cr.commit()

                started = time.perf_counter()
                events = list(thread.generate(user_message_body=prompt, attachment_ids=[]))
                elapsed = round(time.perf_counter() - started, 3)
                thread.invalidate_recordset()
                messages = env["mail.message"].search(
                    [("model", "=", "llm.thread"), ("res_id", "=", thread.id)],
                    order="id",
                )
                visible = env["mail.message"]._message_fetch(
                    [("model", "=", "llm.thread"), ("res_id", "=", thread.id)],
                    limit=200,
                )["messages"]
                final_assistant = messages.filtered(
                    lambda item: item.llm_role == "assistant" and bool(html2plaintext(item.body or "").strip())
                )[-1:]
                snapshots = [_record_snapshot(message) for message in messages]
                tool_records = _tool_rows(messages)
                final_text = html2plaintext(final_assistant.body or "") if final_assistant else ""
                visible_final = bool(final_assistant and final_assistant.id in visible.ids)
                error_rows = [row for row in tool_records if row["kind"] == "result" and row["status"] == "error"]
                searches = [row for row in tool_records if row["kind"] == "call" and row["tool_name"] == "odoo_record_retriever"]
                visible_error_tool_ids = [
                    row["message_id"] for row in error_rows
                    if row["message_id"] in visible.ids
                ]
                version_rows = env["office.workbook.version"].search([("thread_id", "=", thread.id)])
                session_rows = env["office.mapping.session"].search([("thread_id", "=", thread.id)])
                results.append({
                    "case": case["case"],
                    "thread_id": thread.id,
                    "user_id": user.id,
                    "selected_tool_names": sorted(thread.tool_ids.mapped("name")),
                    "prompt": prompt,
                    "elapsed_seconds": elapsed,
                    "event_types": [event.get("type") for event in events if isinstance(event, dict)],
                    "messages": snapshots,
                    "tool_calls_and_results": tool_records,
                    "search_call_count": len(searches),
                    "injected_error_count": injected_calls[thread.id],
                    "final_assistant_text": final_text,
                    "final_assistant_message_id": final_assistant.id if final_assistant else None,
                    "final_assistant_persisted_and_visible_after_refetch": visible_final,
                    "final_answer_contains_expected_values": {
                        value: value in final_text for value in case["expected_values"]
                    },
                    "injected_tool_error_ids_visible_as_chat_messages": visible_error_tool_ids,
                    "thread_version_ids": version_rows.ids,
                    "thread_session_ids": session_rows.ids,
                    "oracle": {
                        "expected_contact_ids": case["expected_contact_ids"],
                        "decoy_id": case["decoy_id"],
                    },
                })

        sdk = _sdk_events(AUDIT_PATH)
        sdk_requests = [event for event in sdk if event.get("event") == "sdk_request_submitted"]
        sdk_responses = [event for event in sdk if event.get("event") == "provider_response_received"]
        sdk_errors = [event for event in sdk if event.get("event") == "sdk_request_error"]
        result = {
            "run_tag": RUN_TAG,
            "database": env.cr.dbname,
            "provider": provider.name,
            "model": model.name,
            "thread_ids": thread_ids,
            "user_id": user.id,
            "injected_faults": {
                "query_error": "one-shot QUERY_FAILED before ORM execution, exact Thread allowlist",
                "access_denial": "one-shot ACCESS_DENIED before ORM execution, exact Thread allowlist",
                "handoff_failure": "existing M4 handoff_interruption hook after complete collection, before Hosted CI",
            },
            "provider_request_count": len(sdk_requests),
            "provider_response_count": len(sdk_responses),
            "provider_error_count": len(sdk_errors),
            "sdk_audit_path": str(AUDIT_PATH),
            "fault_audit_path": str(fault_audit_path),
            "cases": results,
            "status": "RECORDED",
            "cleanup": None,
        }
    except Exception as error:
        failure = error
        result = {
            "run_tag": RUN_TAG,
            "database": env.cr.dbname,
            "provider": PROVIDER_NAME,
            "model": MODEL_NAME,
            "thread_ids": thread_ids,
            "status": "ERROR",
            "error_type": type(error).__name__,
            "error": re.sub(r"(?i)(api[_ -]?key|token|authorization)\s*[:=]\s*\S+", r"\1=[REDACTED]", str(error))[:1200],
            "sdk_audit_path": str(AUDIT_PATH),
            "fault_audit_path": str(fault_audit_path),
        }
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        for key, (existed, value) in created["prior_params"].items():
            record = parameter_model.search([("key", "=", key)], limit=1)
            if existed:
                if record:
                    record.write({"value": value})
                else:
                    parameter_model.create({"key": key, "value": value})
            elif record:
                record.unlink()
        env.cr.commit()

        # Provider/Tool 可能已提交中间事务；若出现 Office 版本，保留相关 Thread 以保存副作用证据。
        thread_ids = created["threads"].ids
        versions = env["office.workbook.version"].search([("thread_id", "in", thread_ids)])
        preserve_thread = bool(versions)
        if created["threads"].exists() and not preserve_thread:
            created["threads"].unlink()
        if created["partners"].exists() and not preserve_thread:
            created["partners"].filtered(lambda partner: partner.parent_id).unlink()
            created["partners"].exists().unlink()
        env.cr.flush()
        bus_domain = [("create_uid", "=", user.id)]
        if created["bus_ids_before"]:
            bus_domain.append(("id", "not in", list(created["bus_ids_before"])))
        new_bus_rows = env["bus.bus"].search(bus_domain)
        if new_bus_rows:
            new_bus_rows.unlink()
        if user.exists():
            # Provider 使用量记录以 owner_id 保留外键；停用隔离用户而不删除其使用量审计行。
            user.write({"active": False})
        env.cr.flush()
        env.cr.commit()
        cleanup_result = {
            "thread_ids_removed": not preserve_thread and not created["threads"].exists(),
            "thread_ids_preserved_for_versions": versions.ids if preserve_thread else [],
            "synthetic_partner_ids_removed": not preserve_thread and not created["partners"].exists(),
            "test_user_deactivated": bool(user and not user.active),
            "test_bus_rows_removed": not new_bus_rows.exists(),
            "test_parameters_restored": all(
                (not parameter_model.search([("key", "=", key)], limit=1)) if not existed else
                parameter_model.search([("key", "=", key)], limit=1).value == value
                for key, (existed, value) in created["prior_params"].items()
            ),
        }
        result["cleanup"] = cleanup_result
        RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        os.chmod(RESULT_PATH, stat.S_IRUSR | stat.S_IWUSR)

    if failure:
        raise failure
    return result


result = run(env)
print(json.dumps({
    "run_tag": result.get("run_tag"),
    "database": result.get("database"),
    "status": result.get("status"),
    "thread_ids": result.get("thread_ids"),
    "provider_request_count": result.get("provider_request_count"),
    "provider_response_count": result.get("provider_response_count"),
    "cases": [
        {
            "case": case.get("case"),
            "thread_id": case.get("thread_id"),
            "search_call_count": case.get("search_call_count"),
            "final_assistant_persisted_and_visible_after_refetch": case.get("final_assistant_persisted_and_visible_after_refetch"),
        }
        for case in result.get("cases", [])
    ],
    "cleanup": result.get("cleanup"),
}, ensure_ascii=False))
