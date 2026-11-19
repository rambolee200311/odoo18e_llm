"""Test-only query normalization followed by the existing full-registry embed.

The Chat request receives only the synthetic blind query. Registry metadata is
sent only to the explicitly authorized OpenAI embedding endpoint. This script
does not load the Oracle, read business rows, or call business search.
"""

import hashlib
import json
import os
import re
import stat
import time
from pathlib import Path
from types import SimpleNamespace

from odoo.addons.office_engine_m3.models.llm_tool import _DISCOVERY_MIN_SIMILARITY


BASE = Path("office_engine/docs/implementation/evidence/CC-M4-01")
EXPECTED_DB = "odoo18e_llm"
MODEL_NAME = "gpt-5.6-luna"
PROVIDER_NAME = "OpenAI GPT-5.6 Luna"
AUDIT_PARAM = "office_engine.m4_tv.audit_thread_ids"
OUTPUT = BASE / "provider_query_rewrite_embedding_blind_v0.1.jsonl"
AUDIT = BASE / "provider_query_rewrite_sdk_audit_v0.1.jsonl"
REWRITE_SYSTEM = (
    "Rewrite the user's business-object request as one concise English search phrase for matching an Odoo model's "
    "business description. Preserve the user's meaning. Do not invent or output technical model names, field names, "
    "domains, or a proposed answer. Output only the phrase, without explanation."
)


def _is_safe_rewrite(value):
    """处理 `_is_safe_rewrite` 所标识的输入、状态或结果。参数：`value`：待处理的值。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
    if not isinstance(value, str):
        return False, "not_string"
    phrase = value.strip().strip("\"'` ")
    if not phrase or len(phrase) > 256:
        return False, "empty_or_too_long"
    if re.search(r"\b[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){1,}\b", phrase, re.IGNORECASE):
        return False, "contains_model_like_identifier"
    if re.search(r"\b[a-z][a-z0-9_]*_id\b", phrase, re.IGNORECASE):
        return False, "contains_field_like_identifier"
    return True, phrase


def _embedding_text(profile):
    return (
        f"Odoo model: {profile['model']}. Description: {profile['description']}. "
        f"Record name field: {profile['rec_name'] or ''}."
    )


def run_query_rewrite_embedding_blind(env):
    """运行 `run_query_rewrite_embedding_blind` 所标识的输入、状态或结果。参数：`env`：当前 Odoo ORM 环境。 返回：无显式返回值；通过现有副作用或状态更新完成处理。"""
    if env.cr.dbname != EXPECTED_DB:
        raise RuntimeError(f"Unexpected database: {env.cr.dbname}")
    model = env["llm.model"].search([("name", "=", MODEL_NAME)], limit=2)
    if len(model) != 1 or model.provider_id.name != PROVIDER_NAME or model.provider_id.service != "openai":
        raise RuntimeError("The approved GPT-5.6 Luna provider/model is unavailable or ambiguous.")
    provider = model.provider_id
    embedding_model = provider.get_model(None, "embedding")
    tools = env["llm.tool"].search([("name", "in", ["office", "odoo_record_retriever"]), ("active", "=", True)])
    if set(tools.mapped("name")) != {"office", "odoo_record_retriever"}:
        raise RuntimeError("Expected Office and Retriever tools are unavailable.")
    cases = json.loads((BASE / "blind_queries_v0.1.json").read_text(encoding="utf-8"))["cases"]
    registry_models = sorted(env.registry.models.items(), key=lambda item: item[0])
    profiles = [
        env["llm.tool"]._retriever_discovery_profile(name, model_class)
        for name, model_class in registry_models
    ]
    output = OUTPUT.open("w", encoding="utf-8")
    output.close()
    audit = AUDIT.open("w", encoding="utf-8")
    audit.close()
    os.chmod(OUTPUT, stat.S_IRUSR | stat.S_IWUSR)
    os.chmod(AUDIT, stat.S_IRUSR | stat.S_IWUSR)
    os.environ["OFFICE_M4_TV_OBSERVABILITY"] = "1"
    os.environ["OFFICE_M4_TV_PROVIDER_AUDIT_PATH"] = str(AUDIT.resolve())

    for index, case in enumerate(cases, start=1):
        thread = env["llm.thread"].create({
            "name": f"CC-M4-01 query normalize {case['id']}",
            "provider_id": provider.id,
            "model_id": model.id,
            "user_id": env.uid,
            "tool_ids": [(6, 0, tools.ids)],
        })
        env["ir.config_parameter"].set_param(AUDIT_PARAM, str(thread.id))
        rewrite_started = time.perf_counter()
        row = {
            "case_id": case["id"],
            "thread_id": thread.id,
            "database": env.cr.dbname,
            "provider": provider.name,
            "chat_model": model.name,
            "embedding_model": embedding_model.name,
            "registry_models": len(profiles),
            "original_query": case["prompt"],
        }
        try:
            normalized_result = provider.openai_chat(
                messages=env["mail.message"].browse([]),
                model=model,
                stream=False,
                prepend_messages=[
                    {"role": "system", "content": REWRITE_SYSTEM},
                    {"role": "user", "content": case["prompt"]},
                ],
                reasoning_effort="none",
                _office_m4_tv_audit_thread_id=thread.id,
            )
            raw_rewrite = normalized_result.get("content") if isinstance(normalized_result, dict) else None
            safe, normalized_query = _is_safe_rewrite(raw_rewrite)
            row.update({
                "rewrite_status": "returned" if safe else "rejected",
                "raw_rewrite": raw_rewrite,
                "normalized_query": normalized_query if safe else None,
                "rewrite_rejection": None if safe else normalized_query,
                "rewrite_seconds": round(time.perf_counter() - rewrite_started, 3),
            })
            if not safe:
                row["overall_status"] = "rewrite_rejected"
            else:
                texts = [normalized_query, *(_embedding_text(profile) for profile in profiles)]
                input_sha256 = hashlib.sha256(
                    json.dumps(texts, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                embed_started = time.perf_counter()
                vectors = provider.embedding(texts, model=embedding_model)
                if len(vectors) != len(texts):
                    raise RuntimeError(f"Incomplete embedding response: {len(vectors)}/{len(texts)}")
                ranked = []
                query_vector = vectors[0]
                for profile, vector in zip(profiles, vectors[1:]):
                    score = env["llm.tool"]._retriever_cosine_similarity(query_vector, vector)
                    if score >= _DISCOVERY_MIN_SIMILARITY:
                        ranked.append((score, profile))
                ranked.sort(key=lambda item: (-item[0], item[1]["model"]))
                row.update({
                    "overall_status": "success",
                    "embedding_input_count": len(texts),
                    "embedding_input_sha256": input_sha256,
                    "returned_vectors": len(vectors),
                    "candidate_count": len(ranked),
                    "top5": [profile["model"] for _score, profile in ranked[:5]],
                    "embedding_seconds": round(time.perf_counter() - embed_started, 3),
                })
        except Exception as exc:
            row.update({
                "overall_status": "error",
                "error_type": type(exc).__name__,
                "error": str(exc)[:1000],
            })
        with OUTPUT.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
        print(
            f"{index:02d}/{len(cases)} {case['id']} status={row.get('overall_status')} "
            f"rewrite={row.get('rewrite_seconds')}s embedding={row.get('embedding_seconds')}s", flush=True,
        )
    print(f"Query rewrite + embedding results: {OUTPUT}", flush=True)
    print(f"Query-only Provider SDK audit: {AUDIT}", flush=True)
