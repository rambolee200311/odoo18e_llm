"""Isolated GPT chat reranking of actual Retriever candidates.

This evidence runner reads only synthetic blind prompts and Registry metadata.
It does not load the Oracle, search business records, or call Office actions.
The only Registry metadata sent to GPT is the candidate pool returned by the
existing Retriever for the corresponding synthetic prompt.
"""

import json
import os
import re
import stat
import time
from pathlib import Path
from types import SimpleNamespace


BASE = Path("office_engine/docs/implementation/evidence/CC-M4-01")
EXPECTED_DB = "odoo18e_llm"
MODEL_NAME = "gpt-5.6-luna"
PROVIDER_NAME = "OpenAI GPT-5.6 Luna"
AUDIT_PARAM = "office_engine.m4_tv.audit_thread_ids"
PAGE_SIZE = 50
OUTPUT = BASE / "provider_chat_rerank_blind_v0.1.jsonl"
AUDIT = BASE / "provider_chat_rerank_sdk_audit_v0.1.jsonl"
SYSTEM_PROMPT = (
    "You select the Odoo data object that best matches the user's business request. "
    "Choose only from the supplied candidates. Rank up to five candidate IDs from best to worst. "
    "Return JSON only with exactly this shape: {\"ranked_candidate_ids\":[\"C000\", ...]}. "
    "Do not include explanations, technical identifiers outside the supplied candidate IDs, "
    "or any text beyond the JSON object."
)


