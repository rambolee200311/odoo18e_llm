"""为开发环境真实 Provider 验收提供严格受限的请求审计开关。"""

import os


_AUDIT_THREAD_IDS_PARAMETER = "office_engine.m4_tv.audit_thread_ids"
_AUDIT_DATABASE = "odoo18e_llm"


def provider_audit_thread_id(env, thread_id):
    """仅对显式允许的开发 Thread 返回 Provider 请求审计关联 ID。

    审计必须同时启用环境开关、指定绝对路径、使用批准的开发库，并在
    ``ir.config_parameter`` allowlist 中列出该 Thread。任一条件不满足即关闭。

    参数：
        env: 当前 Odoo ORM 环境。
        thread_id: 待核验的 Thread ID。

    返回：
        通过全部限制时返回规范化后的整数 ID，否则返回 ``None``。
    """
    path = os.environ.get("OFFICE_M4_TV_PROVIDER_AUDIT_PATH")
    if (
        os.environ.get("OFFICE_M4_TV_OBSERVABILITY") != "1"
        or env.cr.dbname != _AUDIT_DATABASE
        or not path
        or not os.path.isabs(path)
    ):
        return None
    try:
        thread_id = int(thread_id)
        allowed_ids = {
            int(value.strip())
            for value in (
                env["ir.config_parameter"].get_param(_AUDIT_THREAD_IDS_PARAMETER) or ""
            ).split(",")
            if value.strip().isdigit()
        }
    except (TypeError, ValueError, KeyError):
        return None
    return thread_id if thread_id in allowed_ids else None
