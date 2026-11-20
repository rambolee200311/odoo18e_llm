"""通过 Odoo ORM 复核 CC-M4-02 Provider 合成数据清理状态。"""

import json
import re
from pathlib import Path


EVIDENCE = Path("office_engine/docs/implementation/evidence/CC-M4-02").resolve()
RUN_TAGS = (
    "provider_constraints_v0.8",
    "provider_constraints_v0.9",
    "provider_constraints_v1.0",
    "provider_constraints_v1.1",
    "provider_ambiguity_v0.1",
    "provider_ambiguity_v0.2",
    "provider_hierarchy_ambiguity_v0.1",
    "provider_hierarchy_ambiguity_v0.2",
    "provider_hierarchy_ambiguity_v0.4",
    "provider_hierarchy_ambiguity_v0.5",
    "provider_hierarchy_ambiguity_v0.6",
    "provider_query_recovery_v0.7",
    "provider_query_recovery_v0.8",
    "provider_hierarchy_ambiguity_v0.9",
)
EXPECTED_AUDIT_ALLOWLIST = "1398"


def run(env):
    """检查 Provider 运行夹具、v0.3 既存审计 Thread 和白名单均已清理/恢复。"""
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

    # v0.3 的结果 JSON 曾被同名重试保护记录替换；从不可变 Provider 审计中取回 Thread 与唯一后缀。
    legacy_audit = EVIDENCE / "provider_hierarchy_ambiguity_v0.3_sdk_audit.jsonl"
    legacy_thread_ids = set()
    legacy_suffixes = set()
    for line in legacy_audit.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        legacy_thread_ids.update(event.get("thread_ids") or [])
        for message in (event.get("payload") or {}).get("messages", []):
            body = message.get("content") or ""
            match = re.search(r"CC-M4-02 Parent ([0-9a-f]{12})", body)
            if match:
                legacy_suffixes.add(match.group(1))
    thread_ids.extend(sorted(legacy_thread_ids))

    # 用 ORM 搜索 v0.3 唯一后缀，以覆盖其结果文件未能保留的临时用户和合成联系人 ID。
    legacy_partner_matches = env["res.partner"].browse()
    legacy_user_matches = env["res.users"].browse()
    for suffix in sorted(legacy_suffixes):
        legacy_partner_matches |= env["res.partner"].search([("name", "ilike", f"%{suffix}%")])
        legacy_user_matches |= env["res.users"].search([("login", "ilike", f"%{suffix}%")])

    remaining_users = env["res.users"].browse(user_ids).exists().ids + legacy_user_matches.exists().ids
    remaining_threads = env["llm.thread"].browse(thread_ids).exists().ids
    remaining_partners = (
        env["res.partner"].browse(sorted(partner_ids)).exists().ids
        + legacy_partner_matches.exists().ids
    )
    remaining_countries = env["res.country"].browse(sorted(reference_country_ids)).exists().ids
    audit_value = env["ir.config_parameter"].get_param("office_engine.m4_tv.audit_thread_ids")
    result = {
        "database": env.cr.dbname,
        "runs": list(RUN_TAGS),
        "user_ids_checked": user_ids,
        "thread_ids_checked": thread_ids,
        "legacy_v0_3_thread_ids_from_provider_audit": sorted(legacy_thread_ids),
        "legacy_v0_3_suffixes_checked_by_orm": sorted(legacy_suffixes),
        "synthetic_partner_ids_checked": sorted(partner_ids),
        "remaining_country_reference_ids": remaining_countries,
        "remaining_user_ids": sorted(set(remaining_users)),
        "remaining_thread_ids": remaining_threads,
        "remaining_synthetic_partner_ids": sorted(set(remaining_partners)),
        "audit_allowlist": audit_value,
        "expected_audit_allowlist": EXPECTED_AUDIT_ALLOWLIST,
        "runner_cleanup_flags": cleanup_flags,
    }
    result["status"] = "PASS" if (
        not remaining_users
        and not remaining_threads
        and not remaining_partners
        and set(remaining_countries) == reference_country_ids
        and audit_value == EXPECTED_AUDIT_ALLOWLIST
        and all(all(flags.values()) for flags in cleanup_flags.values())
    ) else "FAIL"
    output = EVIDENCE / "ATR-RUN-073_postrun_orm_check.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "PASS":
        raise RuntimeError("Odoo ORM cleanup verification failed.")


run(env)
