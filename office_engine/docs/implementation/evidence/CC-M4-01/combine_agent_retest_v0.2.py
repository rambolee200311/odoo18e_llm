"""合并保留原始失败的 Agent 复测证据，不覆盖任何 Provider 原始记录。"""

import json
import sys
from pathlib import Path


BASE = Path("office_engine/docs/implementation/evidence/CC-M4-01")


def combine(baseline_name, retest_name, output_name):
    """将单项复测并入最终逐例状态，同时保留首次运行状态。"""
    baseline = json.loads((BASE / baseline_name).read_text(encoding="utf-8"))
    retest = json.loads((BASE / retest_name).read_text(encoding="utf-8"))
    baseline_clear = {
        row["case_id"]: row
        for row in baseline["per_case"]
        if row.get("kind") == "clear" and row.get("test_id") == row.get("case_id")
    }
    retest_clear = {
        row["case_id"]: row
        for row in retest["per_case"]
        if row.get("kind") == "clear" and row.get("test_id") == row.get("case_id")
    }
    latest = dict(baseline_clear)
    latest.update(retest_clear)
    combined_rows = list(baseline["per_case"])
    for row in retest_clear.values():
        row = dict(row)
        row["acceptance_retest"] = True
        row["prior_status"] = baseline_clear.get(row["case_id"], {}).get("clear_case_status")
        row["prior_failure"] = baseline_clear.get(row["case_id"], {}).get("final_answer")
        combined_rows.append(row)

    summary = {
        "unique_clear_cases": len(latest),
        "initial_clear_passes": sum(row.get("clear_case_status") == "PASS" for row in baseline_clear.values()),
        "initial_clear_failures": [
            {
                "case_id": case_id,
                "target_model": row.get("target_model"),
                "retriever_top5_status": row.get("retriever_top5_status"),
                "agent_describe_selection_status": row.get("agent_describe_selection_status"),
                "final_answer": row.get("final_answer"),
            }
            for case_id, row in baseline_clear.items()
            if row.get("clear_case_status") != "PASS"
        ],
        "retested_case_ids": sorted(retest_clear),
        "latest_clear_passes": sum(row.get("clear_case_status") == "PASS" for row in latest.values()),
        "technical_ambiguity_passes": baseline["summary"]["technical_ambiguity_passes"],
        "technical_ambiguity_cases": baseline["summary"]["technical_ambiguity_cases"],
        "business_ambiguity_passes": baseline["summary"]["business_ambiguity_passes"],
        "business_ambiguity_cases": baseline["summary"]["business_ambiguity_cases"],
        "negative_passes": baseline["summary"]["negative_passes"],
        "negative_cases": baseline["summary"]["negative_cases"],
        "repeat_cases": baseline["summary"]["repeat_cases"],
        "provider_requests_baseline": baseline["summary"]["provider_sdk_requests"],
        "provider_errors_baseline": baseline["summary"]["provider_sdk_errors"],
        "provider_requests_retest": retest["summary"]["provider_sdk_requests"],
        "provider_errors_retest": retest["summary"]["provider_sdk_errors"],
        "rerank_history_isolated_baseline": baseline["summary"]["internal_rerank_no_thread_history"],
        "rerank_history_isolated_retest": retest["summary"]["internal_rerank_no_thread_history"],
    }
    output = {
        "baseline_evaluation": baseline_name,
        "retest_evaluation": retest_name,
        "oracle_loaded_only_by_evaluators": True,
        "summary": summary,
        "per_case": combined_rows,
    }
    target = BASE / output_name
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Combined evaluation: {target}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("Usage: combine_agent_retest_v0.2.py BASELINE.json RETEST.json OUTPUT.json")
    combine(sys.argv[1], sys.argv[2], sys.argv[3])
