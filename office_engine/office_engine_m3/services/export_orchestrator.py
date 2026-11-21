"""One-call export orchestration over the current user's ORM and M2 Route B."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from odoo import _
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.office_engine_m2.services.candidate_validator import (
    validate_fileless_created_workbook,
    validate_workbook_candidate,
)
from odoo.addons.office_engine_m2.services.edit_orchestrator import (
    XLSX_MIME,
    _latest_user_message,
    _message_text,
    _provider_dependencies,
    _resolve_current,
)
from odoo.addons.office_engine_m2.services.mapping_service import create_fileless_session
from odoo.addons.office_engine_m2.services.workbook_version_service import (
    MAX_VERSION_BYTES,
    _read_attachment,
    _require_session,
    _require_version,
    _write_version,
    fail_export_edit_attempt,
    fail_fileless_creation_request,
    register_export_edit_attempt,
    register_fileless_creation_request,
    store_export_edit_attempt_output,
    store_fileless_creation_output,
)

from .data_handoff import build_provider_instruction, canonical_json, sha256_hex
from .dataset_collector import collect_export_dataset
from .export_verification import verify_export_workbook
from .m4_tv_test_hooks import corrupt_output_identity, raise_handoff_interruption


_logger = logging.getLogger(__name__)
_CARRIER_PATH = Path(__file__).resolve().parents[1] / "static" / "blank_carrier.xlsx"


def _blank_carrier_bytes():
    try:
        content = _CARRIER_PATH.read_bytes()
    except OSError as exc:
        raise ValidationError(_("The static XLSX carrier is unavailable.")) from exc
    if not content or len(content) > 64_000:
        raise ValidationError(_("The static XLSX carrier is invalid."))
    return content


def _safe_provider_metadata(result):
    cleanup = getattr(result, "cleanup_state", "unknown")
    cleanup_state = {
        "not_required": "not_applicable",
        "completed": "complete",
        "cleanup_pending": "pending",
        "unknown": "pending",
    }.get(cleanup, "pending")
    return {
        "provider_response_id": getattr(result, "provider_response_id", False),
        "provider_tool_call_id": (getattr(result, "tool_call_ids", ()) or (False,))[0],
        "provider_file_id": (getattr(result, "provider_file_ids", ()) or (False,))[0],
        "provider_usage_json": getattr(result, "usage", {}) or {},
        "provider_cleanup_state": cleanup_state,
    }


def _write_integrity_receipt(
    version, source_kind, provider_input_sha256, collected, instruction_sha, instruction_bytes, verification
):
    plan_sha = sha256_hex(canonical_json(collected["plan"]).encode("utf-8"))
    relation_sha = sha256_hex(canonical_json(collected["relation_pair_sha256"]).encode("utf-8"))
    is_projection = collected["plan"]["verification_profile"] == "record_projection"
    expected_rows = collected["root_count"] + collected["relation_pair_count"] if is_projection else None
    receipt = {
        "schema_version": "office.data-handoff-receipt.v3",
        "source": {
            "kind": source_kind,
            "query_sha256": plan_sha,
            "root_count": collected["root_count"],
            "collected_count": collected["root_count"],
            "identity_sha256": collected["root_identity_sha256"],
            "relation_pair_count": collected["relation_pair_count"],
            "relation_sha256": relation_sha,
            "security_scope_sha256": collected["security_scope_sha256"],
        },
        "handoff": {
            "profile": "hosted_ci_instruction_json_v1",
            "payload_bytes": collected["payload_bytes"],
            "payload_sha256": collected["handoff_sha256"],
            "record_count": collected["root_count"] + collected["relation_record_count"],
            "submitted": True,
            "provider_input_sha256": provider_input_sha256,
            "provider_instruction_sha256": instruction_sha,
            "provider_instruction_bytes": instruction_bytes,
        },
        "workbook": {
            "profile": collected["plan"]["verification_profile"],
            "integrity_validation": "verified",
            "task_computation": "provider_generated",
            "semantic_verification": "projection_verified" if is_projection else "not_independently_recomputed",
            "expected_records": expected_rows,
            "matched_records": verification.get("projected_rows") if is_projection else None,
            "projection": verification,
        },
        "collection_window": {
            "started_at": collected["collection_started_at"],
            "completed_at": collected["collection_completed_at"],
            "source_view": collected["source_view"],
            "read_consistency": collected["read_consistency"],
        },
        "freshness": {"checked_at_collection": True, "requeried_before_accept": False},
        "candidate_version_id": version.id,
        "output_sha256": version.output_sha256,
    }
    encoded = canonical_json(receipt)
    if len(encoded.encode("utf-8")) > 16_384:
        raise ValidationError(_("The export integrity receipt exceeds its bound."))
    _write_version(version, {"data_integrity_receipt_json": encoded})
    return receipt


def _result(status, operation_status, **values):
    return {
        "status": status,
        "operation_status": operation_status,
        "operation_executed": False,
        "artifact_state": "not_presented",
        "delivery_state": "not_finalized",
        "action": "export_records",
        **values,
    }


def _candidate_result(version, session, collected, verification, *, provider_result=None, receipt=None):
    attachment = version.output_attachment_id
    attachment.check("read")
    unverified = []
    if collected["plan"]["verification_profile"] != "record_projection":
        unverified.append("复杂聚合或语义转换由 Hosted Code Interpreter 执行，本地未重算其业务语义。")
    elif version.validation_result == "PARTIALLY_VERIFIED":
        unverified.append("源记录身份及计划字段已逐行核对；M2 的 XLSX 结构验证等级仍为 PARTIALLY_VERIFIED。")
    return _result(
        "confirmation_required",
        "candidate_review_required",
        candidate_version_id=version.id,
        candidate_state=version.state,
        validation_result=version.validation_result,
        candidate_filename=attachment.name,
        candidate_download_url=f"/web/content/{attachment.id}?download=true",
        candidate_output_sha256=version.output_sha256,
        session_id=session.id,
        current_version_id=session.current_version_id.id or False,
        last_valid_version_id=session.last_valid_version_id.id or False,
        document_revision=session.document_revision,
        workbook_source=(receipt.get("source", {}).get("kind") if receipt else None),
        provider_input_sha256=(receipt.get("handoff", {}).get("provider_input_sha256") if receipt else None),
        source_record_count=collected["root_count"],
        source_relation_record_count=collected["relation_record_count"],
        source_relation_pair_count=collected["relation_pair_count"],
        handoff_sha256=collected["handoff_sha256"],
        handoff_bytes=collected["payload_bytes"],
        projection_verification=verification,
        requires_user_acceptance=True,
        provider=provider_result.to_dict() if provider_result else None,
        unverified_aspects=unverified,
        message=(
            "The complete bounded dataset was handed to Hosted Code Interpreter and an XLSX Candidate was saved. "
            "Current was not changed. Review the Candidate and explicitly accept or reject it."
        ),
    )


def _fail_candidate(version, error_code):
    if version.state in {"verified", "partially_verified"}:
        _write_version(version, {"state": "failed", "error_code": error_code})


def _run_candidate_checks(env, session, version, collected):
    version.invalidate_recordset()
    if version.state == "candidate_received":
        if session.origin_kind == "fileless" and version.version_kind == "initial":
            validate_fileless_created_workbook(env, session.id, version.id)
        else:
            validate_workbook_candidate(env, session.id, version.id)
        version.invalidate_recordset()
        session.invalidate_recordset()
    if version.state not in {"verified", "partially_verified"}:
        return None, None
    content, actual_sha = _read_attachment(env, version.output_attachment_id, expected_sha=version.output_sha256)
    if actual_sha != version.output_sha256 or len(content) != version.file_size:
        raise ValidationError(_("The Candidate file changed before output verification."))
    verification = verify_export_workbook(content, version.filename, collected)
    return verification, content


def execute_export_records(
    env,
    thread,
    tool_message,
    *,
    workbook_source,
    source_query,
    collections,
    tables,
    verification_profile,
    adapter=None,
    provider_client=None,
    model=None,
    limits=None,
    page_size=None,
):
    """Collect a complete dataset, call Hosted CI, then leave a reviewable Candidate."""
    if workbook_source not in {"new", "current"}:
        raise ValidationError(_("workbook_source must be new or current."))
    dependencies = None
    if adapter is None or provider_client is None or not model or limits is None:
        dependencies = _provider_dependencies(env, thread)
        if not dependencies:
            return _result(
                "blocked", "provider_dispatch_disabled",
                error_code="external_file_processing_not_authorized",
                message="External file processing is disabled by trusted server configuration; no Provider request was sent.",
            )
        adapter, provider_client, model, limits = dependencies

    user_message = _latest_user_message(env, thread)
    current_context = None
    if workbook_source == "current":
        current_context = _resolve_current(env, thread)
        if current_context["user_message"] != user_message:
            raise AccessError(_("The export intent is not the current user message."))

    collected = collect_export_dataset(
        env,
        source_query,
        collections,
        tables,
        verification_profile,
        page_size=page_size,
        test_thread_id=thread.id,
    )
    raise_handoff_interruption(env, thread.id)
    if workbook_source == "new":
        input_bytes = _blank_carrier_bytes()
        source_sha = sha256_hex(input_bytes)
        session_context = create_fileless_session(
            env, thread_id=thread.id, intent_message_id=user_message.id
        )
        session = _require_session(env, session_context["session_id"], write=True)
        current = False
        parent_version_id = False
    else:
        input_bytes = current_context["input_bytes"]
        source_sha = current_context["input_sha256"]
        session = current_context["session"]
        current = current_context["current"]
        parent_version_id = current.id

    plan_digest = sha256_hex(canonical_json(collected["plan"]).encode("utf-8"))
    facts = {
        "thread_id": thread.id,
        "owner_id": env.uid,
        "session_id": session.id,
        "intent_message_id": user_message.id,
        "workbook_source": workbook_source,
        "plan_sha256": plan_digest,
        "handoff_sha256": collected["handoff_sha256"],
        "input_sha256": source_sha,
        "provider_model": model,
    }
    facts_bytes = canonical_json(facts).encode("utf-8")
    request_digest = sha256_hex(facts_bytes)
    idempotency_key = "m3-export:" + request_digest[:48]
    instruction, instruction_sha, instruction_bytes = build_provider_instruction(
        _message_text(user_message), collected, input_sha256=source_sha
    )

    if workbook_source == "new":
        version, created = register_fileless_creation_request(
            env,
            session.id,
            intent_message_id=user_message.id,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            model=model,
        )
    else:
        version, created = register_export_edit_attempt(
            env,
            session.id,
            parent_version_id=parent_version_id,
            expected_document_revision=session.document_revision,
            intent_message_id=user_message.id,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            provider_model=model,
        )

    provider_result = None
    if created:
        try:
            provider_result = adapter.execute(
                provider_client=provider_client,
                model=model,
                input_xlsx=input_bytes,
                instruction=instruction,
                limits=limits,
                operation="edit",
                input_sha256=source_sha,
                correlation_id=request_digest[:64],
            )
        except Exception:
            _logger.exception("M3 export Provider outcome is unknown (thread_id=%s, request=%s)", thread.id, request_digest[:12])
            return _result(
                "indeterminate", "provider_outcome_unknown",
                version_id=version.id,
                request_digest=request_digest,
                provider_input_sha256=source_sha,
                error_code="provider_outcome_unknown",
                current_version_id=session.current_version_id.id or False,
                message="The Provider outcome is unknown. This request is recorded and will not be automatically repeated.",
            )
        provider_status = getattr(provider_result, "operation_status", None)
        output_bytes = getattr(provider_result, "candidate_bytes", None)
        if provider_status != "candidate_received" or not isinstance(output_bytes, bytes) or not output_bytes:
            if provider_status != "indeterminate":
                error_code = getattr(getattr(provider_result, "error", None), "category", "provider_export_failed")
                safe_error = error_code if isinstance(error_code, str) and error_code.isidentifier() else "provider_export_failed"
                if workbook_source == "new":
                    fail_fileless_creation_request(env, version.id, safe_error)
                else:
                    fail_export_edit_attempt(env, version.id, safe_error)
            return _result(
                "indeterminate" if provider_status == "indeterminate" else "failed",
                "provider_export_unavailable",
                version_id=version.id,
                request_digest=request_digest,
                source_record_count=collected["root_count"],
                source_relation_record_count=collected["relation_record_count"],
                source_relation_pair_count=collected["relation_pair_count"],
                handoff_sha256=collected["handoff_sha256"],
                handoff_bytes=collected["payload_bytes"],
                provider_instruction_sha256=instruction_sha,
                provider_input_sha256=source_sha,
                error_code=getattr(getattr(provider_result, "error", None), "category", "provider_result_unavailable"),
                provider=provider_result.to_dict(),
                current_version_id=session.current_version_id.id or False,
                message="The Provider did not return a usable XLSX Candidate; Current was not advanced.",
            )
        output_bytes = corrupt_output_identity(env, thread.id, output_bytes, collected["plan"])
        filename = getattr(provider_result, "provider_filename", None)
        if not isinstance(filename, str) or not filename.lower().endswith(".xlsx"):
            filename = "export.xlsx"
        provider_fields = _safe_provider_metadata(provider_result)
        if workbook_source == "new":
            store_fileless_creation_output(
                env,
                version.id,
                content=output_bytes,
                filename=filename,
                mimetype=XLSX_MIME,
                **provider_fields,
            )
        else:
            store_export_edit_attempt_output(
                env,
                version.id,
                content=output_bytes,
                filename=filename,
                mimetype=XLSX_MIME,
                **provider_fields,
            )

    version = _require_version(env, session, version.id, write=True)
    session.invalidate_recordset()
    version.invalidate_recordset()
    if version.state == "verifying" and not version.output_attachment_id:
        return _result(
            "indeterminate", "provider_outcome_unknown",
            version_id=version.id,
            request_digest=request_digest,
            current_version_id=session.current_version_id.id or False,
            message="A Provider attempt is still recorded without a persisted output. It will not be silently repeated.",
        )
    if version.state == "failed":
        return _result(
            "failed", "export_attempt_failed", version_id=version.id,
            error_code=version.error_code or "export_candidate_failed",
            current_version_id=session.current_version_id.id or False,
            message="The export attempt failed; Current remains unchanged.",
        )
    try:
        verification, _output = _run_candidate_checks(env, session, version, collected)
    except AccessError:
        raise
    except ValidationError as exc:
        _logger.info("M3 export verification failed (version_id=%s): %s", version.id, exc)
        _fail_candidate(version, "export_integrity_failed")
        return _result(
            "failed", "export_integrity_failed", version_id=version.id,
            candidate_state="failed", current_version_id=session.current_version_id.id or False,
            error_code="export_integrity_failed",
            source_record_count=collected["root_count"],
            source_relation_record_count=collected["relation_record_count"],
            source_relation_pair_count=collected["relation_pair_count"],
            handoff_sha256=collected["handoff_sha256"],
            handoff_bytes=collected["payload_bytes"],
            provider_instruction_sha256=instruction_sha,
            provider_input_sha256=source_sha,
            provider=provider_result.to_dict() if provider_result else None,
            message=str(exc),
        )
    if not verification:
        return _result(
            "failed", "export_candidate_not_reviewable", version_id=version.id,
            candidate_state=version.state, current_version_id=session.current_version_id.id or False,
            error_code=version.error_code or "export_candidate_not_reviewable",
            message="The generated workbook did not reach a reviewable validation state.",
        )
    receipt = _write_integrity_receipt(
        version,
        workbook_source,
        source_sha,
        collected,
        instruction_sha,
        instruction_bytes,
        verification,
    )
    session.invalidate_recordset()
    version.invalidate_recordset()
    return _candidate_result(
        version, session, collected, verification, provider_result=provider_result, receipt=receipt
    )
