"""Bounded real-OpenAI schema/tool-call verification for CC-M3-01.

Run from the repository root through ``odoo-bin shell``. The script reads the
existing configured Odoo Provider, sends three synthetic, forced tool calls,
executes the returned arguments through ``llm.tool.execute()``, and rolls back
the shell transaction. It never reads or records the API credential value.
"""

from __future__ import annotations

import copy
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlparse


DB_NAME = "odoo18e_llm"
PROVIDER_NAME = "OpenAI GPT-5.6 Luna"
MODEL_NAME = "gpt-5.6-luna"
TOOL_NAME = "odoo_record_retriever"
EVIDENCE_PATH = Path(
    os.environ.get(
        "CC_M3_PROVIDER_EVIDENCE_PATH",
        "office_engine/docs/implementation/evidence/CC-M3-01/provider_tool_call_evidence_attempt03.json",
    )
).resolve()
TIMEOUT_SECONDS = 45

CASES = [
    {
        "case": "in_array",
        "condition": ["name", "in", ["__cc_m3_01_provider_in_a__", "__cc_m3_01_provider_in_b__"]],
        "scalar_guard": ["id", "=", 0],
        "prompt": (
            "Use the tool exactly once. Search res.partner with domain "
            "[[\"name\",\"in\",[\"__cc_m3_01_provider_in_a__\",\"__cc_m3_01_provider_in_b__\"]],"
            "[\"id\",\"=\",0]]. Set fields to [\"id\"], limit 1, offset 0, "
            "include_pagination true, and order \"id asc\". Preserve the domain exactly."
        ),
    },
    {
        "case": "not_in_array",
        "condition": ["name", "not in", ["__cc_m3_01_provider_not_in__"]],
        "scalar_guard": ["id", "=", 0],
        "prompt": (
            "Use the tool exactly once. Search res.partner with domain "
            "[[\"name\",\"not in\",[\"__cc_m3_01_provider_not_in__\"]],[\"id\",\"=\",0]]. "
            "Set fields to [\"id\"], limit 1, offset 0, include_pagination true, "
            "and order \"id asc\". Preserve the domain exactly."
        ),
    },
    {
        "case": "scalar_condition",
        "condition": ["id", "=", 0],
        "scalar_guard": None,
        "prompt": (
            "Use the tool exactly once. Search res.partner with domain "
            "[[\"id\",\"=\",0]]. Set fields to [\"id\"], limit 1, offset 0, "
            "include_pagination true, and order \"id asc\". Preserve the domain exactly."
        ),
    },
]


class CapturingCompletions:
    def __init__(self, delegate, attempt):
        self._delegate = delegate
        self._attempt = attempt
        self.response = None

    def create(self, **kwargs):
        # This is the exact request body passed by Odoo's OpenAI chat adapter;
        # auth headers and the configured API key are not part of this payload.
        self._attempt["provider_request"] = copy.deepcopy(kwargs)
        self.response = self._delegate.create(**kwargs)
        return self.response


def _tool_call_from_response(normalized):
    calls = normalized.get("tool_calls") or []
    if len(calls) != 1:
        raise RuntimeError("provider_did_not_return_exactly_one_tool_call")
    call = calls[0]
    if call.get("function", {}).get("name") != TOOL_NAME:
        raise RuntimeError("provider_returned_unexpected_tool_name")
    raw_arguments = call["function"].get("arguments")
    arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
    if not isinstance(arguments, dict):
        raise RuntimeError("provider_tool_arguments_are_not_an_object")
    return call, arguments


def _check_arguments(case, arguments):
    operation = arguments.get("operation")
    if operation not in {"search", None} or arguments.get("model") != "res.partner":
        raise RuntimeError("provider_tool_arguments_do_not_match_requested_operation")
    if operation is None and case["case"] != "scalar_condition":
        raise RuntimeError("provider_omitted_operation_for_explicit_array_search")
    domain = arguments.get("domain")
    if not isinstance(domain, list):
        raise RuntimeError("provider_domain_is_not_a_list")
    terms = [term for term in domain if isinstance(term, list) and len(term) == 3]
    if case["condition"] not in terms:
        raise RuntimeError("provider_did_not_preserve_requested_domain_condition")
    if case["scalar_guard"] and case["scalar_guard"] not in terms:
        raise RuntimeError("provider_did_not_preserve_zero_record_guard")
    if arguments.get("fields") != ["id"]:
        raise RuntimeError("provider_fields_differ_from_probe_scope")


