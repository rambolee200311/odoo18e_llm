"""Test-only multi-phrase normalization followed by full-registry embedding.

The Chat request contains only the synthetic blind query. Registry metadata is
sent only to the explicitly authorized embedding endpoint. No Oracle or
business rows are read; results are not product code.
"""

import hashlib
import json
import os
import re
import stat
import time
from pathlib import Path

from odoo.addons.office_engine_m3.models.llm_tool import _DISCOVERY_MIN_SIMILARITY


BASE = Path("office_engine/docs/implementation/evidence/CC-M4-01")
EXPECTED_DB = "odoo18e_llm"
MODEL_NAME = "gpt-5.6-luna"
PROVIDER_NAME = "OpenAI GPT-5.6 Luna"
AUDIT_PARAM = "office_engine.m4_tv.audit_thread_ids"
OUTPUT = BASE / "provider_query_variants_embedding_blind_v0.1.jsonl"
AUDIT = BASE / "provider_query_variants_sdk_audit_v0.1.jsonl"
REWRITE_SYSTEM = (
    "Express the user's business-object request as exactly three concise English search phrases for matching "
    "business descriptions in a software registry. Use distinct natural phrasings while preserving the request. "
    "Do not invent or output technical model names, field names, domains, or a proposed answer. Return JSON only "
    "as an object with a `phrases` array of three strings. Do not explain."
)


def _parse_phrases(value):
    """解析 `_parse_phrases` 所标识的输入、状态或结果。参数：`value`：待处理的值。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
    if not isinstance(value, str):
        return [], "not_string"
    text = value.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return [], "invalid_json"
    phrases = data.get("phrases") if isinstance(data, dict) else None
    if not isinstance(phrases, list) or len(phrases) != 3 or any(not isinstance(item, str) for item in phrases):
        return [], "invalid_phrase_list"
    normalized = []
    for phrase in phrases:
        phrase = phrase.strip().strip("\"'` ")
        if not phrase or len(phrase) > 256:
            return [], "empty_or_too_long"
        if re.search(r"\b[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){1,}\b", phrase, re.IGNORECASE):
            return [], "contains_model_like_identifier"
        if re.search(r"\b[a-z][a-z0-9_]*_id\b", phrase, re.IGNORECASE):
            return [], "contains_field_like_identifier"
        normalized.append(phrase)
    return list(dict.fromkeys(normalized)), None


def _profile_text(profile):
    return (
        f"Odoo model: {profile['model']}. Description: {profile['description']}. "
        f"Record name field: {profile['rec_name'] or ''}."
    )


def run_query_variants_embedding_blind(env):
    """运行 `run_query_variants_embedding_blind` 所标识的输入、状态或结果。参数：`env`：当前 Odoo ORM 环境。 返回：无显式返回值；通过现有副作用或状态更新完成处理。"""
    if env.cr.dbname != EXPECTED_DB:
        raise RuntimeError(f"Unexpected database: {env.cr.dbname}")
    model = env["llm.model"].search([("name", "=", MODEL_NAME)], limit=2)
    if len(model) != 1 or model.provider_id.name != PROVIDER_NAME or model.provider_id.service != "openai":
        raise RuntimeError("The approved GPT-5.6 Luna provider/model is unavailable or ambiguous.")
    provider = model.provider_id
    embedding_model = provider.get_model(None, "embedding")
    cases = json.loads((BASE / "blind_queries_v0.1.json").read_text(encoding="utf-8"))["cases"]
    registry_models = sorted(env.registry.models.items(), key=lambda item: item[0])
    retriever = env["llm.tool"].browse(env.ref("llm_tool.llm_tool_odoo_record_retriever").id)
    profiles = [retriever._retriever_discovery_profile(name, model_class) for name, model_class in registry_models]
    OUTPUT.write_text("", encoding="utf-8")
    AUDIT.write_text("", encoding="utf-8")
    os.chmod(OUTPUT, stat.S_IRUSR | stat.S_IWUSR)
    os.chmod(AUDIT, stat.S_IRUSR | stat.S_IWUSR)
    os.environ["OFFICE_M4_TV_OBSERVABILITY"] = "1"
    os.environ["OFFICE_M4_TV_PROVIDER_AUDIT_PATH"] = str(AUDIT.resolve())

    for index, case in enumerate(cases, start=1):
        thread = env["llm.thread"].create({
            "name": f"CC-M4-01 query variants {case['id']}",
            "provider_id": provider.id,
            "model_id": model.id,
            "user_id": env.uid,
            "tool_ids": [(6, 0, env["llm.tool"].search([("name", "in", ["office", "odoo_record_retriever"]), ("active", "=", True)]).ids)],
        })
        env["ir.config_parameter"].set_param(AUDIT_PARAM, str(thread.id))
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
        rewrite_started = time.perf_counter()
        try:
            response = provider.openai_chat(
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
            raw = response.get("content") if isinstance(response, dict) else None
            phrases, rejection = _parse_phrases(raw)
            row.update({
                "rewrite_status": "returned" if phrases else "rejected",
                "raw_rewrite": raw,
                "phrases": phrases,
                "rewrite_rejection": rejection,
                "rewrite_seconds": round(time.perf_counter() - rewrite_started, 3),
            })
            if not phrases:
                row["overall_status"] = "rewrite_rejected"
            else:
                inputs = [*phrases, *(_profile_text(profile) for profile in profiles)]
                if len(inputs) > 2048:
                    raise RuntimeError(f"Embedding batch exceeds provider input cap: {len(inputs)}")
                row["embedding_input_sha256"] = hashlib.sha256(
                    json.dumps(inputs, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                embed_started = time.perf_counter()
                vectors = provider.embedding(inputs, model=embedding_model)
                if len(vectors) != len(inputs):
                    raise RuntimeError(f"Incomplete embedding response: {len(vectors)}/{len(inputs)}")
                query_vectors = vectors[:len(phrases)]
                ranked = []
                for profile, vector in zip(profiles, vectors[len(phrases):]):
                    scores = [retriever._retriever_cosine_similarity(query_vector, vector) for query_vector in query_vectors]
                    score = max(scores)
                    if score >= _DISCOVERY_MIN_SIMILARITY:
                        ranked.append((score, profile))
                ranked.sort(key=lambda item: (-item[0], item[1]["model"]))
                row.update({
                    "overall_status": "success",
                    "embedding_input_count": len(inputs),
                    "returned_vectors": len(vectors),
                    "candidate_count": len(ranked),
                    "top5": [profile["model"] for _score, profile in ranked[:5]],
                    "embedding_seconds": round(time.perf_counter() - embed_started, 3),
                })
        except Exception as exc:
            row.update({"overall_status": "error", "error_type": type(exc).__name__, "error": str(exc)[:1000]})
        with OUTPUT.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
        print(
            f"{index:02d}/{len(cases)} {case['id']} status={row.get('overall_status')} "
            f"rewrite={row.get('rewrite_seconds')}s embedding={row.get('embedding_seconds')}s", flush=True,
        )
    print(f"Query variants + embedding results: {OUTPUT}", flush=True)
    print(f"Query-only Provider SDK audit: {AUDIT}", flush=True)
