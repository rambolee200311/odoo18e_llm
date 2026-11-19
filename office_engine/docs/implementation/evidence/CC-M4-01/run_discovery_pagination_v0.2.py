"""在完整 Registry 上通过真实工具消息路径重复执行 discover 分页遍历。"""

import json
import os
import stat
from pathlib import Path


BASE = Path("office_engine/docs/implementation/evidence/CC-M4-01")
DB_NAME = "odoo18e_llm"
MODEL_NAME = "gpt-5.6-luna"
PROVIDER_NAME = "OpenAI GPT-5.6 Luna"
AUDIT_PARAM = "office_engine.m4_tv.audit_thread_ids"
QUERY = "只识别并描述客户、供应商和联系人档案对应的数据对象及字段，不读取记录。"
PAGE_SIZE = 100


def _walk(retriever, thread):
    """逐页创建持久化工具调用消息并收集 discover 结果。"""
    pages = []
    offset = 0
    expected_count = None
    while expected_count is None or offset < expected_count:
        arguments = {
            "operation": "discover", "query": QUERY, "limit": PAGE_SIZE, "offset": offset,
        }
        message = thread.message_post(
            body="CC-M4-01 synthetic discovery page call",
            body_json={
                "type": "tool_execution",
                "tool_name": "odoo_record_retriever",
                "arguments": arguments,
                "status": "executing",
            },
            llm_role="tool",
            author_id=False,
        )
        page = retriever.with_context(message=message).execute(arguments)
        message.write({
            "body_json": {
                **message.body_json,
                "status": "completed",
                "result": page,
            }
        })
        if expected_count is None:
            expected_count = page["count"]
        pages.append({
            "offset": offset,
            "count": page["count"],
            "returned_count": page["returned_count"],
            "has_more": page["has_more"],
            "next_offset": page["next_offset"],
            "models": [row["model"] for row in page["models"]],
        })
        offset += PAGE_SIZE
        if len(pages) > 100:
            raise RuntimeError("Unexpected Retriever pagination loop.")
    return pages


def run_discovery_pagination_v02(env, tag="retry_round2"):
    """运行 `run_discovery_pagination_v02` 所标识的输入、状态或结果。参数：`env`：当前 Odoo ORM 环境。；`tag`：参与该处理的输入值，具体格式沿用现有调用约定。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
    if env.cr.dbname != DB_NAME:
        raise RuntimeError(f"Unexpected database: {env.cr.dbname}")
    model = env["llm.model"].search([("name", "=", MODEL_NAME)], limit=2)
    if len(model) != 1 or model.provider_id.name != PROVIDER_NAME or model.provider_id.service != "openai":
        raise RuntimeError("The approved Provider/model is unavailable or ambiguous.")
    tools = env["llm.tool"].search(
        [("name", "in", ["office", "odoo_record_retriever"]), ("active", "=", True)]
    )
    if set(tools.mapped("name")) != {"office", "odoo_record_retriever"}:
        raise RuntimeError("The required existing tool pair is unavailable.")
    output = (BASE / f"provider_discovery_pagination_{tag}.json").resolve()
    audit = (BASE / f"provider_discovery_pagination_sdk_audit_{tag}.jsonl").resolve()
    cleanup_file = BASE / f"provider_discovery_pagination_cleanup_{tag}.json"
    if output.exists() or audit.exists() or cleanup_file.exists():
        raise RuntimeError("Refusing to overwrite prior pagination evidence.")
    audit.write_text("", encoding="utf-8")
    os.chmod(audit, stat.S_IRUSR | stat.S_IWUSR)
    os.environ["OFFICE_M4_TV_OBSERVABILITY"] = "1"
    os.environ["OFFICE_M4_TV_PROVIDER_AUDIT_PATH"] = str(audit)
    params = env["ir.config_parameter"]
    prior = params.search([("key", "=", AUDIT_PARAM)], limit=1)
    old_value = prior.value if prior else None
    created = env["llm.thread"].create({
        "name": f"CC-M4-01 stable pagination {tag}",
        "provider_id": model.provider_id.id,
        "model_id": model.id,
        "user_id": env.uid,
        "tool_ids": [(6, 0, tools.ids)],
    })
    params.set_param(AUDIT_PARAM, str(created.id))
    retriever = env.ref("llm_tool.llm_tool_odoo_record_retriever")
    try:
        walk1 = _walk(retriever, created)
        walk2 = _walk(retriever, created)
        merged1 = [name for page in walk1 for name in page["models"]]
        merged2 = [name for page in walk2 for name in page["models"]]
        result = {
            "database": env.cr.dbname,
            "thread_id": created.id,
            "provider": model.provider_id.name,
            "chat_model": model.name,
            "query": QUERY,
            "registry_count": len(env.registry.models),
            "page_size": PAGE_SIZE,
            "walk1": walk1,
            "walk2": walk2,
            "walk1_count_values": sorted({page["count"] for page in walk1}),
            "walk2_count_values": sorted({page["count"] for page in walk2}),
            "walk1_item_count": len(merged1),
            "walk2_item_count": len(merged2),
            "walk1_unique_count": len(set(merged1)),
            "walk2_unique_count": len(set(merged2)),
            "walks_identical": merged1 == merged2,
            "business_search_invoked": False,
            "office_action_invoked": False,
            "oracle_loaded_by_runner": False,
        }
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(output, stat.S_IRUSR | stat.S_IWUSR)
        print(json.dumps({key: result[key] for key in (
            "registry_count", "walk1_count_values", "walk2_count_values", "walk1_item_count",
            "walk2_item_count", "walk1_unique_count", "walk2_unique_count", "walks_identical",
        )}, ensure_ascii=False, indent=2), flush=True)
        return result
    finally:
        created.unlink()
        current = params.search([("key", "=", AUDIT_PARAM)], limit=1)
        if prior:
            if current:
                current.write({"value": old_value})
            else:
                params.create({"key": AUDIT_PARAM, "value": old_value})
        elif current:
            current.unlink()
        env.cr.commit()
        cleanup_file.write_text(json.dumps({
            "database": env.cr.dbname,
            "thread_id_removed": created.id,
            "audit_parameter_restored": True,
            "provider_usage_retained": True,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(cleanup_file, stat.S_IRUSR | stat.S_IWUSR)
        os.environ.pop("OFFICE_M4_TV_OBSERVABILITY", None)
        os.environ.pop("OFFICE_M4_TV_PROVIDER_AUDIT_PATH", None)
