from copy import deepcopy

from odoo import models
from odoo.addons.llm_tool.decorators import llm_tool
from odoo.addons.office_engine_m2.models.office_mapping_tools import (
    LLMThreadOfficeTools as M2OfficeTools,
)

from ..services.export_orchestrator import execute_export_records

_BASE_OFFICE_SCHEMA = deepcopy(M2OfficeTools.office._llm_tool_schema)


class OfficeMappingToolM3(models.AbstractModel):
    _inherit = "office.mapping.tool"

    @llm_tool(
        name="office",
        schema=_BASE_OFFICE_SCHEMA,
        destructive_hint=True,
        description=(
            "The existing Office file lifecycle facade, extended with complete Odoo dataset export. "
            "action=export_records collects authorized records and returns a Candidate requiring explicit user acceptance."
        ),
    )
    def office(
        self,
        action: str,
        candidate_version_id: int | None = None,
        confirmation_required: bool | None = None,
        confirmation_reason: str | None = None,
        workbook_source: str | None = None,
        source_query: dict | None = None,
        collections: list[dict] | None = None,
        tables: list[dict] | None = None,
        verification_profile: str | None = None,
    ) -> dict:
        """Dispatch the existing lifecycle or a complete dataset export."""
        if action != "export_records":
            return super().office(
                action,
                candidate_version_id=candidate_version_id,
                confirmation_required=confirmation_required,
                confirmation_reason=confirmation_reason,
            )
        thread, tool_message = self._office_tool_context()
        try:
            return execute_export_records(
                self.env,
                thread,
                tool_message,
                workbook_source=workbook_source,
                source_query=source_query,
                collections=collections or [],
                tables=tables,
                verification_profile=verification_profile,
            )
        except Exception as exc:
            from odoo.exceptions import AccessError, ValidationError
            from .retriever_errors import RetrieverToolError

            if isinstance(exc, AccessError):
                raise
            if isinstance(exc, ValidationError):
                return {
                    "status": "failed",
                    "operation_status": "export_rejected",
                    "operation_executed": False,
                    "action": "export_records",
                    "error_code": "export_plan_or_integrity_invalid",
                    "message": str(exc),
                }
            if isinstance(exc, RetrieverToolError):
                return {
                    "status": "failed",
                    "operation_status": "export_query_failed",
                    "operation_executed": False,
                    "action": "export_records",
                    "error_code": getattr(exc, "error_code", "QUERY_FAILED"),
                    "diagnostic_id": getattr(exc, "diagnostic_id", False),
                    "message": str(exc),
                }
            raise
