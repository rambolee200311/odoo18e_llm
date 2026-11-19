"""One-off real Provider runner for CC-M4-01; execute inside odoo-bin shell.

The runner reads blind input files only. It never loads the evaluator Oracle.
``llm.thread.generate()`` can commit while processing a request, so shell exit
rollback alone does not clean its fixtures. This runner removes only the
Threads it creates in ``finally`` and restores its test audit parameter; the
credential-free SDK and result evidence files remain on disk. Provider usage
rows are retained by their ``ondelete=set null`` relation.
"""

import hashlib
import json
import os
import re
import stat
import time
from pathlib import Path

from odoo.exceptions import UserError
from odoo.tools import html2plaintext


BASE = Path("office_engine/docs/implementation/evidence/CC-M4-01")
DB_NAME = "odoo18e_llm"
CHAT_MODEL_NAME = "gpt-5.6-luna"
PROVIDER_NAME = "OpenAI GPT-5.6 Luna"
AUDIT_PARAM = "office_engine.m4_tv.audit_thread_ids"


def _read_cases(filename):
    data = json.loads((BASE / filename).read_text(encoding="utf-8"))
    return data["cases"]


def _redact_error(value):
    value = str(value)[:700]
    value = re.sub(r"sk-[A-Za-z0-9_-]{10,}", "[REDACTED]", value)
    value = re.sub(r"(?i)Bearer\s+\S+", "Bearer [REDACTED]", value)
    return value


def _message_snapshot(message):
    return {
        "id": message.id,
        "role": message.llm_role or None,
        "body": html2plaintext(message.body or ""),
        "body_json": message.body_json or {},
        "silent": bool(getattr(message, "llm_silent_retrieval", False)),
        "is_error": bool(message.is_error),
    }


def _prompt(case):
    return (
        "For an Excel export, first identify the business object and relevant field/relationship definitions. "
        "This is schema-only preparation: do not read business records and do not create or modify any workbook. "
        f"Business request: {case['prompt']}"
    )


