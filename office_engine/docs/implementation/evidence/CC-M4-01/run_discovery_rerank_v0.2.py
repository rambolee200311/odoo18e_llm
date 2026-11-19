"""使用真实 Provider 盲测 Registry 重排；不读取 Oracle 或业务记录，也不执行 search/Office 操作。"""

import hashlib
import json
import os
import re
import stat
import time
from pathlib import Path


BASE = Path("office_engine/docs/implementation/evidence/CC-M4-01")
EXPECTED_DB = "odoo18e_llm"
PROVIDER_NAME = "OpenAI GPT-5.6 Luna"
MODEL_NAME = "gpt-5.6-luna"
AUDIT_PARAM = "office_engine.m4_tv.audit_thread_ids"


def run_discovery_rerank_v02(env, case_ids=None, tag="pilot"):
    """运行 `run_discovery_rerank_v02` 所标识的输入、状态或结果。参数：`env`：当前 Odoo ORM 环境。；`case_ids`：参与该处理的输入值，具体格式沿用现有调用约定。；`tag`：参与该处理的输入值，具体格式沿用现有调用约定。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
    if env.cr.dbname != EXPECTED_DB:
        raise RuntimeError(f"Unexpected database: {env.cr.dbname}")
    model = env["llm.model"].search([("name", "=", MODEL_NAME)], limit=2)
    if len(model) != 1 or model.provider_id.name != PROVIDER_NAME or model.provider_id.service != "openai":
        raise RuntimeError("The approved GPT-5.6 Luna Provider/model is unavailable or ambiguous.")
    provider = model.provider_id
    embedding_model = provider.get_model(None, "embedding")
    retriever = env.ref("llm_tool.llm_tool_odoo_record_retriever")
    tools = env["llm.tool"].search(
        [("name", "in", ["office", "odoo_record_retriever"]), ("active", "=", True)]
    )
    if set(tools.mapped("name")) != {"office", "odoo_record_retriever"}:
        raise RuntimeError("The required existing tool pair is unavailable.")

    cases = json.loads((BASE / "blind_queries_v0.1.json").read_text(encoding="utf-8"))["cases"]
    if case_ids is not None:
        wanted = set(case_ids)
        cases = [case for case in cases if case["id"] in wanted]
        if {case["id"] for case in cases} != wanted:
            raise RuntimeError("Requested blind case IDs are missing.")

    output = (BASE / f"provider_discovery_rerank_{tag}_v0.2.jsonl").resolve()
    audit = (BASE / f"provider_discovery_rerank_sdk_audit_{tag}_v0.2.jsonl").resolve()
    cleanup = BASE / f"provider_discovery_rerank_cleanup_{tag}_v0.2.json"
    if any(path.exists() for path in (output, audit, cleanup)):
        raise RuntimeError("Refusing to overwrite prior evidence.")
    for path in (output, audit):
        path.write_text("", encoding="utf-8")
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    parameter = env["ir.config_parameter"]
    prior = parameter.search([("key", "=", AUDIT_PARAM)], limit=1)
    prior_value = prior.value if prior else None
    prior_existed = bool(prior)
    old_observe = os.environ.get("OFFICE_M4_TV_OBSERVABILITY")
    old_audit_path = os.environ.get("OFFICE_M4_TV_PROVIDER_AUDIT_PATH")
    os.environ["OFFICE_M4_TV_OBSERVABILITY"] = "1"
    os.environ["OFFICE_M4_TV_PROVIDER_AUDIT_PATH"] = str(audit)

    original_embedding = type(provider).embedding
    observations = []
    created_thread_ids = []

    def observed_embedding(self, texts, model=None):
        """处理 `observed_embedding` 所标识的输入、状态或结果。参数：`texts`：参与该处理的输入值，具体格式沿用现有调用约定。；`model`：目标 Odoo 模型或模型技术名。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
        materialized = list(texts)
        started = time.perf_counter()
        result = original_embedding(self, materialized, model=model)
        observations.append({
            "input_count": len(materialized),
            "input_sha256": hashlib.sha256(
                json.dumps(materialized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "returned_vectors": len(result),
            "embedding_model": embedding_model.name,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        })
        return result

    type(provider).embedding = observed_embedding
    try:
        for index, case in enumerate(cases, start=1):
            thread = env["llm.thread"].create({
                "name": f"CC-M4-01 rerank {tag} {case['id']}",
                "provider_id": provider.id,
                "model_id": model.id,
                "user_id": env.uid,
                "tool_ids": [(6, 0, tools.ids)],
            })
            created_thread_ids.append(thread.id)
            parameter.set_param(AUDIT_PARAM, str(thread.id))
            arguments = {
                "operation": "discover",
                "query": case["prompt"],
                "limit": 5,
                "offset": 0,
            }
            message = thread.message_post(
                body="CC-M4-01 synthetic blind discovery call",
                body_json={
                    "type": "tool_execution",
                    "tool_name": "odoo_record_retriever",
                    "arguments": arguments,
                    "status": "executing",
                },
                llm_role="tool",
                author_id=False,
            )
            retriever_in_thread = retriever.with_context(message=message)
            before = len(observations)
            started = time.perf_counter()
            try:
                result = retriever_in_thread.execute(arguments)
                message.write({
                    "body_json": {
                        **message.body_json,
                        "status": "completed",
                        "result": result,
                    }
                })
                status = "success"
                error_type = None
                error_summary = None
            except Exception as exc:
                result = None
                status = "error"
                error_type = type(exc).__name__
                error_summary = re.sub(r"sk-[A-Za-z0-9_-]{10,}|(?i:Bearer)\s+\S+", "[REDACTED]", str(exc)[:500])
            elapsed = time.perf_counter() - started
            row = {
                "case_id": case["id"],
                "locale": case["locale"],
                "query": case["prompt"],
                "database": env.cr.dbname,
                "provider": provider.name,
                "chat_model": model.name,
                "embedding_model": embedding_model.name,
                "thread_id": thread.id,
                "thread_tool_ids": [{"id": tool.id, "name": tool.name} for tool in thread.tool_ids],
                "oracle_loaded_by_runner": False,
                "business_search_invoked": False,
                "office_action_invoked": False,
                "registry_count": len(env.registry.models),
                "discovery_result": result,
                "status": status,
                "error_type": error_type,
                "error_summary": error_summary,
                "embedding_observations": observations[before:],
                "end_to_end_discover_seconds": round(elapsed, 3),
            }
            with output.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            print(
                f"{index:02d}/{len(cases)} {case['id']} status={status} "
                f"count={result['count'] if result else 'n/a'} "
                f"top5={[item['model'] for item in result['models']] if result else []} elapsed={elapsed:.2f}s",
                flush=True,
            )
    finally:
        type(provider).embedding = original_embedding
        try:
            created_threads = env["llm.thread"].browse(created_thread_ids).exists()
            created_threads.unlink()
            current = parameter.search([("key", "=", AUDIT_PARAM)], limit=1)
            if prior_existed:
                if current:
                    current.write({"value": prior_value})
                else:
                    parameter.create({"key": AUDIT_PARAM, "value": prior_value})
            elif current:
                current.unlink()
            env.cr.commit()
            cleanup.write_text(json.dumps({
                "database": env.cr.dbname,
                "created_thread_ids": created_thread_ids,
                "removed_thread_count": len(created_threads),
                "audit_parameter_restored": True,
                "provider_usage_retained": True,
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.chmod(cleanup, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            env.cr.rollback()
            raise
        finally:
            if old_observe is None:
                os.environ.pop("OFFICE_M4_TV_OBSERVABILITY", None)
            else:
                os.environ["OFFICE_M4_TV_OBSERVABILITY"] = old_observe
            if old_audit_path is None:
                os.environ.pop("OFFICE_M4_TV_PROVIDER_AUDIT_PATH", None)
            else:
                os.environ["OFFICE_M4_TV_PROVIDER_AUDIT_PATH"] = old_audit_path

    print(f"Retriever evidence: {output}", flush=True)
    print(f"SDK audit: {audit}", flush=True)
    print(f"Cleanup: {cleanup}", flush=True)
    return {"cases": len(cases), "threads": len(created_thread_ids), "cleanup": str(cleanup)}
