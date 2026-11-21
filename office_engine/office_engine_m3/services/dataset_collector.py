"""Deterministic, current-user ORM collection for a resolved export plan."""

from __future__ import annotations

import hashlib
import json
import re

from odoo import _, fields
from odoo.exceptions import AccessError, ValidationError

from .m4_tv_test_hooks import configured_fault, consume_fault


_PAGE_SIZE = 100
_MAX_PAGE_SIZE = 500
_MAX_DOMAIN_LIST = 1000
_MAX_ROOT_ROWS = 25000
_MAX_RELATION_ROWS = 50000
_MAX_PAGES = 1000
_MAX_HANDOFF_BYTES = 1_000_000
_COLLECTION_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


def _canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    )


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _unique(values, label):
    result = []
    seen = set()
    for value in values:
        if value in seen:
            raise ValidationError(_("Duplicate %(label)s in the export plan.", label=label))
        seen.add(value)
        result.append(value)
    return result


def _as_relation_ids(value, *, many2one=False):
    if value in (False, None):
        return []
    if isinstance(value, int) and not isinstance(value, bool):
        return [value]
    if not isinstance(value, (list, tuple)):
        raise ValidationError(_("The ORM returned an invalid relation value."))
    if (
        many2one
        and len(value) == 2
        and isinstance(value[0], int)
        and not isinstance(value[0], bool)
        and isinstance(value[1], str)
    ):
        return [value[0]]
    result = []
    for item in value:
        if isinstance(item, int) and not isinstance(item, bool):
            result.append(item)
        elif isinstance(item, (list, tuple)) and item and isinstance(item[0], int) and not isinstance(item[0], bool):
            result.append(item[0])
        else:
            raise ValidationError(_("The ORM returned an invalid relation identity."))
    return result


def _chunks(values, size):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _read_pages(model, domain, fields, order, *, page_size, max_rows, row_budget=None, test_thread_id=None):
    """按稳定顺序读取全部分页，并仅在隔离测试 Thread 上执行受控故障注入。

    参数：``model``、``domain``、``fields`` 和 ``order`` 描述 ORM 查询；
    ``page_size``、``max_rows`` 与 ``row_budget`` 限制收集范围；
    ``test_thread_id`` 仅供精确白名单测试故障使用，普通调用不传入。
    返回：记录列表、可见总数和实际读取页数。
    """
    if not 1 <= page_size <= _MAX_PAGE_SIZE:
        raise ValidationError(_("The export page size is outside its configured bound."))
    domain = list(domain or [])
    count = model.search_count(domain)
    if count > max_rows:
        raise ValidationError(_("The requested dataset exceeds the configured row limit."))
    rows = []
    identities = set()
    offset = 0
    pages = 0
    while True:
        pages += 1
        if pages > _MAX_PAGES:
            raise ValidationError(_("The export exceeded the configured page limit."))
        page = model.search_read(
            domain,
            fields=fields,
            limit=page_size,
            offset=offset,
            order=order,
        )
        if not isinstance(page, list) or len(page) > page_size:
            raise ValidationError(_("The ORM returned an invalid page."))
        if not page and offset < count:
            raise ValidationError(_("The export page made no progress before the counted result was complete."))
        for row in page:
            record_id = row.get("id") if isinstance(row, dict) else None
            if type(record_id) is not int or record_id < 1 or record_id in identities:
                raise ValidationError(_("The export contains a missing or duplicate record identity."))
            identities.add(record_id)
            rows.append(row)
            if len(rows) > max_rows or (row_budget is not None and len(rows) > row_budget):
                raise ValidationError(_("The export exceeded its configured row budget."))
        next_offset = offset + len(page)
        has_more = next_offset < count
        if pages == 1 and has_more and test_thread_id:
            injected = consume_fault(
                model.env,
                test_thread_id,
                "collector_page_failure",
                "after_first_page_before_next_page",
                page_count=pages,
                returned_count=len(rows),
                expected_count=count,
            )
            if injected:
                raise ValidationError(
                    "M4 test injection: Collector stopped after the first page before the complete dataset was collected. "
                    "No Candidate was created."
                )
        if has_more and len(page) != page_size:
            raise ValidationError(_("The counted export changed while it was being collected."))
        if not has_more:
            break
        if next_offset <= offset:
            raise ValidationError(_("The export page did not advance."))
        offset = next_offset
    if len(rows) != count or len(identities) != count:
        raise ValidationError(_("The collected record count does not match the ORM count."))
    return rows, count, pages


