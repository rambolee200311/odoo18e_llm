"""Independently verify a real Agent XLSX against the CC-M3-03 synthetic fixture.

Run inside ``odoo-bin shell`` with ``CC_M3_03_VERSION_ID`` and optionally
``CC_M3_03_ARTIFACT_PATH`` set. Reads Odoo records and attachment bytes through
the ORM; it does not call a Provider, mutate business data, or prepare tool args.
"""

import hashlib
import json
import os
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook


EXPECTED_DB = "odoo18e_llm"
EVIDENCE_DIR = Path("office_engine/docs/implementation/evidence/CC-M3-03")
if env.cr.dbname != EXPECTED_DB:
    raise RuntimeError("Workbook verification refused an unexpected database.")

manifest = json.loads((EVIDENCE_DIR / "fixture_manifest.json").read_text(encoding="utf-8"))
fixture_check = json.loads((EVIDENCE_DIR / "fixture_verification.json").read_text(encoding="utf-8"))
agent_plan = json.loads((EVIDENCE_DIR / "hvr_agent_plan_thread_677.json").read_text(encoding="utf-8"))
version_id = int(os.environ["CC_M3_03_VERSION_ID"])
version = env["office.workbook.version"].browse(version_id).exists()
if not version or version.state not in {"partially_verified", "verified", "accepted_current", "finalized"}:
    raise AssertionError("The selected Candidate is not a reviewable or finalized workbook version.")
if version.session_id.origin_kind != "fileless" or version.version_kind != "initial":
    raise AssertionError("The selected workbook does not use the authorized new-workbook flow.")
if version.thread_id.id != agent_plan["thread_id"]:
    raise AssertionError("The workbook version does not belong to the recorded real Agent UI run.")

attachment = version.output_attachment_id
attachment.check("read")
content = bytes(attachment.raw)
file_sha = hashlib.sha256(content).hexdigest()
if file_sha != version.output_sha256 or len(content) != version.file_size:
    raise AssertionError("Workbook attachment bytes do not match the stored SHA or size.")

receipt = json.loads(version.data_integrity_receipt_json or "{}")
if receipt.get("output_sha256") != file_sha:
    raise AssertionError("Candidate / final workbook SHA does not match its integrity receipt.")

expected_orders = {item["id"]: item for item in manifest["orders"]}
expected_lines = {item["id"]: item for item in manifest["lines"]}
if len(expected_orders) != 148 or len(expected_lines) != 185:
    raise AssertionError("The saved synthetic manifest does not contain the authorized 148/185 fixture.")

root_tables = [table for table in agent_plan["tables"] if table["source"] == "root"]
relation_tables = [table for table in agent_plan["tables"] if table["source"] != "root"]
if len(root_tables) != 1 or len(relation_tables) != 1:
    raise AssertionError("The recorded Agent plan must contain one root and one direct relation table.")
root_table = root_tables[0]
relation_table = relation_tables[0]
root_fields = [column["source_field"] for column in root_table["columns"]]
relation_fields = [column["source_field"] for column in relation_table["columns"]]
if set(root_fields) != {"billno", "reference", "date"} or len(root_fields) != 3:
    raise AssertionError("The Agent plan does not contain exactly the requested root business fields.")
if set(relation_fields) != {"product_id", "quantity"} or len(relation_fields) != 2:
    raise AssertionError("The Agent plan does not contain exactly the requested detail business fields.")
if relation_table["source"] not in {item["key"] for item in agent_plan["collections"]}:
    raise AssertionError("The Agent relation worksheet is not backed by its discovered collection.")


