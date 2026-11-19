"""Candidate-only full-registry embedding probe for CC-M4-01.

Run inside ``odoo-bin shell``. Reads blind inputs and Registry metadata only;
does not load the Oracle, read business records, or call Retriever search.
The surrounding harness must roll back its transaction after execution.
"""

import hashlib
import json
import time
from pathlib import Path

from odoo.addons.office_engine_m3.models.llm_tool import _DISCOVERY_MIN_SIMILARITY


BASE = Path("office_engine/docs/implementation/evidence/CC-M4-01")
EXPECTED_DB = "odoo18e_llm"
MODEL_NAME = "gpt-5.6-luna"
PROVIDER_NAME = "OpenAI GPT-5.6 Luna"
OUTPUT = BASE / "provider_localized_profile_blind_v0.1.jsonl"


def _embedding_text(model_name, description, localized_description, rec_name):
    return (
        f"Odoo model: {model_name}. Description: {description}. "
        f"Localized description: {localized_description}. "
        f"Record name field: {rec_name or ''}."
    )


def _load_registry(env, locale):
    '加载 `_load_registry` 所标识的输入、状态或结果。参数：`env`：当前 Odoo ORM 环境。；`locale`：参与该处理的输入值，具体格式沿用现有调用约定。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。'
    rows = sorted(env.registry.models.items(), key=lambda row: row[0])
    names = [name for name, _model in rows]
    # Blind inputs use product-language labels; map them to installed Odoo
    # language codes without changing the test prompt.
    lang = {"en": "en_US", "zh-CN": "zh_CN"}.get(locale, locale.replace("-", "_"))
    ir_models = env["ir.model"].with_context(lang=lang).search_read(
        [("model", "in", names)], ["model", "name"]
    )
    labels = {row["model"]: row.get("name") or "" for row in ir_models}
    profiles = []
    for name, model_class in rows:
        profiles.append({
            "model": name,
            "description": str(getattr(model_class, "_description", "") or ""),
            "localized_description": labels.get(name, ""),
            "rec_name": str(getattr(model_class, "_rec_name", "") or "") or None,
        })
    return profiles


def run_localized_profile_blind(env):
    """运行 `run_localized_profile_blind` 所标识的输入、状态或结果。参数：`env`：当前 Odoo ORM 环境。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
    if env.cr.dbname != EXPECTED_DB:
        raise RuntimeError(f"Unexpected database: {env.cr.dbname}")
    model = env["llm.model"].search([("name", "=", MODEL_NAME)], limit=2)
    if len(model) != 1 or model.provider_id.name != PROVIDER_NAME or model.provider_id.service != "openai":
        raise RuntimeError("The approved GPT-5.6 Luna provider/model is unavailable or ambiguous.")
    provider = model.provider_id
    embedding_model = provider.get_model(None, "embedding")
    cases = json.loads((BASE / "blind_queries_v0.1.json").read_text(encoding="utf-8"))["cases"]
    OUTPUT.write_text("", encoding="utf-8")
    all_rows = []
    for index, case in enumerate(cases, start=1):
        profiles = _load_registry(env, case["locale"])
        texts = [
            case["prompt"],
            *(
                _embedding_text(
                    profile["model"], profile["description"],
                    profile["localized_description"], profile["rec_name"],
                )
                for profile in profiles
            ),
        ]
        input_sha256 = hashlib.sha256(
            json.dumps(texts, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        started = time.perf_counter()
        vectors = provider.embedding(texts, model=embedding_model)
        elapsed = time.perf_counter() - started
        if len(vectors) != len(texts):
            raise RuntimeError(f"Incomplete embeddings for {case['id']}: {len(vectors)}/{len(texts)}")
        query_vector = vectors[0]
        ranked = []
        for profile, vector in zip(profiles, vectors[1:]):
            score = env["llm.tool"]._retriever_cosine_similarity(query_vector, vector)
            if score >= _DISCOVERY_MIN_SIMILARITY:
                ranked.append((score, profile))
        ranked.sort(key=lambda row: (-row[0], row[1]["model"]))
        row = {
            "case_id": case["id"],
            "locale": case["locale"],
            "query": case["prompt"],
            "database": env.cr.dbname,
            "provider": provider.name,
            "chat_model": model.name,
            "embedding_model": embedding_model.name,
            "registry_models": len(profiles),
            "input_count": len(texts),
            "input_sha256": input_sha256,
            "returned_vectors": len(vectors),
            "result_count": len(ranked),
            "top5": [profile for _score, profile in ranked[:5]],
            "provider_seconds": round(elapsed, 3),
        }
        with OUTPUT.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
        all_rows.append(row)
        print(
            f"{index:02d}/{len(cases)} {case['id']} candidates={len(ranked)} "
            f"seconds={row['provider_seconds']}", flush=True,
        )
    print(f"Localized full-registry probe: {OUTPUT}", flush=True)
    return all_rows
