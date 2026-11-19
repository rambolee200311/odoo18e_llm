"""Repeated full-page walk of the real discover implementation.

Run in ``odoo-bin shell``. The synthetic Thread and all ORM work are rolled
back. This test reads Registry metadata only and invokes no business search.
"""

import json
from pathlib import Path
from types import SimpleNamespace


BASE = Path("office_engine/docs/implementation/evidence/CC-M4-01")
EXPECTED_DB = "odoo18e_llm"
MODEL_NAME = "gpt-5.6-luna"
PROVIDER_NAME = "OpenAI GPT-5.6 Luna"
QUERY = "只识别并描述客户、供应商和联系人档案对应的数据对象及字段，不读取记录。"
PAGE_LIMIT = 20
OUTPUT = BASE / "provider_discovery_pagination_v0.1.json"


def _walk(retriever, query):
    """处理 `_walk` 所标识的输入、状态或结果。参数：`retriever`：参与该处理的输入值，具体格式沿用现有调用约定。；`query`：检索或处理所用的查询条件。 返回：返回当前实现读取、校验或计算得到的结果；异常遵循现有错误契约传播。"""
    pages = []
    offset = 0
    expected_count = None
    while expected_count is None or offset < expected_count:
        page = retriever._retriever_discover(query=query, limit=PAGE_LIMIT, offset=offset)
        if expected_count is None:
            expected_count = page["count"]
        pages.append({
            "offset": page["offset"],
            "limit": page["limit"],
            "count": page["count"],
            "returned_count": page["returned_count"],
            "has_more": page["has_more"],
            "next_offset": page["next_offset"],
            "models": [row["model"] for row in page["models"]],
        })
        offset += PAGE_LIMIT
        if len(pages) > 100:
            raise RuntimeError("Unexpected discover pagination loop.")
    return pages


def run_discovery_pagination(env):
    """运行 `run_discovery_pagination` 所标识的输入、状态或结果。参数：`env`：当前 Odoo ORM 环境。 返回：无显式返回值；通过现有副作用或状态更新完成处理。"""
    if env.cr.dbname != EXPECTED_DB:
        raise RuntimeError(f"Unexpected database: {env.cr.dbname}")
    model = env["llm.model"].search([("name", "=", MODEL_NAME)], limit=2)
    if len(model) != 1 or model.provider_id.name != PROVIDER_NAME or model.provider_id.service != "openai":
        raise RuntimeError("The approved GPT-5.6 Luna provider/model is unavailable or ambiguous.")
    thread = env["llm.thread"].create({
        "name": "CC-M4-01 discover pagination probe",
        "provider_id": model.provider_id.id,
        "model_id": model.id,
        "user_id": env.uid,
        "tool_ids": [(6, 0, env.ref("llm_tool.llm_tool_odoo_record_retriever").ids)],
    })
    retriever = env.ref("llm_tool.llm_tool_odoo_record_retriever").with_context(
        message=SimpleNamespace(model="llm.thread", res_id=thread.id)
    )
    walk1 = _walk(retriever, QUERY)
    walk2 = _walk(retriever, QUERY)
    merged1 = [model_name for page in walk1 for model_name in page["models"]]
    merged2 = [model_name for page in walk2 for model_name in page["models"]]
    result = {
        "database": env.cr.dbname,
        "thread_id": thread.id,
        "provider": model.provider_id.name,
        "chat_model": model.name,
        "query": QUERY,
        "registry_models": len(env.registry.models),
        "page_limit": PAGE_LIMIT,
        "walk1": walk1,
        "walk2": walk2,
        "walk1_count_values": sorted({page["count"] for page in walk1}),
        "walk2_count_values": sorted({page["count"] for page in walk2}),
        "walk1_merged_count": len(merged1),
        "walk2_merged_count": len(merged2),
        "walk1_unique_count": len(set(merged1)),
        "walk2_unique_count": len(set(merged2)),
        "walks_identical": merged1 == merged2,
    }
    result["pass"] = bool(
        result["walk1_count_values"] == result["walk2_count_values"]
        and len(result["walk1_count_values"]) == 1
        and len(result["walk2_count_values"]) == 1
        and result["walk1_merged_count"] == result["walk1_count_values"][0]
        and result["walk2_merged_count"] == result["walk2_count_values"][0]
        and result["walk1_unique_count"] == result["walk1_merged_count"]
        and result["walk2_unique_count"] == result["walk2_merged_count"]
        and result["walks_identical"]
    )
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key not in {"walk1", "walk2"}}, ensure_ascii=False), flush=True)
    print(f"Pagination evidence: {OUTPUT}", flush=True)