def _parse_ranked_ids(content):
    """解析 `_parse_ranked_ids` 所标识的输入、状态或结果。参数：`content`：待处理的文本或内容。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
    if not isinstance(content, str):
        return [], "not_string"
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        return [], "invalid_json"
    ranked = parsed.get("ranked_candidate_ids") if isinstance(parsed, dict) else None
    if not isinstance(ranked, list) or any(not isinstance(item, str) for item in ranked):
        return [], "invalid_ranked_candidate_ids"
    return ranked, None


def run_provider_chat_rerank_blind(env):
    """运行 `run_provider_chat_rerank_blind` 所标识的输入、状态或结果。参数：`env`：当前 Odoo ORM 环境。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
    if env.cr.dbname != EXPECTED_DB:
        raise RuntimeError(f"Unexpected database: {env.cr.dbname}")
    if OUTPUT.exists() or AUDIT.exists():
        raise RuntimeError("Refusing to overwrite existing rerank evidence files.")

    models = env["llm.model"].search([("name", "=", MODEL_NAME)], limit=2)
    if len(models) != 1 or models.provider_id.name != PROVIDER_NAME or models.provider_id.service != "openai":
        raise RuntimeError("The approved GPT-5.6 Luna Provider/model is unavailable or ambiguous.")
    model = models
    provider = model.provider_id
    retriever = env.ref("llm_tool.llm_tool_odoo_record_retriever")
    cases = json.loads((BASE / "blind_queries_v0.1.json").read_text(encoding="utf-8"))["cases"]

    OUTPUT.write_text("", encoding="utf-8")
    AUDIT.write_text("", encoding="utf-8")
    os.chmod(OUTPUT, stat.S_IRUSR | stat.S_IWUSR)
    os.chmod(AUDIT, stat.S_IRUSR | stat.S_IWUSR)

    old_observability = os.environ.get("OFFICE_M4_TV_OBSERVABILITY")
    old_audit_path = os.environ.get("OFFICE_M4_TV_PROVIDER_AUDIT_PATH")
    params = env["ir.config_parameter"]
    old_param = params.search([("key", "=", AUDIT_PARAM)], limit=1)
    old_param_value = old_param.value if old_param else None
    thread = None
    completed = 0
    os.environ["OFFICE_M4_TV_OBSERVABILITY"] = "1"
    os.environ["OFFICE_M4_TV_PROVIDER_AUDIT_PATH"] = str(AUDIT.resolve())

    try:
        tools = env["llm.tool"].search([("name", "in", ["office", "odoo_record_retriever"]), ("active", "=", True)])
        if set(tools.mapped("name")) != {"office", "odoo_record_retriever"}:
            raise RuntimeError("The expected existing Office and Retriever tools are unavailable.")
        thread = env["llm.thread"].create({
            "name": "CC-M4-01 isolated Registry candidate chat rerank",
            "provider_id": provider.id,
            "model_id": model.id,
            "user_id": env.uid,
            "tool_ids": [(6, 0, tools.ids)],
        })
        params.set_param(AUDIT_PARAM, str(thread.id))
        retriever = retriever.with_context(message=SimpleNamespace(model="llm.thread", res_id=thread.id))

        for index, case in enumerate(cases, start=1):
            row = {
                "case_id": case["id"],
                "locale": case["locale"],
                "query": case["prompt"],
                "database": env.cr.dbname,
                "provider": provider.name,
                "chat_model": model.name,
                "candidate_limit": PAGE_SIZE,
                "thread_id": thread.id,
                "oracle_loaded_by_runner": False,
                "business_search_invoked": False,
                "office_action_invoked": False,
            }
            started = time.perf_counter()
            try:
                discovery = retriever.odoo_record_retriever_execute(
                    operation="discover", query=case["prompt"], limit=PAGE_SIZE, offset=0
                )
                raw_candidates = discovery.get("models", [])
                candidates = [
                    {
                        "candidate_id": f"C{candidate_index:03d}",
                        "model": candidate["model"],
                        "description": candidate.get("description") or "",
                        "rec_name": candidate.get("rec_name"),
                    }
                    for candidate_index, candidate in enumerate(raw_candidates)
                ]
                row.update({
                    "retriever_candidate_count": discovery.get("count"),
                    "candidate_pool_returned": len(candidates),
                    "candidate_pool": candidates,
                    "retriever_status": discovery.get("status"),
                })
                if not candidates:
                    row.update({"status": "empty_candidate_pool", "reranked_candidate_ids": []})
                else:
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": json.dumps({
                                "business_request": case["prompt"],
                                "candidates": candidates,
                            }, ensure_ascii=False, separators=(",", ":")),
                        },
                    ]
                    response = provider.openai_chat(
                        messages=env["mail.message"].browse([]),
                        model=model,
                        stream=False,
                        prepend_messages=messages,
                        reasoning_effort="none",
                        _office_m4_tv_audit_thread_id=thread.id,
                    )
                    content = response.get("content") if isinstance(response, dict) else None
                    ranked_ids, parse_error = _parse_ranked_ids(content)
                    allowed = {candidate["candidate_id"] for candidate in candidates}
                    validation_error = None
                    if parse_error:
                        validation_error = parse_error
                    elif not ranked_ids or len(ranked_ids) > min(5, len(candidates)):
                        validation_error = "wrong_rank_count"
                    elif len(ranked_ids) != len(set(ranked_ids)):
                        validation_error = "duplicate_candidate_id"
                    elif any(candidate_id not in allowed for candidate_id in ranked_ids):
                        validation_error = "unknown_candidate_id"
                    row.update({
                        "raw_response": content,
                        "reranked_candidate_ids": ranked_ids,
                        "response_validation_error": validation_error,
                        "status": "success" if validation_error is None else "invalid_response",
                    })
            except Exception as exc:
                row.update({
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:1000],
                })
            row["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            with OUTPUT.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                handle.flush()
            completed += 1
            print(
                f"{index:02d}/{len(cases)} {case['id']} status={row['status']} "
                f"pool={row.get('candidate_pool_returned', 0)} elapsed={row['elapsed_seconds']}s",
                flush=True,
            )
    finally:
        if thread and thread.exists():
            thread.unlink()
        if old_param:
            params.set_param(AUDIT_PARAM, old_param_value)
        else:
            params.search([("key", "=", AUDIT_PARAM)]).unlink()
        if old_observability is None:
            os.environ.pop("OFFICE_M4_TV_OBSERVABILITY", None)
        else:
            os.environ["OFFICE_M4_TV_OBSERVABILITY"] = old_observability
        if old_audit_path is None:
            os.environ.pop("OFFICE_M4_TV_PROVIDER_AUDIT_PATH", None)
        else:
            os.environ["OFFICE_M4_TV_PROVIDER_AUDIT_PATH"] = old_audit_path

    summary = {"cases": len(cases), "completed": completed, "thread_cleaned": True}
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    print(f"Rerank result: {OUTPUT}", flush=True)
    print(f"Provider SDK audit: {AUDIT}", flush=True)
    return summary
