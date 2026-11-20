"""通过 Odoo ORM 检查 CC-M4-02 Provider 复测夹具清理状态。"""

import json
from pathlib import Path


EVIDENCE = Path("office_engine/docs/implementation/evidence/CC-M4-02").resolve()
RUN_TAGS = (
    "provider_constraints_v0.8",
    "provider_constraints_v0.9",
    "provider_constraints_v1.0",
    "provider_constraints_v1.1",
)
EXPECTED_AUDIT_ALLOWLIST = "1398"


def run(env):
    """读取各次真实 Provider 运行 ID 并确认 Odoo 业务/线程夹具已清理。"""
    if env.cr.dbname != "odoo18e_llm":
        raise RuntimeError(f"Unexpected database: {env.cr.dbname}")
    user_ids = []
    thread_ids = []
    partner_ids = set()
    reference_country_ids = set()
    cleanup_flags = {}
    for tag in RUN_TAGS:
        data = json.loads((EVIDENCE / f"{tag}_result.json").read_text(encoding="utf-8"))
        if data.get("database") != env.cr.dbname:
            raise RuntimeError(f"Run {tag} used an unexpected database.")
        user_ids.append(data["user_id"])
        thread_ids.append(data["thread_id"])
        oracle = data["test_fixture"]["oracle"]
        for key in ("parent_id", "decoy_ids"):
            value = oracle[key]
            partner_ids.update(value if isinstance(value, list) else [value])
        reference_country_ids.add(oracle["country_id"])
        for key in ("individual_ids", "company_ids", "contact_ids"):
            partner_ids.update(oracle[key])
        cleanup_flags[tag] = data.get("cleanup", {})

    # 用 Odoo ORM 对照脚本自报的清理标记，确认数据库中没有残留夹具。
    remaining_users = env["res.users"].browse(user_ids).exists().ids
    remaining_threads = env["llm.thread"].browse(thread_ids).exists().ids
    remaining_partners = env["res.partner"].browse(sorted(partner_ids)).exists().ids
    remaining_countries = env["res.country"].browse(sorted(reference_country_ids)).exists().ids
    audit_value = env["ir.config_parameter"].get_param("office_engine.m4_tv.audit_thread_ids")
    result = {
        "database": env.cr.dbname,
        "runs": list(RUN_TAGS),
        "user_ids_checked": user_ids,
        "thread_ids_checked": thread_ids,
        "synthetic_partner_ids_checked": sorted(partner_ids),
        "existing_country_reference_ids_checked": sorted(reference_country_ids),
        "remaining_country_reference_ids": remaining_countries,
        "remaining_user_ids": remaining_users,
        "remaining_thread_ids": remaining_threads,
        "remaining_synthetic_partner_ids": remaining_partners,
        "audit_allowlist": audit_value,
        "expected_audit_allowlist": EXPECTED_AUDIT_ALLOWLIST,
        "runner_cleanup_flags": cleanup_flags,
        "status": "PASS",
    }
    result["status"] = "PASS" if not remaining_users and not remaining_threads and not remaining_partners and set(remaining_countries) == reference_country_ids and audit_value == EXPECTED_AUDIT_ALLOWLIST and all(all(flags.values()) for flags in cleanup_flags.values()) else "FAIL"
    output = EVIDENCE / "ATR-RUN-046_postrun_orm_check.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "PASS":
        raise RuntimeError("Odoo ORM cleanup verification failed.")


run(env)
