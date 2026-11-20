"""独立核对 CC-M4-02 v1.1 真实 Provider 结果与本地隐藏 Oracle。"""

import json
from pathlib import Path


EVIDENCE = Path(__file__).resolve().parent
RUN_TAG = "provider_constraints_v1.1"


def _require(condition, message):
    """断言一条业务验收条件，并在不满足时给出可读失败原因。"""
    if not condition:
        raise AssertionError(message)


def _arguments(entry):
    """解析工具轨迹中已记录的 JSON 参数。"""
    raw = entry.get("arguments")
    return json.loads(raw) if isinstance(raw, str) else raw or {}


def _domain_map(domain):
    """将普通 AND Domain 转成字段到 (operator, value) 的核对映射。"""
    return {
        term[0]: (term[1], term[2])
        for term in domain or []
        if isinstance(term, (list, tuple)) and len(term) == 3
    }


def main():
    """检查工具轨迹、分页、关系身份和两轮用户可见答案是否与 Oracle 一致。"""
    result_path = EVIDENCE / f"{RUN_TAG}_result.json"
    audit_path = EVIDENCE / f"{RUN_TAG}_sdk_audit.jsonl"
    data = json.loads(result_path.read_text(encoding="utf-8"))
    oracle = data["test_fixture"]["oracle"]
    parent_id = oracle["parent_id"]
    country_id = oracle["country_id"]
    people_ids = set(oracle["individual_ids"])
    company_ids = set(oracle["company_ids"])
    child_ids = set(oracle["contact_ids"])
    decoy_ids = set(oracle["decoy_ids"])
    calls = [_arguments(call) for call in data["retriever_tool_calls"]]
    tool_results = data["retriever_tool_results"]

    _require(data["database"] == "odoo18e_llm", "Provider run used an unexpected database.")
    _require(data["provider"] == "OpenAI GPT-5.6 Luna", "Provider identity differs from the approved test model.")
    _require(data["model"] == "gpt-5.6-luna", "Provider model differs from the approved test model.")
    _require(set(data["selected_tool_names"]) == {"odoo_record_retriever", "office"}, "The approved tool pair was not bound.")
    _require(data["provider_request_count"] == data["provider_response_count"] == 11, "Provider request/response counts do not balance.")
    _require(data["provider_error_count"] == 0, "The Provider reported an SDK/API error.")
    _require("Contact Creation" not in " ".join(data["user_groups"]), "The query user has elevated contact-management access.")
    _require(all(data["cleanup"].values()), "A test fixture or audit setting was not cleaned up.")

    audit_events = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    submitted = [event for event in audit_events if event.get("event") == "sdk_request_submitted"]
    received = [event for event in audit_events if event.get("event") == "provider_response_received"]
    errors = [event for event in audit_events if event.get("event") == "sdk_request_error"]
    _require(len(submitted) == len(received) == 11 and not errors, "Raw SDK audit does not match the run summary.")

    # 由实际 Tool Call/回执建立映射；不信任 Agent 的完成陈述或脚本中的预期值单独通过。
    indexed_results = []
    for entry in tool_results:
        call = entry.get("tool_call", {}).get("function", {})
        args = json.loads(call.get("arguments") or "{}")
        indexed_results.append((args, entry.get("result") or {}))

    # 证明 Agent 得到的 Registry 元数据确实指向所用关系字段和业务显示名。
    partner_descriptions = [
        body for args, body in indexed_results
        if args.get("operation") == "describe" and args.get("model") == "res.partner"
    ]
    country_descriptions = [
        body for args, body in indexed_results
        if args.get("operation") == "describe" and args.get("model") == "res.country"
    ]
    _require(len(partner_descriptions) == len(country_descriptions) == 1, "Expected complete metadata for both relation models.")
    partner_description = partner_descriptions[0]
    country_description = country_descriptions[0]
    partner_fields = {field["name"]: field for field in partner_description.get("fields", [])}
    country_fields = {field["name"]: field for field in country_description.get("fields", [])}
    _require(partner_description.get("rec_name") == "name" and country_description.get("rec_name") == "name", "Relation lookup did not use the described rec_name contract.")
    _require(partner_fields.get("parent_id", {}).get("relation") == "res.partner", "Parent relation was not supported by describe metadata.")
    _require(partner_fields.get("country_id", {}).get("relation") == "res.country", "Country relation was not supported by describe metadata.")

    def result_for(predicate):
        """按可观察的工具参数选取唯一结果，避免依赖自然语言总结。"""
        matches = [(args, body) for args, body in indexed_results if predicate(args, body)]
        _require(len(matches) == 1, f"Expected one matching tool result, found {len(matches)}.")
        return matches[0]

    parent_name = data["test_fixture"]["parent_name"]
    country_name = data["test_fixture"]["country_name"]
    parent_lookup_args, parent_lookup = result_for(
        lambda args, body: args.get("operation") == "search"
        and args.get("model") == "res.partner"
        and _domain_map(args.get("domain")).get("name") == ("=", parent_name)
    )
    country_lookup_args, country_lookup = result_for(
        lambda args, body: args.get("operation") == "search"
        and args.get("model") == "res.country"
        and _domain_map(args.get("domain")).get("name") == ("=", country_name)
    )
    _require([row["id"] for row in parent_lookup.get("records", [])] == [parent_id], "Parent name did not resolve uniquely to the Oracle parent ID.")
    _require([row["id"] for row in country_lookup.get("records", [])] == [country_id], "Country name did not resolve uniquely to the Oracle country ID.")
    _require(parent_lookup.get("has_more") is False and parent_lookup.get("count") == 1, "Parent resolution was not complete and unique.")
    _require(country_lookup.get("has_more") is False and country_lookup.get("count") == 1, "Country resolution was not complete and unique.")

    def complete_search(args, body, ids):
        """核验 ORM 查询已按完整分页返回指定 Oracle 身份集合。"""
        records = body.get("records", [])
        returned_ids = {row["id"] for row in records}
        _require(body.get("status") == "success", "Expected a successful ORM search result.")
        _require(body.get("count") == len(records) == body.get("returned_count"), "The result count and returned page differ.")
        _require(body.get("has_more") is False and body.get("next_offset") is None, "A query page was not fully consumed.")
        _require(returned_ids == ids, f"Returned record identities differ from the Oracle: {returned_ids} != {ids}.")
        return records

    people_args, people_result = result_for(
        lambda args, body: args.get("operation") == "search"
        and _domain_map(args.get("domain")).get("is_company") == ("=", False)
        and _domain_map(args.get("domain")).get("parent_id") == ("=", parent_id)
    )
    companies_args, companies_result = result_for(
        lambda args, body: args.get("operation") == "search"
        and _domain_map(args.get("domain")).get("is_company") == ("=", True)
        and _domain_map(args.get("domain")).get("parent_id") == ("=", parent_id)
    )
    children_args, children_result = result_for(
        lambda args, body: args.get("operation") == "search"
        and _domain_map(args.get("domain")).get("parent_id") == ("in", oracle["company_ids"])
        and args.get("model") == "res.partner"
    )
    people = complete_search(people_args, people_result, people_ids)
    companies = complete_search(companies_args, companies_result, company_ids)
    children = complete_search(children_args, children_result, child_ids)

    for args, body in ((people_args, people_result), (companies_args, companies_result), (children_args, children_result)):
        domain = _domain_map(args.get("domain"))
        domain_terms = args.get("domain", [])
        _require(domain.get("country_id") == ("=", country_id), "A result query did not preserve the resolved country constraint.")
        _require(domain.get("active") == ("=", True), "A result query did not preserve the active constraint.")
        _require(["create_date", ">=", f"{data['test_fixture']['task_date']} 00:00:00"] in domain_terms, "A result query did not preserve the inclusive task date bound.")
        _require(["create_date", "<", _next_day(data["test_fixture"]["task_date"])] in domain_terms, "A result query is missing the exclusive next-day bound.")

    _require(all(row.get("parent_id", [None])[0] == parent_id for row in people + companies), "A direct child has the wrong parent relationship.")
    child_parent_by_id = {row["id"]: row.get("parent_id", [None])[0] for row in children}
    _require(child_parent_by_id == dict(zip(oracle["contact_ids"], oracle["company_ids"])), "Child rows were not grouped under their exact Oracle company IDs.")
    _require(not ((people_ids | company_ids | child_ids) & decoy_ids), "Oracle fixture identity sets overlap the decoy.")

    # 按 Thread 每轮的可见回答核对姓名和邮箱；不以回答文本中的“已完成”作为充分证据。
    turn_texts = data["turn_final_texts"]
    expected_turn_values = data["test_fixture"]["expected_turn_values"]
    _require(len(turn_texts) == 2, "The Provider did not produce two completed turns.")
    for turn_index, expected_values in enumerate(expected_turn_values):
        _require(all(value in turn_texts[turn_index] for value in expected_values), f"Turn {turn_index + 1} omitted Oracle output values.")
    _require(data["test_fixture"]["decoy_name"] not in "\n".join(turn_texts), "The final answer included a decoy record.")
    _require(not any(value in turn_texts[0] for value in data["test_fixture"]["expected_final_values"]), "Turn 1 included companies or child contacts before the user's change.")
    _require("CC-M4-02 Person " not in turn_texts[1], "Turn 2 reused prior individual contacts as company children.")

    response_call_counts = []
    for event in received:
        choices = (event.get("response") or {}).get("choices") or []
        tool_calls = (choices[0].get("message") or {}).get("tool_calls") or [] if choices else []
        response_call_counts.append(len(tool_calls))
    _require(max(response_call_counts, default=0) <= 1, "A Provider response bundled multiple tool calls despite the sequencing rule.")

    payload_text = "\n".join(
        json.dumps(event.get("payload") or {}, ensure_ascii=False)
        for event in submitted
    )
    _require("oracle_expected_records" not in payload_text, "The independent Oracle marker was sent to the Provider.")
    _require("expected_turn_values" not in payload_text, "Expected answer values were sent to the Provider.")

    evidence = {
        "run_tag": RUN_TAG,
        "status": "PASS",
        "database": data["database"],
        "provider": data["provider"],
        "model": data["model"],
        "thread_id": data["thread_id"],
        "provider_requests": len(submitted),
        "provider_responses": len(received),
        "provider_errors": len(errors),
        "ordinary_internal_user_without_contact_manager": True,
        "metadata_relation_resolution": {
            "parent_record_id": parent_id,
            "country_record_id": country_id,
            "parent_candidates": parent_lookup["count"],
            "country_candidates": country_lookup["count"],
        },
        "oracle_identity_checks": {
            "individual_ids": sorted({row["id"] for row in people}) == sorted(people_ids),
            "company_ids": sorted({row["id"] for row in companies}) == sorted(company_ids),
            "child_ids": sorted({row["id"] for row in children}) == sorted(child_ids),
            "child_parent_map": {str(key): value for key, value in sorted(child_parent_by_id.items())},
            "all_query_pages_complete": True,
            "decoy_absent": data["test_fixture"]["decoy_name"] not in "\n".join(turn_texts),
            "oracle_not_injected": True,
        },
        "turn_output_values": {
            "turn_1": all(value in turn_texts[0] for value in expected_turn_values[0]),
            "turn_2": all(value in turn_texts[1] for value in expected_turn_values[1]),
        },
        "cleanup": data["cleanup"],
    }
    output = EVIDENCE / f"{RUN_TAG}_oracle_validation.json"
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


def _next_day(date_string):
    """返回用户任务日期之后一天的 Odoo Datetime 下界文本。"""
    from datetime import date, timedelta

    return f"{date.fromisoformat(date_string) + timedelta(days=1)} 00:00:00"


if __name__ == "__main__":
    main()
