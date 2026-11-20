"""独立核对真实 Provider 记录中的 Domain 错误传播、查询集合及最终 Oracle。"""

import json
from pathlib import Path


EVIDENCE = Path(__file__).resolve().parent


def _read_result(name):
    """读取一个已保存的 Provider 运行结果 JSON。"""
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def _tool_messages(result):
    """返回 Thread 中按实际执行顺序保存的 Retriever 工具消息。"""
    return [
        message
        for message in result.get("thread_messages", [])
        if message.get("role") == "tool"
        and (message.get("body_json") or {}).get("tool_name") == "odoo_record_retriever"
    ]


def _arguments(message):
    """解析工具消息所保存的参数，兼容 JSON 文本和对象两种形状。"""
    value = (message.get("body_json") or {}).get("arguments")
    return json.loads(value) if isinstance(value, str) else value or {}


def _expected_person_values(result):
    """按合成夹具规则和隐藏 Oracle 身份独立构造联系人姓名、邮箱。"""
    fixture = result["test_fixture"]
    suffix = fixture["parent_name"].removeprefix("CC-M4-02 Parent ")
    oracle = fixture["oracle"]
    names = [
        *(f"CC-M4-02 Person {suffix}-{index}" for index in (1, 2)),
        *(f"CC-M4-02 Contact {suffix}-{index}" for index in (1, 2)),
    ]
    emails = [
        *(f"cc-m4-02-person-{suffix}-{index}@example.invalid" for index in (1, 2)),
        *(f"cc-m4-02-contact-{suffix}-{index}@example.invalid" for index in (1, 2)),
    ]
    return set(oracle["individual_ids"] + oracle["contact_ids"]), names + emails


def evaluate_focused_run():
    """评价一次盲化单条件 Provider 查询及其完整 Retriever/Oracle 轨迹。"""
    result = _read_result("provider_domain_precision_v0.2_result.json")
    messages = _tool_messages(result)
    failed = next(
        message for message in messages
        if (message.get("body_json") or {}).get("status") == "error"
    )
    failed_error = failed["body_json"].get("error", "")
    failed_arguments = _arguments(failed)
    failed_field = next(
        term[0] for term in failed_arguments.get("domain", [])
        if isinstance(term, list) and term and term[0] == "company_type"
    )
    failed_position = messages.index(failed)
    followup = next(
        message for message in messages[failed_position + 1:]
        if (message.get("body_json") or {}).get("status") == "completed"
        and _arguments(message).get("operation") == "search"
    )
    followup_arguments = _arguments(followup)
    followup_result = followup["body_json"].get("result") or {}
    actual_ids = {row["id"] for row in followup_result.get("records", [])}
    expected_ids, expected_values = _expected_person_values(result)
    final_text = result.get("final_assistant_text", "")
    extras = actual_ids - expected_ids
    return {
        "run_tag": result["run_tag"],
        "database": result["database"],
        "provider_model": result["model"],
        "request_response_counts": [result["provider_request_count"], result["provider_response_count"]],
        "initial_nonsearchable_domain": failed_arguments.get("domain"),
        "initial_error_code": failed["body_json"].get("error_code"),
        "initial_error_mentions_field": failed_field in failed_error,
        "initial_failure_has_no_success_result": "result" not in failed["body_json"],
        "followup_domain": followup_arguments.get("domain"),
        "followup_preserved_equivalent_type_predicate": any(
            isinstance(term, list) and term[0] == "is_company"
            for term in followup_arguments.get("domain", [])
        ),
        "followup_returned_ids": sorted(actual_ids),
        "oracle_expected_ids": sorted(expected_ids),
        "followup_extra_ids": sorted(extras),
        "followup_domain_matches_full_business_oracle": actual_ids == expected_ids,
        "final_output_contains_all_oracle_values": all(value in final_text for value in expected_values),
        "cleanup": result.get("cleanup"),
    }


def evaluate_complex_run():
    """评价两轮复杂任务中记录值解析和查询结果是否匹配隐藏 Oracle。"""
    result = _read_result("provider_constraints_v0.7_result.json")
    messages = _tool_messages(result)
    search_messages = [
        message for message in messages
        if _arguments(message).get("operation") == "search"
    ]
    first_domain = _arguments(search_messages[0]).get("domain", [])
    wrong_parent_value = next(
        (term[2] for term in first_domain if isinstance(term, list) and term[0] == "parent_id"),
        None,
    )
    wrong_country_value = next(
        (term[2] for term in first_domain if isinstance(term, list) and term[0] == "country_id"),
        None,
    )
    oracle = result["test_fixture"]["oracle"]
    expected_ids = set(oracle["company_ids"] + oracle["contact_ids"])
    actual_search_ids = set()
    for message in search_messages:
        body = message.get("body_json") or {}
        values = body.get("result") or {}
        actual_search_ids.update(row.get("id") for row in values.get("records", []))
    errors = [
        {
            "error_code": message["body_json"].get("error_code"),
            "error": message["body_json"].get("error"),
            "arguments": _arguments(message),
        }
        for message in messages
        if (message.get("body_json") or {}).get("status") == "error"
    ]
    return {
        "run_tag": result["run_tag"],
        "database": result["database"],
        "provider_model": result["model"],
        "request_response_counts": [result["provider_request_count"], result["provider_response_count"]],
        "first_parent_domain_value": wrong_parent_value,
        "first_country_domain_value": wrong_country_value,
        "first_search_was_zero": bool(search_messages and not (search_messages[0]["body_json"].get("result") or {}).get("records")),
        "expected_oracle_ids": sorted(expected_ids),
        "ids_returned_by_all_searches": sorted(actual_search_ids),
        "final_expected_values_present": result.get("final_expected_values_present"),
        "final_assistant_text": result.get("final_assistant_text"),
        "tool_errors": errors,
        "cleanup": result.get("cleanup"),
    }


output = {
    "focused_domain_recovery": evaluate_focused_run(),
    "complex_two_turn_query": evaluate_complex_run(),
}
path = EVIDENCE / "provider_domain_precision_final_oracle_validation.json"
path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(output, ensure_ascii=False, indent=2))
