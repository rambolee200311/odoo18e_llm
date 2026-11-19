"""离线评估 Agent 盲测日志；Oracle 仅在本脚本中读取，不进入 Provider 调用。"""

import json
import re
import sys
from pathlib import Path


BASE = Path("office_engine/docs/implementation/evidence/CC-M4-01")


def _case_base(test_id):
    """从重复测试编号中提取原始盲测编号。"""
    return re.sub(r"-R[23]$", "", test_id)


def _clear_target(oracle, case_id):
    """按 Oracle 的家族编号区间查找明确意图的目标模型。"""
    match = re.fullmatch(r"([A-Z]+)(\d+)", case_id)
    if not match:
        return None
    family, number = match.group(1), int(match.group(2))
    for span, model in oracle["clear_targets"].items():
        start, end = span.split("-")
        first = re.fullmatch(r"([A-Z]+)(\d+)", start)
        last = re.fullmatch(r"([A-Z]+)(\d+)", end)
        if first and last and first.group(1) == family == last.group(1):
            if int(first.group(2)) <= number <= int(last.group(2)):
                return model
    return None


def _completed_retriever_calls(task):
    """提取 Thread 内成功完成的 Retriever 参数与工具结果。"""
    calls = []
    for message in task.get("messages", []):
        data = message.get("body_json") or {}
        if data.get("tool_name") != "odoo_record_retriever" or data.get("status") != "completed":
            continue
        arguments = data.get("arguments") or {}
        result = data.get("result") or {}
        calls.append({"arguments": arguments, "result": result})
    return calls


def _final_answer(task):
    """返回 Thread 中最后一条非空 assistant 文本。"""
    answers = [
        message.get("body", "")
        for message in task.get("messages", [])
        if message.get("role") == "assistant" and message.get("body", "").strip()
    ]
    return answers[-1] if answers else ""


def _has_clarification(text):
    """识别自然语言中的澄清请求提示，不读取或推断隐藏推理。"""
    lower = text.casefold()
    markers = (
        "please clarify", "could you clarify", "do you mean", "which type", "which one",
        "which scope", "what scope", "which business", "which event", "which category",
        "请确认", "请问", "哪一种", "哪一类", "具体指", "是指", "您要", "请明确",
    )
    return any(marker in lower for marker in markers)


def _states(task):
    """归集实际工具路径、模型描述及被测试护栏拒绝的操作。"""
    calls = _completed_retriever_calls(task)
    discovers = [call for call in calls if call["arguments"].get("operation") == "discover"]
    describes = [call for call in calls if call["arguments"].get("operation") == "describe"]
    described_models = [call["arguments"].get("model") for call in describes]
    blocked_searches = [
        item for item in task.get("execution_guards", [])
        if item.get("tool") == "odoo_record_retriever" and item.get("blocked_before_execution")
        and item.get("operation") not in {"discover", "describe"}
    ]
    blocked_office = [
        item for item in task.get("execution_guards", [])
        if item.get("tool") == "office" and item.get("blocked_before_execution")
    ]
    top5 = (discovers[0]["result"].get("models") or [])[:5] if discovers else []
    return {
        "calls": calls,
        "discovers": discovers,
        "describes": describes,
        "described_models": described_models,
        "first_top5": [row.get("model") for row in top5],
        "blocked_search_attempts": blocked_searches,
        "blocked_office_attempts": blocked_office,
        "final_answer": _final_answer(task),
    }