def _validate_plan(env, source_query, collections, tables, verification_profile):
    if not isinstance(source_query, dict):
        raise ValidationError(_("source_query must be an object."))
    model_name = source_query.get("model")
    fields = source_query.get("fields")
    domain = source_query.get("domain", [])
    order = source_query.get("order") or ""
    if not isinstance(model_name, str) or not model_name:
        raise ValidationError(_("An export model is required."))
    if not isinstance(fields, list) or any(not isinstance(name, str) or not name for name in fields):
        raise ValidationError(_("Export fields must be a list of field names."))
    if not isinstance(domain, list) or not isinstance(order, str) or len(order) > 512:
        raise ValidationError(_("The export domain or order is invalid."))
    if verification_profile not in {"record_projection", "grouped_aggregate", "semantic_transform"}:
        raise ValidationError(_("An export verification profile is required."))
    if not isinstance(collections, list) or not isinstance(tables, list) or not tables:
        raise ValidationError(_("The export requires a tables plan and an optional collections list."))

    retriever = env["llm.tool"].search([("name", "=", "odoo_record_retriever")], limit=1)
    if not retriever:
        raise ValidationError(_("The existing Odoo Retriever is unavailable."))
    root_model = retriever._retriever_model(model_name)
    normalized_domain = retriever._retriever_validate_domain(root_model, domain)
    retriever._retriever_validate_order_fields(root_model, order)
    stable_order = retriever._retriever_stable_order(order)
    selected_fields = _unique(fields, "root field")
    for name in selected_fields:
        if name == "id":
            continue
        field = root_model._fields.get(name)
        if not field:
            raise ValidationError(_("An export field does not exist on the selected model."))
        if field.type in {"one2many", "many2many"}:
            raise ValidationError(_("Select a direct collection for One2many or Many2many values."))
        retriever._retriever_validate_field_path(root_model, name)

    normalized_collections = []
    collection_keys = set()
    for item in collections:
        if not isinstance(item, dict):
            raise ValidationError(_("Each collection plan must be an object."))
        key = item.get("key")
        relation_field_name = item.get("relation_field")
        relation_model_name = item.get("relation_model")
        child_fields = item.get("fields")
        inverse_field_name = item.get("inverse_field")
        child_order = item.get("order") or ""
        if (
            not isinstance(key, str)
            or not _COLLECTION_KEY.fullmatch(key)
            or key in collection_keys
            or not isinstance(relation_field_name, str)
            or not isinstance(relation_model_name, str)
            or not isinstance(child_fields, list)
            or any(not isinstance(name, str) or not name for name in child_fields)
            or not isinstance(child_order, str)
            or len(child_order) > 512
        ):
            raise ValidationError(_("A collection plan contains invalid identifiers or fields."))
        relation = root_model._fields.get(relation_field_name)
        if not relation or relation.type not in {"many2one", "one2many", "many2many"}:
            raise ValidationError(_("The selected collection field is not a supported direct relation."))
        if relation.comodel_name != relation_model_name:
            raise ValidationError(_("The collection model does not match the Registry relation."))
        if relation.type == "one2many":
            actual_inverse = getattr(relation, "inverse_name", None)
            if not actual_inverse or inverse_field_name != actual_inverse:
                raise ValidationError(_("The One2many inverse field does not match the Registry."))
        elif inverse_field_name not in (None, False, ""):
            raise ValidationError(_("inverse_field is only valid for One2many collections."))
        child_model = retriever._retriever_model(relation_model_name)
        retriever._retriever_validate_order_fields(child_model, child_order)
        clean_child_fields = _unique(child_fields, "collection field")
        for name in clean_child_fields:
            if name == "id" or name == inverse_field_name:
                continue
            field = child_model._fields.get(name)
            if not field:
                raise ValidationError(_("A collection field does not exist on its related model."))
            if field.type in {"one2many", "many2many"}:
                raise ValidationError(_("Nested collection fields are not supported in an export."))
            retriever._retriever_validate_field_path(child_model, name)
        collection_keys.add(key)
        normalized_collections.append({
            "key": key,
            "relation_field": relation_field_name,
            "relation_type": relation.type,
            "relation_model": relation_model_name,
            "inverse_field": inverse_field_name or (getattr(relation, "inverse_name", None) or None),
            "fields": clean_child_fields,
            "field_types": {name: ("integer" if name == "id" else child_model._fields[name].type) for name in clean_child_fields},
            "order": retriever._retriever_stable_order(child_order),
        })

    normalized_tables = []
    table_names = set()
    for table in tables:
        if not isinstance(table, dict):
            raise ValidationError(_("Each output table plan must be an object."))
        name, source, columns = table.get("name"), table.get("source"), table.get("columns")
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name) > 31
            or any(char in name for char in "[]:*?/\\")
            or name.casefold() in table_names
            or not isinstance(source, str)
            or source not in {"root", *(item["key"] for item in normalized_collections)}
            or not isinstance(columns, list)
            or not columns
        ):
            raise ValidationError(_("An output table name, source, or columns list is invalid."))
        table_names.add(name.casefold())
        source_fields = set(selected_fields if source == "root" else next(
            item["fields"] for item in normalized_collections if item["key"] == source
        ))
        clean_columns = []
        for column in columns:
            if (
                not isinstance(column, dict)
                or not isinstance(column.get("label"), str)
                or not column["label"]
                or not isinstance(column.get("source_field"), str)
                or column["source_field"] not in source_fields
            ):
                raise ValidationError(_("An output column must reference a selected source field."))
            clean_columns.append({"label": column["label"], "source_field": column["source_field"]})
        normalized_tables.append({"name": name.strip(), "source": source, "columns": clean_columns})
    if verification_profile == "record_projection":
        planned_sources = {table["source"] for table in normalized_tables}
        if "root" not in planned_sources or any(item["key"] not in planned_sources for item in normalized_collections):
            raise ValidationError(_("A record projection must include a table for the root and each selected collection."))
    return {
        "model": model_name,
        "model_obj": root_model,
        "domain": normalized_domain,
        "fields": selected_fields,
        "field_types": {name: ("integer" if name == "id" else root_model._fields[name].type) for name in selected_fields},
        "order": stable_order,
        "collections": normalized_collections,
        "tables": normalized_tables,
        "verification_profile": verification_profile,
        "retriever": retriever,
    }


