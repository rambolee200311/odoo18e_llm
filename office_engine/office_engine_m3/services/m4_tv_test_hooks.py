"""提供受环境、开发库和 Thread 白名单限制的 M4 临时故障注入。"""

import io
import json
import logging
import os
from datetime import datetime, timezone

from odoo.exceptions import ValidationError

from .provider_request_audit import provider_audit_thread_id as _provider_audit_thread_id

_logger = logging.getLogger(__name__)
CONFIG_PARAMETER = "office_engine.m4_tv.test_fault"
TEST_DATABASE = "odoo18e_llm"
_ALLOWED_FAULTS = {"collector_page_failure", "handoff_interruption", "output_identity_mismatch"}


def parse_fault_config(database, enabled, raw_config, thread_id):
    """Pure guard used by both runtime hooks and unit tests."""
    if database != TEST_DATABASE or enabled is not True or not isinstance(raw_config, str):
        return None
    try:
        config = json.loads(raw_config)
    except (TypeError, ValueError):
        return None
    if not isinstance(config, dict) or config.get("fault") not in _ALLOWED_FAULTS:
        return None
    if str(config.get("thread_id")) != str(thread_id):
        return None
    page_size = config.get("page_size")
    if page_size is not None and (type(page_size) is not int or not 1 <= page_size <= 20):
        return None
    return config


def configured_fault(env, thread_id):
    """读取并校验服务端测试配置，不改变当前业务用户身份。

    测试配置只由开发环境管理员维护；普通用户执行工具时仍需读取该配置以匹配
    Thread 白名单，因此仅此配置读取使用 ``sudo``，业务记录查询始终沿用原用户。

    参数：
        env: 当前业务执行环境。
        thread_id: 允许注入故障的目标 Thread ID。

    返回：
        通过全部门禁的故障配置；未启用或不匹配时返回 ``None``。
    """
    if os.environ.get("OFFICE_M4_TV_TEST_HOOKS") != "1" or env.cr.dbname != TEST_DATABASE:
        return None
    try:
        raw = env["ir.config_parameter"].sudo().get_param(CONFIG_PARAMETER)
    except Exception:
        _logger.exception("Unable to read the gated M4 TV test configuration")
        return None
    return parse_fault_config(env.cr.dbname, True, raw, thread_id)


def provider_audit_thread_id(env, thread_id):
    """委托统一的测试审计 allowlist 校验，避免两份门禁逻辑发生偏差。"""
    return _provider_audit_thread_id(env, thread_id)


def _record_fault(env, thread_id, fault, stage, **details):
    """将已触发的隔离故障写入受限审计文件和服务器日志。"""
    record = {
        "event": "m4_tv_fault_injected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": env.cr.dbname,
        "thread_id": int(thread_id),
        "fault": fault,
        "stage": stage,
        "details": details,
    }
    path = os.environ.get("OFFICE_M4_TV_FAULT_AUDIT_PATH")
    if path and os.path.isabs(path):
        fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        try:
            os.write(fd, (json.dumps(record, sort_keys=True) + "\n").encode("utf-8"))
        finally:
            os.close(fd)
    _logger.warning("M4 TV test fault injected: %s", json.dumps(record, sort_keys=True))


def consume_fault(env, thread_id, expected_fault, stage, **details):
    """只为白名单 Thread 消费一次故障，并清空服务端测试参数。"""
    config = configured_fault(env, thread_id)
    if not config or config.get("fault") != expected_fault:
        return None
    env["ir.config_parameter"].sudo().set_param(CONFIG_PARAMETER, "")
    _record_fault(env, thread_id, expected_fault, stage, **details)
    return config


def raise_handoff_interruption(env, thread_id):
    """在完整收集后、调用 Hosted Code Interpreter 前注入一次性中断。"""
    config = consume_fault(
        env,
        thread_id,
        "handoff_interruption",
        "after_complete_collection_before_hosted_ci",
    )
    if config:
        raise ValidationError(
            "M4 test injection: the complete collected dataset was interrupted before Hosted Code Interpreter handoff. "
            "No Candidate was created."
        )


def corrupt_output_identity(env, thread_id, output_bytes, plan):
    """在隔离 Thread 的输出校验前改写记录身份，验证完整性门禁。"""
    config = consume_fault(env, thread_id, "output_identity_mismatch", "after_provider_before_output_validation")
    if not config:
        return output_bytes
    from openpyxl import load_workbook

    root_table = next((table for table in plan.get("tables", []) if table.get("source") == "root"), None)
    if not root_table:
        _record_fault(env, thread_id, config["fault"], "injection_not_applied", reason="missing_root_table")
        raise ValidationError("M4 test injection could not locate the planned root worksheet.")
    workbook = load_workbook(io.BytesIO(output_bytes))
    try:
        if root_table["name"] not in workbook.sheetnames:
            _record_fault(env, thread_id, config["fault"], "injection_not_applied", reason="missing_worksheet")
            raise ValidationError("M4 test injection could not locate the planned root worksheet.")
        sheet = workbook[root_table["name"]]
        headers = [cell.value for cell in sheet[1]]
        if "__office_record_id" not in headers or sheet.max_row < 2:
            _record_fault(env, thread_id, config["fault"], "injection_not_applied", reason="identity_column_missing")
            raise ValidationError("M4 test injection requires one planned root identity cell.")
        column = headers.index("__office_record_id") + 1
        original_id = sheet.cell(row=2, column=column).value
        if type(original_id) is not int:
            _record_fault(env, thread_id, config["fault"], "injection_not_applied", reason="identity_not_integer")
            raise ValidationError("M4 test injection requires an integer root identity cell.")
        injected_id = original_id + 1_000_000_000
        sheet.cell(row=2, column=column).value = injected_id
        output = io.BytesIO()
        workbook.save(output)
        _record_fault(
            env,
            thread_id,
            config["fault"],
            "identity_cell_changed",
            worksheet=root_table["name"],
            row=2,
            original_identity=original_id,
            injected_identity=injected_id,
        )
        return output.getvalue()
    finally:
        workbook.close()
