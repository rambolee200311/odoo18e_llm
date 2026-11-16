"""Independently re-read the committed CC-M3-03 fixture through the Odoo ORM."""

import hashlib
import json
from pathlib import Path


EXPECTED_DB = "odoo18e_llm"
EVIDENCE_DIR = Path("office_engine/docs/implementation/evidence/CC-M3-03")
manifest = json.loads((EVIDENCE_DIR / "fixture_manifest.json").read_text(encoding="utf-8"))
if env.cr.dbname != EXPECTED_DB or manifest.get("database") != EXPECTED_DB:
    raise RuntimeError("Fixture verification refused an unexpected database.")

projects = env["project.project"].search([("name", "=", manifest["project_name"])])
if len(projects) != 1 or projects.id != manifest["project_id"]:
    raise AssertionError("Synthetic fixture project identity did not match the saved manifest.")
orders = env["world.depot.outbound.order"].search([("project", "=", projects.id)], order="id asc")
expected_orders = {item["id"]: item for item in manifest["orders"]}
if set(orders.ids) != set(expected_orders) or len(orders) != 148:
    raise AssertionError("Synthetic source order identity set did not match 148 saved identities.")

actual_order_rows = []
for order in orders:
    expected = expected_orders[order.id]
    actual = {
        "id": order.id,
        "order_number": order.billno,
        "reference": order.reference,
        "date": order.date.isoformat(),
    }
    if actual != {key: expected[key] for key in actual}:
        raise AssertionError(f"Synthetic order fields changed for source identity {order.id}.")
    actual_order_rows.append(actual)

lines = env["world.depot.outbound.order.product"].search(
    [("outbound_order_id", "in", orders.ids)], order="id asc"
)
expected_lines = {item["id"]: item for item in manifest["lines"]}
if set(lines.ids) != set(expected_lines) or len(lines) != manifest["line_count"]:
    raise AssertionError("Synthetic detail identity set did not match the saved manifest.")

actual_line_rows = []
for line in lines:
    actual = {
        "id": line.id,
        "parent_id": line.outbound_order_id.id,
        "product_name": line.product_id.display_name,
        "product_code": line.product_id.default_code,
        "quantity": line.quantity,
    }
    expected = expected_lines[line.id]
    if actual != expected:
        raise AssertionError(f"Synthetic detail or parent relation changed for source identity {line.id}.")
    actual_line_rows.append(actual)

source_snapshot = {"orders": actual_order_rows, "lines": actual_line_rows}
source_sha256 = hashlib.sha256(
    json.dumps(source_snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
verification = {
    "database": EXPECTED_DB,
    "project_name": projects.name,
    "project_id": projects.id,
    "order_count": len(orders),
    "line_count": len(lines),
    "order_identity_count": len({row["id"] for row in actual_order_rows}),
    "line_identity_count": len({row["id"] for row in actual_line_rows}),
    "parent_relation_count": len({(row["parent_id"], row["id"]) for row in actual_line_rows}),
    "source_snapshot_sha256": source_sha256,
    "result": "PASS",
}
(EVIDENCE_DIR / "fixture_verification.json").write_text(
    json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(verification, ensure_ascii=False))