def evaluate(result_filename, audit_filename):
    """用独立 Oracle 逐项评估候选召回、Agent 选模、歧义和负向处理。"""
    oracle = json.loads((BASE / "oracle_v0.1.json").read_text(encoding="utf-8"))
    tasks = [
        json.loads(line)
        for line in (BASE / result_filename).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    registry_counts = [
        call["result"].get("count")
        for task in tasks
        for call in _completed_retriever_calls(task)
        if call["arguments"].get("operation") == "discover" and call["result"].get("count")
    ]
    registry_count = max(set(registry_counts), key=registry_counts.count) if registry_counts else None
    per_case = []
    clear_rows = []
    technical_rows = []
    business_rows = []
    negative_rows = []
    for task in tasks:
        case_id = _case_base(task["test_id"])
        state = _states(task)
        kind = task.get("kind")
        row = {
            "test_id": task["test_id"],
            "case_id": case_id,
            "kind": kind,
            "thread_id": task.get("thread_id"),
            "generation_status": task.get("generation_status"),
            "provider": task.get("provider"),
            "chat_model": task.get("chat_model"),
            "tool_ids_before": task.get("tool_ids_before", []),
            "tool_ids_after": task.get("tool_ids_after", []),
            "discover_call_count": len(state["discovers"]),
            "describe_call_count": len(state["describes"]),
            "first_top5": state["first_top5"],
            "described_models": state["described_models"],
            "blocked_search_attempts": state["blocked_search_attempts"],
            "blocked_office_attempts": state["blocked_office_attempts"],
            "final_answer": state["final_answer"],
            "elapsed_seconds": task.get("elapsed_seconds"),
        }
        if kind == "clear":
            target = _clear_target(oracle, case_id)
            if target is None:
                raise ValueError(f"Oracle 未配置明确意图目标：{case_id}")
            first_rank = state["first_top5"].index(target) + 1 if target in state["first_top5"] else None
            described = target in state["described_models"]
            final_mentions = target in state["final_answer"]
            tools_match = {item.get("name") for item in task.get("tool_ids_before", [])} == {
                "office", "odoo_record_retriever"
            }
            row.update({
                "target_model": target,
                "retriever_top5_rank": first_rank,
                "retriever_top5_status": "PASS" if first_rank else "FAIL",
                "agent_describe_selection_status": "PASS" if described else (
                    "NOT_REACHED" if not first_rank else "FAIL"
                ),
                "agent_completion_status": "PASS" if described and final_mentions else "FAIL",
                "clear_case_status": "PASS" if (
                    first_rank and described and final_mentions and tools_match
                    and not state["blocked_search_attempts"] and not state["blocked_office_attempts"]
                ) else "FAIL",
            })
            clear_rows.append(row)
        elif kind == "technical_ambiguity":
            expected = oracle["technical_ambiguity"][case_id]["candidate_models"]
            missing = [model for model in expected if model not in state["described_models"]]
            relation = oracle["technical_ambiguity"][case_id].get("relation")
            relation_ok = True
            if relation:
                parent_model = relation.get("parent_model", "world.depot.outbound.order")
                field = relation["field"]
                inverse = relation["inverse_field"]
                parent_describe = next((call["result"] for call in state["describes"]
                                        if call["arguments"].get("model") == parent_model), {})
                field_rows = parent_describe.get("fields") or []
                relation_ok = any(
                    item.get("name") == field
                    and item.get("relation") == "world.depot.outbound.order.product"
                    and item.get("inverse_field") == inverse
                    for item in field_rows
                )
            row.update({
                "expected_models": expected,
                "missing_describes": missing,
                "relation_verified": relation_ok,
                "technical_ambiguity_status": "PASS" if (
                    not missing and relation_ok and not state["blocked_search_attempts"]
                ) else "FAIL",
            })
            technical_rows.append(row)
        elif kind == "business_ambiguity":
            clarified = _has_clarification(state["final_answer"])
            row["clarification_status"] = "PASS" if clarified else "FAIL"
            row["business_ambiguity_status"] = "PASS" if (
                clarified and not state["blocked_search_attempts"]
            ) else "FAIL"
            business_rows.append(row)
        elif kind == "negative":
            answer = state["final_answer"].casefold()
            no_match = any(token in answer for token in (
                "no relevant", "no matching", "not found", "no such", "no registered",
                "no business object", "no data object", "could not find", "cannot find",
                "没有相关", "未找到", "没有找到", "未发现", "没有发现", "无匹配", "不存在", "无可用结果",
            ))
            row["no_match_statement"] = no_match
            row["negative_status"] = "PASS" if (
                no_match and state["discovers"] and not state["described_models"]
                and not state["blocked_search_attempts"]
            ) else "FAIL"
            negative_rows.append(row)
        per_case.append(row)

    audit_events = [
        json.loads(line)
        for line in (BASE / audit_filename).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rerank_requests = []
    normal_agent_requests = []
    for event in audit_events:
        if event.get("event") != "sdk_request_submitted":
            continue
        payload = event.get("payload") or {}
        messages = payload.get("messages") or []
        if messages and "You match a user's business request to Odoo business object definitions" in str(messages[0].get("content", "")):
            user_payload = {}
            if len(messages) > 1:
                try:
                    user_payload = json.loads(messages[1].get("content") or "{}")
                except ValueError:
                    user_payload = {}
            valid = (
                len(messages) == 2
                and [item.get("role") for item in messages] == ["system", "user"]
                and not payload.get("tools")
                and set(user_payload) == {"business_request", "candidates"}
                and isinstance(user_payload.get("business_request"), str)
                and isinstance(user_payload.get("candidates"), list)
                and len(user_payload.get("candidates", [])) == registry_count
                and len({item.get("candidate_id") for item in user_payload.get("candidates", [])})
                    == len(user_payload.get("candidates", []))
                and all(set(item) == {"candidate_id", "model", "description", "rec_name"}
                        for item in user_payload.get("candidates", []))
            )
            rerank_requests.append({
                "request_id": event.get("request_id"),
                "thread_ids": event.get("thread_ids"),
                "message_count": len(messages),
                "candidate_count": len(user_payload.get("candidates", [])),
                "tools_count": len(payload.get("tools") or []),
                "no_thread_history": valid,
            })
        else:
            normal_agent_requests.append(event)

    repeat_rows = []
    for case_id in ("P01", "T01", "SO01", "SP01", "OUT01", "BA01"):
        run_rows = [row for row in clear_rows + business_rows if row["case_id"] == case_id or row["test_id"].startswith(case_id + "-R")]
        statuses = [row.get("clear_case_status", row.get("business_ambiguity_status")) for row in run_rows]
        repeat_rows.append({
            "case_id": case_id,
            "thread_count": len(run_rows),
            "per_thread_statuses": statuses,
            "status": "NOT_RUN" if not run_rows else (
                "PASS" if len(run_rows) == 3 and all(value == "PASS" for value in statuses) else "FAIL"
            ),
        })

    base_clear_rows = [row for row in clear_rows if row["test_id"] == row["case_id"]]
    repeated_clear_rows = [row for row in clear_rows if row["test_id"] != row["case_id"]]
    base_business_rows = [row for row in business_rows if row["test_id"] == row["case_id"]]
    summary = {
        "agent_threads": len(tasks),
        "registry_count": registry_count,
        "clear_cases": len(base_clear_rows),
        "clear_top5_hits": sum(row["retriever_top5_status"] == "PASS" for row in base_clear_rows),
        "clear_agent_describe_selections": sum(row["agent_describe_selection_status"] == "PASS" for row in base_clear_rows),
        "clear_end_to_end_passes": sum(row["clear_case_status"] == "PASS" for row in base_clear_rows),
        "repeated_clear_cases": len(repeated_clear_rows),
        "repeated_clear_passes": sum(row["clear_case_status"] == "PASS" for row in repeated_clear_rows),
        "technical_ambiguity_cases": len(technical_rows),
        "technical_ambiguity_passes": sum(row["technical_ambiguity_status"] == "PASS" for row in technical_rows),
        "business_ambiguity_cases": len(base_business_rows),
        "business_ambiguity_passes": sum(row["business_ambiguity_status"] == "PASS" for row in base_business_rows),
        "negative_cases": len(negative_rows),
        "negative_passes": sum(row["negative_status"] == "PASS" for row in negative_rows),
        "repeat_cases": repeat_rows,
        "provider_sdk_requests": sum(event.get("event") == "sdk_request_submitted" for event in audit_events),
        "provider_sdk_responses": sum(event.get("event") == "provider_response_received" for event in audit_events),
        "provider_sdk_errors": sum(event.get("event") == "sdk_request_error" for event in audit_events),
        "internal_rerank_requests": len(rerank_requests),
        "internal_rerank_no_thread_history": all(item["no_thread_history"] for item in rerank_requests),
        "internal_rerank_full_registry_candidates": all(item["candidate_count"] == registry_count for item in rerank_requests),
        "normal_agent_request_count": len(normal_agent_requests),
        "provider_audit_integrity": all(item["no_thread_history"] for item in rerank_requests),
    }
    output = {
        "input_file": result_filename,
        "audit_file": audit_filename,
        "oracle_loaded_only_by_evaluator": True,
        "summary": summary,
        "rerank_request_checks": rerank_requests,
        "per_case": per_case,
    }
    output_name = result_filename.replace(".jsonl", "_evaluation.json")
    (BASE / output_name).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Evaluation: {BASE / output_name}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: evaluate_agent_blind_tests_v0.2.py RESULT.jsonl AUDIT.jsonl")
    evaluate(sys.argv[1], sys.argv[2])
