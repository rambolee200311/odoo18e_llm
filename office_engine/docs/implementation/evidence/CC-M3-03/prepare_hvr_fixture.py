"""Create the CC-M3-03 synthetic fixture from an Odoo shell (ORM only).

Run only with ``-d odoo18e_llm``. The script refuses any other database and
commits only after all 148 orders, their details, and the independent manifest
have been created successfully.
"""

import json
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4


EXPECTED_DB = "odoo18e_llm"
FIXTURE_SIZE = 148
EVIDENCE_DIR = Path("office_engine/docs/implementation/evidence/CC-M3-03")
MANIFEST_PATH = EVIDENCE_DIR / "fixture_manifest.json"


def create_fixture(env):
    if env.cr.dbname != EXPECTED_DB:
        raise RuntimeError(f"Refusing fixture setup on unexpected database: {env.cr.dbname}")
    if MANIFEST_PATH.exists():
        raise FileExistsError(f"Synthetic fixture manifest already exists: {MANIFEST_PATH}")

    marker = uuid4().hex[:10].upper()
    project_name = f"M3 CC03 Synthetic Acceptance {marker}"
    product_prefix = f"M3CC03-{marker}"
    base_date = date(2026, 10, 1)

    with env.cr.savepoint():
        Partner = env["res.partner"]
        Category = env["product.category"]
        Project = env["project.project"]
        Template = env["product.template"]
        Order = env["world.depot.outbound.order"]
        Line = env["world.depot.outbound.order.product"]

        partner = Partner.create({"name": f"{project_name} Synthetic Recipient"})
        category_root = env.ref("product.product_category_all")
        category = Category.create(
            {"name": f"{project_name} Synthetic Category", "parent_id": category_root.id}
        )
        project = Project.create(
            {
                "name": project_name,
                "owner": partner.id,
                "category": category.id,
                "is_check_origin_doc": False,
            }
        )
        unit = env.ref("uom.product_uom_unit")
        products = env["product.product"]
        for suffix, name, weight in (("A", "Synthetic Panel A", 1.25), ("B", "Synthetic Panel B", 2.5)):
            code = f"{product_prefix}-{suffix}"
            template = Template.create(
                {
                    "name": f"{project_name} {name}",
                    "categ_id": category.id,
                    "type": "consu",
                    "uom_id": unit.id,
                    "uom_po_id": unit.id,
                    "is_storable": True,
                    "default_code": code,
                    "barcode": code,
                    "weight": weight,
                    "sale_ok": False,
                    "purchase_ok": False,
                }
            )
            products |= template.product_variant_id

        orders_expected = []
        lines_expected = []
        for index in range(1, FIXTURE_SIZE + 1):
            order = Order.create(
                {
                    "type": "outbound",
                    "date": (base_date + timedelta(days=index - 1)).isoformat(),
                    "project": project.id,
                    "unload_company": partner.id,
                    "reference": f"{product_prefix}-REF-{index:03d}",
                    "state": "new",
                    "is_auto_moves": False,
                }
            )
            if not order.billno:
                raise RuntimeError("The outbound order sequence did not assign an order number.")
            orders_expected.append(
                {
                    "id": order.id,
                    "order_number": order.billno,
                    "reference": order.reference,
                    "date": order.date.isoformat(),
                    "line_ids": [],
                }
            )

            line_specs = [(products[0], float(1 + index % 11))]
            if index % 4 == 0:
                line_specs.append((products[1], float(2 + index % 7)))
            for product, quantity in line_specs:
                line = Line.create(
                    {
                        "outbound_order_id": order.id,
                        "product_id": product.id,
                        "pallets": 1.0,
                        "quantity": quantity,
                        "remark": f"{project_name} synthetic detail",
                    }
                )
                line_expected = {
                    "id": line.id,
                    "parent_id": order.id,
                    "product_name": product.display_name,
                    "product_code": product.default_code,
                    "quantity": quantity,
                }
                orders_expected[-1]["line_ids"].append(line.id)
                lines_expected.append(line_expected)

        manifest = {
            "database": EXPECTED_DB,
            "fixture_marker": marker,
            "project_name": project_name,
            "project_id": project.id,
            "synthetic_partner_id": partner.id,
            "synthetic_category_id": category.id,
            "synthetic_product_template_ids": products.mapped("product_tmpl_id").ids,
            "synthetic_product_ids": products.ids,
            "order_count": len(orders_expected),
            "line_count": len(lines_expected),
            "orders": orders_expected,
            "lines": lines_expected,
        }
        MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    env.cr.commit()
    print(
        json.dumps(
            {
                key: manifest[key]
                for key in ("database", "fixture_marker", "project_name", "order_count", "line_count")
            },
            ensure_ascii=False,
        )
    )


create_fixture(env)
