"""只读核对 CC-M4-02 回归后的模块版本及合成测试数据清理状态。"""

import json


def run(env):
    """通过 Odoo ORM 收集指定开发库的安装版本和测试夹具残留计数。"""
    if env.cr.dbname != "odoo18e_llm":
        raise RuntimeError(f"Unexpected database: {env.cr.dbname}")

    modules = env["ir.module.module"].search(
        [("name", "in", ["office_engine_m2", "office_engine_m3"])],
        order="name",
    )
    users = env["res.users"].search_count([("login", "ilike", "cc-m4-02-%")])
    partners = env["res.partner"].search_count([("name", "ilike", "CC-M4-02 %")])
    threads = env["llm.thread"].search_count([("name", "ilike", "CC-M4-02 synthetic task %")])
    audit_allowlist = env["ir.config_parameter"].get_param(
        "office_engine.m4_tv.audit_thread_ids",
        default=False,
    )

    result = {
        "database": env.cr.dbname,
        "modules": [
            {
                "name": module.name,
                "state": module.state,
                "installed_version": module.installed_version,
                "latest_version": module.latest_version,
            }
            for module in modules
        ],
        "synthetic_test_users_remaining": users,
        "synthetic_test_partners_remaining": partners,
        "synthetic_test_threads_remaining": threads,
        "provider_audit_allowlist_restored_value": audit_allowlist,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


run(env)
