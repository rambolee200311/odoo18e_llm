"""Offline-only evaluator for the isolated GPT candidate reranking run.

This file is intentionally separate from the Provider runner. It is the only
new runner component that reads the independent Oracle labels.
"""

import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


BASE = Path("office_engine/docs/implementation/evidence/CC-M4-01")
RUN_INPUT = BASE / "provider_chat_rerank_blind_v0.1.jsonl"
BASELINE_INPUT = BASE / "provider_discovery_top5_v0.1.jsonl"
ORACLE_INPUT = BASE / "oracle_v0.1.json"
OUTPUT = BASE / "provider_chat_rerank_evaluation_v0.1.json"


def _expand_targets(target_ranges):
    """处理 `_expand_targets` 所标识的输入、状态或结果。参数：`target_ranges`：参与该处理的输入值，具体格式沿用现有调用约定。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
    result = {}
    for key, target in target_ranges.items():
        if "-" not in key:
            result[key] = target
            continue
        prefix, suffix = key.split("-", 1)
        # Clear-target ranges in this dataset use a shared alphabetic prefix.
        left_prefix = "".join(character for character in prefix if not character.isdigit())
        right_prefix = "".join(character for character in suffix if not character.isdigit())
        left_number = int("".join(character for character in prefix if character.isdigit()))
        right_number = int("".join(character for character in suffix if character.isdigit()))
        if left_prefix != right_prefix:
            raise ValueError(f"Malformed Oracle range: {key}")
        for number in range(left_number, right_number + 1):
            result[f"{left_prefix}{number:02d}"] = target
    return result


def _nearest_rank(values, percentile):
    """处理 `_nearest_rank` 所标识的输入、状态或结果。参数：`values`：需要写入或处理的字段值。；`percentile`：参与该处理的输入值，具体格式沿用现有调用约定。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
    values = sorted(values)
    if not values:
        return None
    return values[max(0, math.ceil(percentile * len(values)) - 1)]