def run_agent_blind_tests(env):
    """运行 `run_agent_blind_tests` 所标识的输入、状态或结果。参数：`env`：当前 Odoo ORM 环境。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
    if env.cr.dbname != DB_NAME:
        raise RuntimeError(f"Unexpected database: {env.cr.dbname}")

    model = env["llm.model"].search([("name", "=", CHAT_MODEL_NAME)], limit=2)
    if len(model) != 1 or model.provider_id.name != PROVIDER_NAME or model.provider_id.service != "openai":
        raise RuntimeError("The approved GPT-5.6 Luna model/provider is unavailable or ambiguous.")
    provider = model.provider_id
    embedding_model = provider.get_model(None, "embedding")
    retriever = env.ref("llm_tool.llm_tool_odoo_record_retriever")
    selected_tools = env["llm.tool"].search(
        [("name", "in", ["office", "odoo_record_retriever"]), ("active", "=", True)]
    )
    if set(selected_tools.mapped("name")) != {"office", "odoo_record_retriever"}:
        raise RuntimeError("The required Office and Retriever tools are not both active.")

    clear_cases = _read_cases("blind_queries_v0.1.json")
    supplemental_cases = _read_cases("supplemental_queries_v0.1.json")
    cases_by_id = {case["id"]: case for case in [*clear_cases, *supplemental_cases]}
    if len(cases_by_id) != len(clear_cases) + len(supplemental_cases):
        raise RuntimeError("Blind case IDs are not unique.")

    tasks = [(case["id"], case) for case in [*clear_cases, *supplemental_cases]]
    repeat_ids = ("P01", "T01", "SO01", "SP01", "OUT01", "BA01")
    for case_id in repeat_ids:
        case = cases_by_id.get(case_id)
        if not case:
            raise RuntimeError(f"Frozen repeat case is missing: {case_id}")
        tasks.extend((f"{case_id}-R{run_number}", case) for run_number in (2, 3))

    output = (BASE / "provider_agent_threads_v0.1.jsonl").resolve()
    audit = (BASE / "provider_agent_calls_v0.1.jsonl").resolve()
    output.write_text("", encoding="utf-8")
    audit.write_text("", encoding="utf-8")
    os.chmod(output, stat.S_IRUSR | stat.S_IWUSR)
    os.chmod(audit, stat.S_IRUSR | stat.S_IWUSR)
    param_model = env["ir.config_parameter"]
    original_param = param_model.search([("key", "=", AUDIT_PARAM)], limit=1)
    original_param_existed = bool(original_param)
    original_param_value = original_param.value if original_param else None
    created_thread_ids = []
    os.environ["OFFICE_M4_TV_OBSERVABILITY"] = "1"
    os.environ["OFFICE_M4_TV_PROVIDER_AUDIT_PATH"] = str(audit)

    embeddings = []
    guards = []
    tool_class = type(retriever)
    original_execute = tool_class.execute
    original_embedding = type(provider).embedding

    def guarded_execute(self, parameters):
        """处理 `guarded_execute` 所标识的输入、状态或结果。参数：`parameters`：参与该处理的输入值，具体格式沿用现有调用约定。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
        if self.name == "office":
            guards.append({
                "tool": "office",
                "blocked_before_execution": True,
                "action": parameters.get("action") if isinstance(parameters, dict) else None,
            })
            raise UserError("CC-M4-01 read-only discovery harness: Office actions are disabled.")
        if self.name == "odoo_record_retriever":
            operation = parameters.get("operation") if isinstance(parameters, dict) else None
            if operation not in {"discover", "describe"}:
                guards.append({
                    "tool": self.name,
                    "blocked_before_execution": True,
                    "operation": operation or "legacy_search",
                })
                raise UserError("CC-M4-01 schema-only harness: business record search is disabled.")
            guards.append({
                "tool": self.name,
                "blocked_before_execution": False,
                "operation": operation,
                "parameters": parameters,
            })
        return original_execute(self, parameters)

    def observed_embedding(self, texts, model=None):
        """处理 `observed_embedding` 所标识的输入、状态或结果。参数：`texts`：参与该处理的输入值，具体格式沿用现有调用约定。；`model`：目标 Odoo 模型或模型技术名。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
        started = time.perf_counter()
        digest = hashlib.sha256(
            json.dumps(list(texts), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        vectors = original_embedding(self, texts, model=model)
        embeddings.append({
            "input_count": len(texts),
            "input_sha256": digest,
            "returned_vectors": len(vectors),
            "seconds": round(time.perf_counter() - started, 3),
            "embedding_model": embedding_model.name,
        })
        return vectors

    tool_class.execute = guarded_execute
    type(provider).embedding = observed_embedding
    try:
        for index, (test_id, case) in enumerate(tasks, start=1):
            thread = env["llm.thread"].create({
                "name": f"CC-M4-01 {test_id}",
                "provider_id": provider.id,
                "model_id": model.id,
                "user_id": env.uid,
                "tool_ids": [(6, 0, selected_tools.ids)],
            })
            created_thread_ids.append(thread.id)
            env["ir.config_parameter"].set_param(AUDIT_PARAM, str(thread.id))
            selected_before = [{"id": item.id, "name": item.name} for item in thread.tool_ids]
            guard_start = len(guards)
            embedding_start = len(embeddings)
            task = {
                "test_id": test_id,
                "case_id": case["id"],
                "locale": case["locale"],
                "kind": case["kind"],
                "prompt": _prompt(case),
                "database": env.cr.dbname,
                "thread_id": thread.id,
                "provider": provider.name,
                "provider_service": provider.service,
                "chat_model": model.name,
                "embedding_model": embedding_model.name,
                "tool_ids_before": selected_before,
            }
            started = time.perf_counter()
            try:
                events = list(thread.generate(user_message_body=task["prompt"], attachment_ids=[]))
                task["generation_status"] = "returned"
                task["event_types"] = [event.get("type") for event in events if isinstance(event, dict)]
            except Exception as exc:  # preserve each Provider/Thread failure and continue
                task["generation_status"] = "error"
                task["generation_error_type"] = type(exc).__name__
                task["generation_error"] = _redact_error(exc)
            task["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            task["tool_ids_after"] = [{"id": item.id, "name": item.name} for item in thread.tool_ids]
            messages = env["mail.message"].search(
                [("model", "=", "llm.thread"), ("res_id", "=", thread.id)], order="id"
            )
            task["messages"] = [_message_snapshot(message) for message in messages]
            task["execution_guards"] = guards[guard_start:]
            task["embedding_observations"] = embeddings[embedding_start:]
            with output.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(task, ensure_ascii=False, sort_keys=True, default=str) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            print(
                f"{index:02d}/{len(tasks)} {test_id} status={task['generation_status']} "
                f"messages={len(task['messages'])} embeddings={len(task['embedding_observations'])} "
                f"guards={len(task['execution_guards'])} seconds={task['elapsed_seconds']}",
                flush=True,
            )
    finally:
        tool_class.execute = original_execute
        type(provider).embedding = original_embedding
        try:
            created_threads = env["llm.thread"].browse(created_thread_ids).exists()
            created_threads.unlink()
            current_param = param_model.search([("key", "=", AUDIT_PARAM)], limit=1)
            if original_param_existed:
                if current_param:
                    current_param.write({"value": original_param_value})
                else:
                    param_model.create({"key": AUDIT_PARAM, "value": original_param_value})
            elif current_param:
                current_param.unlink()
            env.cr.commit()
            print(
                f"Cleanup: removed {len(created_threads)} test Threads and restored the audit parameter; "
                "Provider usage rows were retained.",
                flush=True,
            )
        except Exception:
            env.cr.rollback()
            raise

    print(f"Agent evidence: {output}", flush=True)
    print(f"Provider SDK audit: {audit}", flush=True)
    print(f"Threads attempted: {len(tasks)}", flush=True)