def _safe_error_details(exc):
    body = getattr(exc, "body", None)
    if not isinstance(body, dict):
        body = {}
    error = body.get("error") if isinstance(body.get("error"), dict) else body
    message = getattr(exc, "message", None) or error.get("message") or ""
    if not isinstance(message, str):
        message = ""
    message = message[:1200]
    message = re.sub(r"(?i)Bearer\s+\S+", "Bearer [REDACTED]", message)
    message = re.sub(r"(?i)sk-[A-Za-z0-9_-]{12,}", "[REDACTED_KEY]", message)
    message = re.sub(
        r"(?i)(api[_ -]?key|authorization)(\s*[:=]\s*)[^,\s]+",
        r"\1\2[REDACTED]",
        message,
    )
    return {
        "exception_class": type(exc).__name__,
        "http_status": getattr(exc, "status_code", None),
        "request_id": getattr(exc, "request_id", None),
        "provider_code": error.get("code"),
        "provider_param": error.get("param"),
        "provider_type": error.get("type"),
        "provider_message_redacted": message,
    }


def run(env):
    if env.cr.dbname != DB_NAME:
        raise RuntimeError("unexpected_database")
    if EVIDENCE_PATH.exists():
        raise RuntimeError("refusing_to_overwrite_existing_provider_evidence")

    providers = env["llm.provider"].search(
        [
            ("name", "=", PROVIDER_NAME),
            ("service", "=", "openai"),
            ("active", "=", True),
        ]
    )
    models = env["llm.model"].search(
        [
            ("name", "=", MODEL_NAME),
            ("provider_id", "in", providers.ids),
            ("active", "=", True),
        ]
    )
    if len(providers) != 1 or len(models) != 1:
        raise RuntimeError("configured_provider_model_pair_is_not_unique")

    provider = providers
    model = models
    endpoint = (provider.api_base or "https://api.openai.com/v1").strip()
    parsed = urlparse(endpoint)
    if not (
        parsed.scheme == "https"
        and parsed.hostname == "api.openai.com"
        and parsed.path.rstrip("/") == "/v1"
        and parsed.port in (None, 443)
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment
    ):
        raise RuntimeError("configured_endpoint_is_not_standard_openai")
    if not provider.api_key:
        raise RuntimeError("configured_provider_credential_missing")

    tools = env["llm.tool"].search(
        [("name", "=", TOOL_NAME), ("active", "=", True)], limit=1
    )
    if len(tools) != 1:
        raise RuntimeError("retriever_tool_not_unique_or_inactive")
    tool = tools
    formatted_tools = provider.format_tools(tool)
    if (
        not formatted_tools
        or formatted_tools[0].get("type") != "function"
        or formatted_tools[0].get("function", {}).get("name") != TOOL_NAME
    ):
        raise RuntimeError("odoo_openai_tool_formatter_did_not_produce_retriever_function")

    # Use a configured regular Odoo internal user for the ORM tool execution.
    execution_user = env.ref("base.user_admin")
    evidence = {
        "test": "CC-M3-01 TEST-RET-004 Provider facet",
        "status": "running",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "database": DB_NAME,
        "provider": {
            "name": provider.name,
            "service": provider.service,
            "active": bool(provider.active),
            "model": model.name,
            "model_use": model.model_use,
            "reasoning_effort": "none (matches office_engine_m2 GPT-5 tool-call path)",
            "credential_present": bool(provider.api_key),
            "credential_value_recorded": False,
            "endpoint_class": "https://api.openai.com/v1",
            "sdk_automatic_retries": 0,
        },
        "tool_schema_source": "llm.provider.format_tools([odoo_record_retriever])",
        "provider_tool_schema": formatted_tools,
        "execution_user_id": execution_user.id,
        "cases": [],
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)

    base_client = provider.openai_get_client().with_options(
        timeout=TIMEOUT_SECONDS, max_retries=0
    )
    all_passed = True
    try:
        for case in CASES:
            attempt = {"case": case["case"], "status": "started"}
            evidence["cases"].append(attempt)
            proxy = SimpleNamespace(
                chat=SimpleNamespace(
                    completions=CapturingCompletions(base_client.chat.completions, attempt)
                )
            )
            messages = [
                {
                    "role": "system",
                    "content": (
                        "This is a synthetic compatibility probe. Call only the supplied "
                        "odoo_record_retriever function once. Do not add, remove, or change "
                        "any requested argument."
                    ),
                },
                {"role": "user", "content": case["prompt"]},
            ]
            attempt["requested_parameters"] = {
                "operation": "search",
                "model": "res.partner",
                "domain": [case["condition"]]
                + ([case["scalar_guard"]] if case["scalar_guard"] else []),
                "fields": ["id"],
                "limit": 1,
                "offset": 0,
                "order": "id asc",
                "include_pagination": True,
            }
            try:
                with patch.object(
                    type(provider), "openai_get_client", lambda self: proxy
                ):
                    normalized = provider.openai_chat(
                        messages=env["mail.message"].browse([]),
                        model=model,
                        stream=False,
                        tools=tool,
                        prepend_messages=messages,
                        tool_choice={
                            "type": "function",
                            "function": {"name": TOOL_NAME},
                        },
                        reasoning_effort="none",
                    )

                call, arguments = _tool_call_from_response(normalized)
                attempt["provider_response"] = {
                    "request_id": getattr(proxy.chat.completions._delegate, "_request_id", None),
                    "response_id": getattr(getattr(attempt, "response", None), "id", None),
                    "tool_call_id": call.get("id"),
                    "tool_call_type": call.get("type"),
                    "tool_name": call.get("function", {}).get("name"),
                    "tool_call_arguments_raw": call.get("function", {}).get("arguments"),
                }
                # Capture response metadata from the SDK object returned by the
                # actual request, saved by the capture wrapper below.
                response = proxy.chat.completions.response
                if response is not None:
                    usage = getattr(response, "usage", None)
                    attempt["provider_response"].update(
                        {
                            "request_id": getattr(response, "_request_id", None),
                            "response_id": getattr(response, "id", None),
                            "model": getattr(response, "model", None),
                            "finish_reason": getattr(response.choices[0], "finish_reason", None),
                            "usage": usage.model_dump(exclude_none=True) if usage else None,
                        }
                    )
                attempt["returned_tool_arguments"] = arguments
                _check_arguments(case, arguments)
                executed = tool.with_user(execution_user).execute(arguments)
                attempt["tool_execute"] = executed
                legacy_route = arguments.get("operation") is None
                attempt["operation_route"] = "legacy_omitted_operation" if legacy_route else "explicit_search"
                is_envelope = isinstance(executed, dict)
                returned_records = executed.get("records") if is_envelope else executed
                result_count = executed.get("count") if is_envelope else len(returned_records or [])
                execution_succeeded = (
                    is_envelope and "records" in executed and "count" in executed
                    if legacy_route
                    else is_envelope and executed.get("status") == "success"
                )
                attempt["assertions"] = {
                    "operation_contract_match": legacy_route == (case["case"] == "scalar_condition")
                    and arguments.get("model") == "res.partner",
                    "requested_domain_condition_preserved": True,
                    "only_id_field_requested": True,
                    "tool_execute_success": execution_succeeded,
                    "zero_records_returned": returned_records == [] and result_count == 0,
                }
                if not all(attempt["assertions"].values()):
                    raise RuntimeError("tool_execute_result_assertion_failed")
                attempt["status"] = "passed"
            except Exception as exc:
                all_passed = False
                attempt["status"] = "failed"
                attempt["error"] = _safe_error_details(exc)
                attempt["error"]["provider_request_attempted"] = "provider_request" in attempt
                evidence["status"] = "failed"
                evidence["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
                EVIDENCE_PATH.write_text(
                    json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                break
            evidence["status"] = "running"
            EVIDENCE_PATH.write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    finally:
        base_client.close()

    evidence["status"] = "passed" if all_passed and len(evidence["cases"]) == len(CASES) else "failed"
    evidence["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    evidence["provider_request_count"] = sum(
        1 for item in evidence["cases"] if "provider_request" in item
    )
    EVIDENCE_PATH.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    env.cr.rollback()
    print(
        "CC_M3_01_PROVIDER_TEST="
        + json.dumps(
            {
                "status": evidence["status"],
                "database": evidence["database"],
                "model": MODEL_NAME,
                "case_statuses": [
                    {"case": item["case"], "status": item["status"]}
                    for item in evidence["cases"]
                ],
                "provider_request_count": evidence["provider_request_count"],
                "evidence_path": str(EVIDENCE_PATH),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )
    if evidence["status"] != "passed":
        raise SystemExit(1)


run(env)
