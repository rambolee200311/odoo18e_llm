"""在现有开发库用 GPT-5.6 Luna 对合成联系人关系执行两轮 Retriever 组件集成。"""

import json
import os
import stat
import time
from pathlib import Path

from odoo.tools import html2plaintext


EVIDENCE = Path("office_engine/docs/implementation/evidence/CC-M4-02").resolve()
DATABASE = "odoo18e_llm"
PROVIDER_NAME = "OpenAI GPT-5.6 Luna"
MODEL_NAME = "gpt-5.6-luna"
AUDIT_PARAMETER = "office_engine.m4_tv.audit_thread_ids"
RUN_TAG = "provider_constraints_v0.6"
AUDIT_PATH = EVIDENCE / f"{RUN_TAG}_sdk_audit.jsonl"
RESULT_PATH = EVIDENCE / f"{RUN_TAG}_result.json"


def _message_snapshot(message):
    """记录 Thread 的用户、工具和最终回复，供独立 Oracle 核对。"""
    return {
        "id": message.id,
        "role": message.llm_role or None,
        "body": html2plaintext(message.body or ""),
        "body_json": message.body_json or {},
        "is_error": bool(message.is_error),
    }


def _run_provider_scenario(env, cleanup):
    """创建合成数据并执行两轮真实 Provider 查询，返回可核对的执行证据。"""
    if env.cr.dbname != DATABASE:
        raise RuntimeError(f"Unexpected database: {env.cr.dbname}")
    if AUDIT_PATH.exists() or RESULT_PATH.exists():
        raise RuntimeError("Refusing to overwrite existing CC-M4-02 Provider evidence.")

    model = env["llm.model"].search([("name", "=", MODEL_NAME)], limit=2)
    if (
        len(model) != 1
        or model.provider_id.name != PROVIDER_NAME
        or model.provider_id.service != "openai"
    ):
        raise RuntimeError("The approved OpenAI GPT-5.6 Luna model is unavailable or ambiguous.")
    provider = model.provider_id
    selected_tools = env["llm.tool"].search(
        [("name", "in", ["odoo_record_retriever", "office"]), ("active", "=", True)]
    )
    if set(selected_tools.mapped("name")) != {"odoo_record_retriever", "office"}:
        raise RuntimeError("Both approved tools must be active and selected for each Thread.")

    suffix = os.urandom(6).hex()
    user = env["res.users"].with_context(no_reset_password=True).create(
        {
            "name": f"CC-M4-02 synthetic reader {suffix}",
            "login": f"cc-m4-02-{suffix}@example.invalid",
            "email": f"cc-m4-02-{suffix}@example.invalid",
            "company_id": env.company.id,
            "company_ids": [(6, 0, [env.company.id])],
            "groups_id": [(6, 0, [
                env.ref("base.group_user").id,
                env.ref("base.group_partner_manager").id,
                env.ref("llm.group_llm_manager").id,
            ])],
        }
    )
    cleanup["user"] = user
    cleanup["user_partner"] = user.partner_id
    Partner = env["res.partner"].with_user(user)
    Country = env["res.country"].with_user(user)
    country = Country.search([], order="id", limit=1)
    if not country:
        user.unlink()
        raise RuntimeError("The test user cannot read existing country metadata.")

    created_partners = Partner.browse()

    def make_partner(values):
        """只用受测业务用户创建一个带有唯一测试标记的合成联系人。"""
        nonlocal created_partners
        partner = Partner.create(values)
        created_partners |= partner
        cleanup["partners"] |= partner
        return partner

    parent_name = f"CC-M4-02 Parent {suffix}"
    parent = make_partner({"name": parent_name, "is_company": True, "country_id": country.id})
    direct_people = Partner.browse()
    for index in (1, 2):
        direct_people |= make_partner({
            "name": f"CC-M4-02 Person {suffix}-{index}",
            "parent_id": parent.id,
            "country_id": country.id,
            "is_company": False,
            "active": True,
            "email": f"cc-m4-02-person-{suffix}-{index}@example.invalid",
        })
    companies = Partner.browse()
    for index in (1, 2):
        companies |= make_partner({
            "name": f"CC-M4-02 Company {suffix}-{index}",
            "parent_id": parent.id,
            "country_id": country.id,
            "is_company": True,
            "active": True,
        })
    contacts = Partner.browse()
    for index, company in enumerate(companies, start=1):
        contacts |= make_partner({
            "name": f"CC-M4-02 Contact {suffix}-{index}",
            "parent_id": company.id,
            "country_id": country.id,
            "is_company": False,
            "active": True,
            "email": f"cc-m4-02-contact-{suffix}-{index}@example.invalid",
        })
    other_parent = make_partner({
        "name": f"CC-M4-02 Other Parent {suffix}",
        "is_company": True,
        "country_id": country.id,
    })
    decoy = make_partner({
        "name": f"CC-M4-02 Decoy Company {suffix}",
        "parent_id": other_parent.id,
        "country_id": country.id,
        "is_company": True,
        "active": True,
    })

    # Oracle 只在脚本内独立保存，不传给模型或作为 Tool 参数注入。
    oracle = {
        "parent_id": parent.id,
        "country_id": country.id,
        "individual_ids": direct_people.ids,
        "company_ids": companies.ids,
        "contact_ids": contacts.ids,
        "decoy_ids": [decoy.id],
    }
    prompts = [
        (
            f"请找出 2026 年 11 月 20 日创建、目前仍有效、直接属于公司 {parent_name}、"
            f"且位于 {country.name} 的个人联系人。请在聊天里列出姓名和邮箱；不要创建或修改任何文件。"
        ),
        (
            "改为列出公司的账户，而不是个人联系人，并补上每个账户下联系人的姓名和邮箱。"
            "保留我前面提出的其他条件。只在聊天中回答，不创建或修改文件。"
        ),
    ]
    thread = env["llm.thread"].with_user(user).create(
        {
            "name": f"CC-M4-02 synthetic task {suffix}",
            "provider_id": provider.id,
            "model_id": model.id,
            "tool_ids": [(6, 0, selected_tools.ids)],
        }
    )
    cleanup["thread"] = thread
    if set(thread.tool_ids.mapped("name")) != {"odoo_record_retriever", "office"}:
        raise RuntimeError("The synthetic Thread does not have exactly the approved tool pair.")

    # 记录运行前 Bus 游标；最终只清理本次测试用户产生的新事件。
    cleanup["bus_ids_before"] = set(env["bus.bus"].search([]).ids)
    parameter_model = env["ir.config_parameter"].sudo()
    prior_parameter = parameter_model.search([("key", "=", AUDIT_PARAMETER)], limit=1)
    parameter_existed = bool(prior_parameter)
    prior_value = prior_parameter.value if prior_parameter else None
    cleanup["audit_parameter"] = {
        "model": parameter_model,
        "existed": parameter_existed,
        "value": prior_value,
    }
    parameter_model.set_param(AUDIT_PARAMETER, str(thread.id))
    old_enabled = os.environ.get("OFFICE_M4_TV_OBSERVABILITY")
    old_path = os.environ.get("OFFICE_M4_TV_PROVIDER_AUDIT_PATH")
    os.environ["OFFICE_M4_TV_OBSERVABILITY"] = "1"
    os.environ["OFFICE_M4_TV_PROVIDER_AUDIT_PATH"] = str(AUDIT_PATH)
    AUDIT_PATH.write_text("", encoding="utf-8")
    os.chmod(AUDIT_PATH, stat.S_IRUSR | stat.S_IWUSR)

    runs = []
    try:
        for prompt in prompts:
            started = time.perf_counter()
            events = list(thread.generate(user_message_body=prompt, attachment_ids=[]))
            runs.append({
                "prompt": prompt,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "event_types": [event.get("type") for event in events if isinstance(event, dict)],
            })
    finally:
        os.environ.pop("OFFICE_M4_TV_OBSERVABILITY", None)
        os.environ.pop("OFFICE_M4_TV_PROVIDER_AUDIT_PATH", None)
        if old_enabled is not None:
            os.environ["OFFICE_M4_TV_OBSERVABILITY"] = old_enabled
        if old_path is not None:
            os.environ["OFFICE_M4_TV_PROVIDER_AUDIT_PATH"] = old_path
        current_parameter = parameter_model.search([("key", "=", AUDIT_PARAMETER)], limit=1)
        if parameter_existed:
            if current_parameter:
                current_parameter.write({"value": prior_value})
            else:
                parameter_model.create({"key": AUDIT_PARAMETER, "value": prior_value})
        elif current_parameter:
            current_parameter.unlink()
        # Provider generation may commit internally; persist the restored allowlist before fixture cleanup.
        env.cr.commit()

    all_messages = env["mail.message"].search(
        [("model", "=", "llm.thread"), ("res_id", "=", thread.id)], order="id"
    )
    messages = [_message_snapshot(message) for message in all_messages]
    user_text = "\n".join(item["body"] for item in messages if item["role"] == "user")
    final_messages = [
        item["body"]
        for item in messages
        if item["role"] == "assistant" and item["body"].strip()
    ]
    final_text = final_messages[-1] if final_messages else ""
    expected_values = [
        *(companies.mapped("name")),
        *(contacts.mapped("name")),
        *(contacts.mapped("email")),
    ]
    call_rows = []
    office_calls = []
    search_results = []
    for item in messages:
        body_json = item["body_json"]
        for call in body_json.get("tool_calls", []) if isinstance(body_json, dict) else []:
            name = (call.get("function") or {}).get("name")
            arguments = (call.get("function") or {}).get("arguments")
            call_rows.append({"tool": name, "arguments": arguments})
            if name == "office":
                office_calls.append(arguments)
        if (
            item["role"] == "tool"
            and isinstance(body_json, dict)
            and body_json.get("tool_name") == "odoo_record_retriever"
        ):
            call = body_json.get("tool_call") or {}
            result = body_json.get("result") or {}
            search_results.append({"tool_call": call, "result": result})

    sdk_events = [
        json.loads(line)
        for line in AUDIT_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    request_events = [event for event in sdk_events if event.get("event") == "sdk_request_submitted"]
    response_events = [event for event in sdk_events if event.get("event") == "provider_response_received"]
    errors = [event for event in sdk_events if event.get("event") == "sdk_request_error"]
    request_tools = [
        event.get("payload", {}).get("tools")
        for event in request_events
    ]

    result = {
        "run_tag": RUN_TAG,
        "database": env.cr.dbname,
        "provider": provider.name,
        "provider_service": provider.service,
        "model": model.name,
        "thread_id": thread.id,
        "user_id": user.id,
        "user_groups": sorted(user.groups_id.mapped("full_name")),
        "selected_tool_names": sorted(thread.tool_ids.mapped("name")),
        "test_fixture": {
            "parent_name": parent_name,
            "country_name": country.name,
            "oracle": oracle,
            "expected_final_values": expected_values,
            "decoy_name": decoy.name,
        },
        "runs": runs,
        "provider_request_count": len(request_events),
        "provider_response_count": len(response_events),
        "provider_error_count": len(errors),
        "submitted_tool_schemas": request_tools,
        "retriever_tool_calls": call_rows,
        "office_tool_calls": office_calls,
        "retriever_tool_results": search_results,
        "user_messages_present_in_thread": all(text in user_text for text in prompts),
        "final_assistant_text": final_text,
        "final_expected_values_present": {value: value in final_text for value in expected_values},
        "final_decoy_absent": decoy.name not in final_text,
        "thread_messages": messages,
        "provider_audit_path": str(AUDIT_PATH),
    }

    return result


def run(env):
    """执行隔离场景，并在成功或失败后清理其 Thread、合成记录和测试用户。"""
    cleanup = {
        "user": env["res.users"].browse(),
        "thread": env["llm.thread"].browse(),
        "partners": env["res.partner"].browse(),
        "user_partner": env["res.partner"].browse(),
    }
    old_enabled = os.environ.get("OFFICE_M4_TV_OBSERVABILITY")
    old_path = os.environ.get("OFFICE_M4_TV_PROVIDER_AUDIT_PATH")
    result = None
    failure = None
    try:
        result = _run_provider_scenario(env, cleanup)
    except Exception as error:  # 失败也写证据，并由 finally 清理已创建的夹具。
        failure = error
        result = {
            "run_tag": RUN_TAG,
            "database": env.cr.dbname,
            "provider": PROVIDER_NAME,
            "model": MODEL_NAME,
            "status": "ERROR",
            "error_type": type(error).__name__,
            "error": str(error),
            "provider_audit_path": str(AUDIT_PATH),
        }
    finally:
        if old_enabled is None:
            os.environ.pop("OFFICE_M4_TV_OBSERVABILITY", None)
        else:
            os.environ["OFFICE_M4_TV_OBSERVABILITY"] = old_enabled
        if old_path is None:
            os.environ.pop("OFFICE_M4_TV_PROVIDER_AUDIT_PATH", None)
        else:
            os.environ["OFFICE_M4_TV_PROVIDER_AUDIT_PATH"] = old_path

        audit_parameter = cleanup.get("audit_parameter")
        if audit_parameter:
            parameter_model = audit_parameter["model"]
            current_parameter = parameter_model.search([("key", "=", AUDIT_PARAMETER)], limit=1)
            if audit_parameter["existed"]:
                if current_parameter:
                    current_parameter.write({"value": audit_parameter["value"]})
                else:
                    parameter_model.create({"key": AUDIT_PARAMETER, "value": audit_parameter["value"]})
            elif current_parameter:
                current_parameter.unlink()
            env.cr.commit()

        thread = cleanup["thread"]
        partners = cleanup["partners"]
        user = cleanup["user"]
        user_partner = cleanup["user_partner"]
        if thread.exists():
            thread.unlink()
        if partners.exists():
            partners.unlink()
        # message_post 会延迟创建 Bus 事件；先冲刷，再按测试用户和运行前游标定向清理。
        env.cr.flush()
        bus_ids_before = cleanup.get("bus_ids_before", set())
        bus_domain = [("create_uid", "=", user.id)]
        if bus_ids_before:
            bus_domain.append(("id", "not in", list(bus_ids_before)))
        new_user_bus_events = env["bus.bus"].search(bus_domain)
        new_user_bus_events.unlink()
        env.cr.flush()
        if user.exists():
            user.unlink()
        if user_partner.exists():
            user_partner.unlink()
        env.cr.flush()
        env.cr.commit()
        result["cleanup"] = {
            "thread_removed": not thread.exists(),
            "partner_ids_removed": not partners.exists(),
            "test_user_removed": not user.exists(),
            "test_user_partner_removed": not user_partner.exists(),
            "test_bus_events_removed": not new_user_bus_events.exists(),
            "provider_usage_retained": True,
            "oracle_expected_records_not_sent_separately": True,
        }

    if AUDIT_PATH.exists():
        audit_events = [
            json.loads(line)
            for line in AUDIT_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        result.setdefault("provider_request_count", sum(
            event.get("event") == "sdk_request_submitted" for event in audit_events
        ))
        result.setdefault("provider_response_count", sum(
            event.get("event") == "provider_response_received" for event in audit_events
        ))
        result.setdefault("provider_error_count", sum(
            event.get("event") == "sdk_request_error" for event in audit_events
        ))
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    os.chmod(RESULT_PATH, stat.S_IRUSR | stat.S_IWUSR)
    print(json.dumps({
        "database": result["database"],
        "provider": result["provider"],
        "model": result["model"],
        "status": result.get("status", "COMPLETED"),
        "thread_id": result.get("thread_id"),
        "provider_requests": result.get("provider_request_count"),
        "provider_responses": result.get("provider_response_count"),
        "cleanup": result["cleanup"],
        "result_path": str(RESULT_PATH),
        "audit_path": str(AUDIT_PATH) if AUDIT_PATH.exists() else None,
    }, ensure_ascii=False, indent=2), flush=True)
    if failure:
        raise failure


run(env)