def _record_id(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _expected_value(source, field, record_id):
    if source == "root":
        record = expected_orders[record_id]
        return {
            "billno": record["order_number"],
            "reference": record["reference"],
            "date": record["date"],
        }[field]
    record = expected_lines[record_id]
    return {
        "product_id": record["product_name"],
        "quantity": record["quantity"],
    }[field]


def _date_string(value):
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.isoformat()
    return value

workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
seen_orders = set()
seen_lines = set()
seen_pairs = set()
try:
    expected_sheet_names = {root_table["name"], relation_table["name"]}
    if set(workbook.sheetnames) != expected_sheet_names:
        raise AssertionError(f"Unexpected output worksheets: {workbook.sheetnames!r}")

    root_rows = list(workbook[root_table["name"]].iter_rows(values_only=True))
    root_headers = list(root_rows.pop(0))
    while root_headers and root_headers[-1] in (None, ""):
        root_headers.pop()
    root_labels = [column["label"] for column in root_table["columns"]]
    if root_headers != root_labels + ["__office_record_id"]:
        raise AssertionError("The root worksheet headers do not match the Agent plan and identity contract.")
    root_index = {name: index for index, name in enumerate(root_headers)}
    root_ids = []
    for row in root_rows:
        record_id = _record_id(row[root_index["__office_record_id"]])
        if record_id in seen_orders or record_id not in expected_orders:
            raise AssertionError(f"Unexpected or duplicate root identity: {record_id!r}")
        seen_orders.add(record_id)
        root_ids.append(record_id)
        for column in root_table["columns"]:
            actual = row[root_index[column["label"]]]
            expected = _expected_value("root", column["source_field"], record_id)
            if column["source_field"] == "date":
                actual = _date_string(actual)
            if actual != expected:
                raise AssertionError(f"Root row values differ for source identity {record_id}.")
    if seen_orders != set(expected_orders):
        raise AssertionError("Root worksheet identities do not exactly match the 148-record source set.")
    if root_ids != sorted(expected_orders):
        raise AssertionError("Root worksheet rows do not preserve the selected stable source order.")

    detail_rows = list(workbook[relation_table["name"]].iter_rows(values_only=True))
    detail_headers = list(detail_rows.pop(0))
    while detail_headers and detail_headers[-1] in (None, ""):
        detail_headers.pop()
    detail_labels = [column["label"] for column in relation_table["columns"]]
    if detail_headers != detail_labels + ["__office_parent_id", "__office_record_id"]:
        raise AssertionError("The relation worksheet headers do not match the Agent plan and identity contract.")
    detail_index = {name: index for index, name in enumerate(detail_headers)}
    line_ids = []
    for row in detail_rows:
        line_id = _record_id(row[detail_index["__office_record_id"]])
        parent_id = _record_id(row[detail_index["__office_parent_id"]])
        if line_id in seen_lines or line_id not in expected_lines:
            raise AssertionError(f"Unexpected or duplicate detail identity: {line_id!r}")
        seen_lines.add(line_id)
        line_ids.append(line_id)
        line = expected_lines[line_id]
        if parent_id != line["parent_id"]:
            raise AssertionError(f"Detail {line_id} is associated with the wrong parent identity.")
        for column in relation_table["columns"]:
            actual = row[detail_index[column["label"]]]
            expected = _expected_value(relation_table["source"], column["source_field"], line_id)
            if actual != expected:
                raise AssertionError(f"Detail values differ for source identity {line_id}.")
        seen_pairs.add((parent_id, line_id))
    if seen_lines != set(expected_lines):
        raise AssertionError("Detail worksheet identities do not exactly match the 185-record source set.")
    if len(seen_pairs) != 185:
        raise AssertionError("The detail worksheet does not contain 185 unique parent/detail pairs.")
    if line_ids != sorted(expected_lines):
        raise AssertionError("Relation worksheet rows do not preserve the selected stable source order.")
finally:
    workbook.close()

artifact_path = Path(os.environ.get(
    "CC_M3_03_ARTIFACT_PATH",
    str(EVIDENCE_DIR / f"downloaded_version_{version.id}.xlsx"),
))
artifact_path.parent.mkdir(parents=True, exist_ok=True)
artifact_path.write_bytes(content)

result = {
    "database": EXPECTED_DB,
    "thread_id": version.thread_id.id,
    "session_id": version.session_id.id,
    "version_id": version.id,
    "version_state": version.state,
    "filename": attachment.name,
    "file_size": len(content),
    "candidate_or_final_sha256": file_sha,
    "fixture_source_snapshot_sha256": fixture_check["source_snapshot_sha256"],
    "source_identity_sha256": receipt.get("source", {}).get("identity_sha256"),
    "handoff_sha256": receipt.get("handoff", {}).get("payload_sha256"),
    "provider_input_sha256": receipt.get("handoff", {}).get("provider_input_sha256"),
    "root_records": len(seen_orders),
    "detail_records": len(seen_lines),
    "parent_detail_pairs": len(seen_pairs),
    "worksheets": workbook.sheetnames,
    "root_source_fields": root_fields,
    "relation_source_fields": relation_fields,
    "artifact_path": str(artifact_path),
    "result": "PASS",
}
result_path = EVIDENCE_DIR / f"workbook_verification_v{version.id}.json"
result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