def _contains_credential_field(value):
    """处理 `_contains_credential_field` 所标识的输入、状态或结果。参数：`value`：待处理的值。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
    forbidden = {"api_key", "authorization", "authorization_header", "access_token", "client_secret", "password"}
    if isinstance(value, dict):
        return any(key.casefold() in forbidden or _contains_credential_field(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_credential_field(item) for item in value)
    return False


def evaluate():
    """评估 `evaluate` 所标识的输入、状态或结果。返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
    oracle = json.loads(ORACLE_INPUT.read_text(encoding="utf-8"))
    targets = _expand_targets(oracle["clear_targets"])
    run_rows = [json.loads(line) for line in RUN_INPUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    baseline_rows = [json.loads(line) for line in BASELINE_INPUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(run_rows) != 40 or len(baseline_rows) != 40:
        raise ValueError("Expected the full 40-case reranker run and baseline.")
    baseline_by_id = {row["case_id"]: row for row in baseline_rows}

    per_case = []
    for row in run_rows:
        case_id = row["case_id"]
        target = targets[case_id]
        pool_models = [candidate["model"] for candidate in row.get("candidate_pool", [])]
        id_to_model = {candidate["candidate_id"]: candidate["model"] for candidate in row.get("candidate_pool", [])}
        ranked_models = [id_to_model[candidate_id] for candidate_id in row.get("reranked_candidate_ids", []) if candidate_id in id_to_model]
        baseline_top5 = [candidate["model"] for candidate in baseline_by_id[case_id]["top5"]]
        same_run_top5 = pool_models[:5]
        per_case.append({
            "case_id": case_id,
            "target_model": target,
            "retriever_status": row.get("retriever_status"),
            "retriever_candidate_count": row.get("retriever_candidate_count"),
            "candidate_pool_returned": len(pool_models),
            "target_in_candidate_pool": target in pool_models,
            "baseline_retriever_top5": baseline_top5,
            "baseline_top5_hit": target in baseline_top5,
            "same_run_retriever_top5": same_run_top5,
            "same_run_retriever_top5_hit": target in same_run_top5,
            "reranker_status": row.get("status"),
            "reranked_models_returned": ranked_models,
            "reranker_output_hit": target in ranked_models,
            "reranker_top1_hit": bool(ranked_models and ranked_models[0] == target),
            "ranked_count": len(ranked_models),
            "response_validation_error": row.get("response_validation_error"),
        })

    total = len(per_case)
    chat_rows = [row for row in run_rows if row.get("status") in {"success", "invalid_response"}]
    valid_rows = [row for row in run_rows if row.get("status") == "success"]
    counts = Counter(row.get("status") for row in run_rows)
    audit_events = [
        json.loads(line)
        for line in (BASE / "provider_chat_rerank_sdk_audit_v0.1.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    requests = {event["request_id"]: event for event in audit_events if event.get("event") == "sdk_request_submitted"}
    responses = {event["request_id"]: event for event in audit_events if event.get("event") == "provider_response_received"}
    latency_seconds = [
        (datetime.fromisoformat(responses[request_id]["timestamp"]) - datetime.fromisoformat(request["timestamp"])).total_seconds()
        for request_id, request in requests.items()
        if request_id in responses
    ]
    output_by_query = {row["query"]: row for row in run_rows}
    payload_matches_logged_candidates = True
    payload_is_metadata_only = True
    provider_response_matches_runner = True
    provider_schema = True
    for request_id, request in requests.items():
        payload = request.get("payload") or {}
        messages = payload.get("messages") or []
        user_messages = [message for message in messages if message.get("role") == "user"]
        system_messages = [message for message in messages if message.get("role") == "system"]
        if len(user_messages) != 1 or len(system_messages) != 1 or "tools" in payload or "tool_choice" in payload:
            provider_schema = False
            continue
        try:
            user_data = json.loads(user_messages[0]["content"])
        except (KeyError, TypeError, ValueError):
            payload_matches_logged_candidates = False
            payload_is_metadata_only = False
            continue
        run_row = output_by_query.get(user_data.get("business_request"))
        if not run_row or user_data.get("candidates") != run_row.get("candidate_pool"):
            payload_matches_logged_candidates = False
        candidates = user_data.get("candidates")
        if not isinstance(candidates, list) or any(
            set(candidate) != {"candidate_id", "model", "description", "rec_name"}
            for candidate in candidates if isinstance(candidate, dict)
        ) or any(not isinstance(candidate, dict) for candidate in candidates or []):
            payload_is_metadata_only = False
        if run_row and request_id in responses:
            response = responses[request_id].get("response") or {}
            choices = response.get("choices") or []
            response_content = choices[0].get("message", {}).get("content") if choices else None
            if response_content != run_row.get("raw_response"):
                provider_response_matches_runner = False
    credential_fields_present = any(_contains_credential_field(event) for event in audit_events)
    summary = {
        "run_id": "CC-M4-01 isolated Retriever-candidate GPT chat rerank v0.1",
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_boundary": "Oracle labels read only by this offline evaluator, never by Provider runner or Provider requests.",
        "provider": "OpenAI GPT-5.6 Luna",
        "database": "odoo18e_llm",
        "candidate_pool_limit": 50,
        "cases": total,
        "runner_status_counts": dict(sorted(counts.items())),
        "provider_chat_requests_expected": len(chat_rows),
        "provider_sdk_request_count": len(requests),
        "provider_sdk_response_count": len(responses),
        "provider_sdk_errors": sum(event.get("event") == "sdk_request_error" for event in audit_events),
        "provider_payload_matches_logged_retriever_candidates": payload_matches_logged_candidates,
        "provider_payload_contains_only_candidate_schema_metadata": payload_is_metadata_only,
        "provider_response_matches_runner_output": provider_response_matches_runner,
        "no_provider_tool_schema_or_tool_call_expected": provider_schema,
        "credential_fields_present_in_provider_audit": credential_fields_present,
        "provider_chat_latency_seconds_p50": round(_nearest_rank(latency_seconds, 0.50), 3) if latency_seconds else None,
        "provider_chat_latency_seconds_p95": round(_nearest_rank(latency_seconds, 0.95), 3) if latency_seconds else None,
        "valid_rank_list_count": len(valid_rows),
        "candidate_pool_recall_at_50": sum(row["target_in_candidate_pool"] for row in per_case),
        "baseline_retriever_top5_hits": sum(row["baseline_top5_hit"] for row in per_case),
        "same_run_retriever_top5_hits": sum(row["same_run_retriever_top5_hit"] for row in per_case),
        "reranker_returned_list_target_hits": sum(row["reranker_output_hit"] for row in per_case),
        "reranker_top1_hits": sum(row["reranker_top1_hit"] for row in per_case),
        "reranker_top1_hits_when_target_in_pool": sum(
            row["reranker_top1_hit"] for row in per_case if row["target_in_candidate_pool"]
        ),
        "target_covered_cases": sum(row["target_in_candidate_pool"] for row in per_case),
        "ranked_list_length_distribution": dict(sorted(Counter(row["ranked_count"] for row in per_case).items())),
        "reranker_complete_top5_outputs": sum(row["ranked_count"] == 5 for row in per_case),
        "not_product_acceptance": True,
        "per_case": per_case,
    }
    for key in (
        "candidate_pool_recall_at_50",
        "baseline_retriever_top5_hits",
        "same_run_retriever_top5_hits",
        "reranker_returned_list_target_hits",
        "reranker_top1_hits",
        "reranker_complete_top5_outputs",
    ):
        summary[f"{key}_rate"] = round(summary[key] / total, 4)
    summary["reranker_top1_rate_when_target_in_pool"] = round(
        summary["reranker_top1_hits_when_target_in_pool"] / summary["target_covered_cases"], 4
    ) if summary["target_covered_cases"] else None
    summary["all_integrity_checks_pass"] = bool(
        summary["provider_sdk_request_count"] == 39
        and summary["provider_sdk_response_count"] == 39
        and summary["provider_sdk_errors"] == 0
        and payload_matches_logged_candidates
        and payload_is_metadata_only
        and provider_response_matches_runner
        and provider_schema
        and not credential_fields_present
    )
    OUTPUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key not in {"per_case"}}, ensure_ascii=False, indent=2))
    print(f"Offline evaluation: {OUTPUT}")
    return summary


if __name__ == "__main__":
    evaluate()