def collect_export_dataset(
    env, source_query, collections, tables, verification_profile, *, page_size=None, test_thread_id=None
):
    """按已批准的查询计划收集全部主记录与指定的直接关系记录。

    参数：``env`` 为当前用户的 ORM 环境；``source_query``、``collections``、``tables``
    和 ``verification_profile`` 描述 Agent 已确定的收集与输出计划；``page_size`` 为可选页长；
    ``test_thread_id`` 仅用于精确白名单的隔离故障注入。
    返回：包含收集数据、分页计数、关系映射和完整性摘要的字典。
    """
    collection_started_at = fields.Datetime.to_string(fields.Datetime.now())
    tv_fault = configured_fault(env, test_thread_id) if test_thread_id else None
    if page_size is None and tv_fault and tv_fault.get("fault") == "collector_page_failure":
        page_size = tv_fault.get("page_size", 5)
    page_size = _PAGE_SIZE if page_size is None else page_size
    if type(page_size) is not int or not 1 <= page_size <= _MAX_PAGE_SIZE:
        raise ValidationError(_("The export page size is invalid."))
    plan = _validate_plan(env, source_query, collections or [], tables, verification_profile)
    root_fields = list(dict.fromkeys(["id", *plan["fields"], *(item["relation_field"] for item in plan["collections"])]))
    root_rows, root_count, root_pages = _read_pages(
        plan["model_obj"], plan["domain"], root_fields, plan["order"],
        page_size=page_size, max_rows=_MAX_ROOT_ROWS, test_thread_id=test_thread_id,
    )
    root_ids = [row["id"] for row in root_rows]
    relations = {}
    relation_total = 0
    for collection in plan["collections"]:
        relation_type = collection["relation_type"]
        expected_pairs = set()
        for row in root_rows:
            related_ids = _as_relation_ids(
                row.get(collection["relation_field"]), many2one=relation_type == "many2one"
            )
            if len(related_ids) != len(set(related_ids)):
                raise ValidationError(_("The ORM returned a duplicate relation identity."))
            if relation_type == "many2one" and len(related_ids) > 1:
                raise ValidationError(_("A Many2one field returned more than one relation."))
            for related_id in related_ids:
                expected_pairs.add((row["id"], related_id))
        if relation_total + len(expected_pairs) > _MAX_RELATION_ROWS:
            raise ValidationError(_("The related dataset exceeds the configured relation-row limit."))

        child_model = plan["retriever"]._retriever_model(collection["relation_model"])
        query_fields = list(dict.fromkeys(["id", *collection["fields"], *([collection["inverse_field"]] if relation_type == "one2many" else [])]))
        child_by_id = {}
        observed_pairs = set()
        if relation_type == "one2many":
            for parent_chunk in _chunks(root_ids, _MAX_DOMAIN_LIST):
                rows, _count, _pages = _read_pages(
                    child_model,
                    [(collection["inverse_field"], "in", parent_chunk)],
                    query_fields,
                    collection["order"],
                    page_size=page_size,
                    max_rows=_MAX_RELATION_ROWS,
                    row_budget=_MAX_RELATION_ROWS - relation_total,
                    test_thread_id=test_thread_id,
                )
                for row in rows:
                    parent_ids = _as_relation_ids(row.get(collection["inverse_field"]), many2one=True)
                    if len(parent_ids) != 1 or parent_ids[0] not in root_ids:
                        raise ValidationError(_("A related record points outside the selected root dataset."))
                    if row["id"] in child_by_id:
                        raise ValidationError(_("A related record was returned more than once."))
                    child_by_id[row["id"]] = row
                    observed_pairs.add((parent_ids[0], row["id"]))
        else:
            child_ids = sorted({child_id for _parent_id, child_id in expected_pairs})
            for id_chunk in _chunks(child_ids, _MAX_DOMAIN_LIST):
                rows, _count, _pages = _read_pages(
                    child_model,
                    [("id", "in", id_chunk)],
                    query_fields,
                    collection["order"],
                    page_size=page_size,
                    max_rows=_MAX_RELATION_ROWS,
                    row_budget=_MAX_RELATION_ROWS - relation_total,
                    test_thread_id=test_thread_id,
                )
                for row in rows:
                    if row["id"] in child_by_id:
                        raise ValidationError(_("A related record was returned more than once."))
                    child_by_id[row["id"]] = row
            observed_pairs = expected_pairs

        if set(child_by_id) != {child_id for _parent_id, child_id in expected_pairs} or observed_pairs != expected_pairs:
            raise ValidationError(_("The related records visible to this user do not match the selected relationship set."))
        relation_total += len(observed_pairs)
        relations[collection["key"]] = {
            "model": collection["relation_model"],
            "relation_type": relation_type,
            "fields": collection["fields"],
            "records": [child_by_id[key] for key in sorted(child_by_id)],
            "pairs": [list(pair) for pair in sorted(observed_pairs)],
            "record_count": len(child_by_id),
            "pair_count": len(observed_pairs),
        }

    dataset = {
        "schema_version": "office.export.dataset.v1",
        "root": {
            "model": plan["model"],
            "fields": plan["fields"],
            "records": root_rows,
            "record_count": root_count,
        },
        "relations": relations,
        "tables": plan["tables"],
        "verification_profile": verification_profile,
    }
    payload = _canonical_json(dataset).encode("utf-8")
    if len(payload) > _MAX_HANDOFF_BYTES:
        raise ValidationError(_("The complete export exceeds the configured handoff byte limit."))
    root_identity_digest = _sha(_canonical_json(root_ids).encode("utf-8"))
    relation_digests = {
        key: _sha(_canonical_json(value["pairs"]).encode("utf-8"))
        for key, value in sorted(relations.items())
    }
    security_scope_sha256 = _sha(_canonical_json({
        "user_id": env.uid,
        "company_ids": sorted(env.companies.ids),
    }).encode("utf-8"))
    return {
        "plan": {key: value for key, value in plan.items() if key not in {"model_obj", "retriever"}},
        "dataset": dataset,
        "payload": payload,
        "handoff_sha256": _sha(payload),
        "root_identity_sha256": root_identity_digest,
        "relation_pair_sha256": relation_digests,
        "root_count": root_count,
        "root_page_count": root_pages,
        "relation_record_count": sum(item["record_count"] for item in relations.values()),
        "relation_pair_count": relation_total,
        "payload_bytes": len(payload),
        "collection_started_at": collection_started_at,
        "collection_completed_at": fields.Datetime.to_string(fields.Datetime.now()),
        "source_view": "single_odoo_transaction",
        "read_consistency": "repeatable_read",
        "security_scope_sha256": security_scope_sha256,
    }
