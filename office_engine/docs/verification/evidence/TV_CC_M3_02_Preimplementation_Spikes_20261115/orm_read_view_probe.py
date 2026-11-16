"""Read-only Odoo ORM probe for the OPEN-03 minimum feasibility spike.

Run with the existing Odoo development database only:
  ./venv/bin/python ./odoo-bin shell -c ./odoo.conf -d odoo18e_llm --no-http

Paste this body into the shell. It reads only ir.model metadata and does not
write or commit records.
"""
import json

cr = env.cr
cnx = getattr(cr, "_cnx", None)
connection_id = id(cnx) if cnx is not None else None
pages = []
for offset in (0, 10, 20):
    rows = env["ir.model"].search([], order="id", limit=10, offset=offset)
    pages.append({
        "offset": offset,
        "count": len(rows),
        "first_id": rows[:1].id or None,
        "last_id": rows[-1:].id or None,
        "same_cursor": env.cr is cr,
        "same_connection": id(getattr(env.cr, "_cnx", None)) == connection_id,
    })
level = getattr(cnx, "isolation_level", None)
print(json.dumps({
    "db": env.cr.dbname,
    "uid": env.uid,
    "connection_identity_stable": all(page["same_connection"] for page in pages),
    "pages": pages,
    "isolation_level_code": level,
    "repeatable_read": level == 2,
}, sort_keys=True))
