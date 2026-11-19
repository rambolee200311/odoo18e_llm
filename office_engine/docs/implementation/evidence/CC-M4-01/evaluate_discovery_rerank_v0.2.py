"""Offline-only evaluator; never import this module from a Provider runner."""

import json
import re
import statistics
import sys
from pathlib import Path


BASE = Path("office_engine/docs/implementation/evidence/CC-M4-01")


def evaluate(result_name):
    """评估 `evaluate` 所标识的输入、状态或结果。参数：`result_name`：参与该处理的输入值，具体格式沿用现有调用约定。 返回：无显式返回值；通过现有副作用或状态更新完成处理。"""
    oracle = json.loads((BASE / "oracle_v0.1.json").read_text(encoding="utf-8"))
    clear_targets = oracle["clear_targets"]
    rows = [json.loads(line) for line in (BASE / result_name).read_text(encoding="utf-8").splitlines() if line.strip()]
    per_case = []
    for row in rows:
        # Oracle keys encode ranges such as P01-P04; resolve by exact family and suffix.
        target = None
        match = re.fullmatch(r"([A-Z]+)(\d+)", row["case_id"])
        if not match:
            raise ValueError(f"Unexpected clear case ID: {row['case_id']}")
        family, number_text = match.groups()
        number = int(number_text)
        for key, model in clear_targets.items():
            start, end = key.split("-")
            first = re.fullmatch(r"([A-Z]+)(\d+)", start)
            last = re.fullmatch(r"([A-Z]+)(\d+)", end)
            if first and last and first.group(1) == family == last.group(1):
                if int(first.group(2)) <= number <= int(last.group(2)):
                    target = model
                    break
        if target is None:
            raise ValueError(f"No independent Oracle target for {row['case_id']}")
        result = row.get("discovery_result")
        names = [item["model"] for item in result.get("models", [])] if result else []
        rank = names.index(target) + 1 if target in names else None
        per_case.append({
            "case_id": row["case_id"],
            "target_model": target,
            "target_rank": rank,
            "top5_hit": row.get("status") == "success" and rank is not None and rank <= 5,
            "status": row.get("status", "success"),
            "error_type": row.get("error_type"),
            "error_summary": row.get("error_summary"),
            "returned_count": result.get("returned_count") if result else 0,
            "registry_count": row["registry_count"],
            "count_matches_registry": bool(result) and (result.get("count") == row["registry_count"] or result.get("count") == 0),
            "discover_seconds": row["end_to_end_discover_seconds"],
            "embedding_seconds": sum(x["elapsed_seconds"] for x in row["embedding_observations"]),
        })
    clear_cases = per_case
    hit_count = sum(item["top5_hit"] for item in clear_cases)
    elapsed = sorted(item["discover_seconds"] for item in per_case)
    audit_name = result_name.replace("provider_discovery_rerank_", "provider_discovery_rerank_sdk_audit_")
    audit_path = BASE / audit_name
    audit_events = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()] if audit_path.exists() else []
    request_times = {}
    chat_latencies = []
    for event in audit_events:
        if event.get("event") == "sdk_request_submitted":
            request_times[event["request_id"]] = event["timestamp"]
        elif event.get("event") == "provider_response_received" and event.get("request_id") in request_times:
            from datetime import datetime
            started = datetime.fromisoformat(request_times.pop(event["request_id"]))
            finished = datetime.fromisoformat(event["timestamp"])
            chat_latencies.append((finished - started).total_seconds())
    percentiles = lambda values: {
        "p50": round(statistics.median(values), 3) if values else None,
        "p95": round(sorted(values)[min(len(values) - 1, int((len(values) - 1) * 0.95))], 3) if values else None,
    }
    output = {
        "result_file": result_name,
        "oracle_loaded_only_by_evaluator": True,
        "cases": len(per_case),
        "clear_cases": len(clear_cases),
        "clear_top5_hits": hit_count,
        "clear_top5_required": "40/40",
        "clear_top5_pass": len(clear_cases) == 40 and hit_count == 40,
        "discovery_latency_seconds": percentiles(elapsed),
        "embedding_latency_seconds": percentiles([item["embedding_seconds"] for item in per_case if item["embedding_seconds"]]),
        "chat_latency_seconds": percentiles(chat_latencies),
        "provider_request_count": sum(event.get("event") == "sdk_request_submitted" for event in audit_events),
        "provider_response_count": sum(event.get("event") == "provider_response_received" for event in audit_events),
        "provider_error_count": sum(event.get("event") == "sdk_request_error" for event in audit_events),
        "failed_case_count": sum(item["status"] != "success" for item in per_case),
        "per_case": per_case,
    }
    out_name = result_name.replace(".jsonl", "_evaluation.json")
    (BASE / out_name).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: output[key] for key in (
        "cases", "clear_cases", "clear_top5_hits", "clear_top5_pass", "discovery_latency_seconds",
        "provider_request_count", "provider_response_count", "provider_error_count", "failed_case_count",
    )}, ensure_ascii=False, indent=2))
    print(f"Evaluation: {BASE / out_name}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: evaluate_discovery_rerank_v0.2.py RESULT.jsonl")
    evaluate(sys.argv[1])
