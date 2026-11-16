"""Read-only, objective verification for record-projection XLSX outputs."""

from datetime import date, datetime, time
from io import BytesIO

from odoo.exceptions import ValidationError


def _cell_value(value, field_type):
    if isinstance(value, (list, tuple)) and len(value) == 2 and isinstance(value[0], int):
        return value[1]
    if value is False and field_type in {"many2one", "date", "datetime"}:
        return None
    if isinstance(value, (list, tuple, dict)):
        return value
    return value


def _comparable(value):
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    return value


def _matches(actual, expected, field_type=None):
    # XLSX serial dates are read by openpyxl as midnight datetimes. Compare
    # them as calendar dates when the selected Odoo field is a Date.
    if field_type == "date":
        if isinstance(actual, datetime):
            actual = actual.date()
        if isinstance(expected, datetime):
            expected = expected.date()
    actual = _comparable(actual)
    expected = _comparable(expected)
    if expected is None:
        return actual in (None, "")
    if isinstance(expected, (list, tuple, dict)):
        return actual == expected
    if isinstance(expected, bool):
        return type(actual) is bool and actual is expected
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return type(actual) in (int, float) and actual == expected
    if isinstance(expected, str):
        return actual == expected
    return actual == expected


def _table_rows(collected, table):
    dataset = collected["dataset"]
    source = table["source"]
    if source == "root":
        return [
            (False, row["id"], row, dataset["root"]["fields"], collected["plan"]["field_types"])
            for row in dataset["root"]["records"]
        ]
    relation = dataset["relations"][source]
    collection_plan = next(item for item in collected["plan"]["collections"] if item["key"] == source)
    records = {row["id"]: row for row in relation["records"]}
    return [
        (parent_id, child_id, records[child_id], relation["fields"], collection_plan["field_types"])
        for parent_id, child_id in relation["pairs"]
    ]


def verify_export_workbook(content, filename, collected):
    """Check file readability and, for projections, exact planned identities and cells."""
    if not isinstance(content, bytes) or not content:
        raise ValidationError("The Hosted CI output is empty.")
    if not isinstance(filename, str) or not filename.lower().endswith(".xlsx"):
        raise ValidationError("The Hosted CI output is not an XLSX file.")
    try:
        from openpyxl import load_workbook
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=False)
    except Exception as exc:
        raise ValidationError("The Hosted CI output cannot be read as an XLSX workbook.") from exc
    try:
        if not workbook.sheetnames:
            raise ValidationError("The Hosted CI output has no worksheets.")
        profile = collected["plan"]["verification_profile"]
        if profile != "record_projection":
            return {"identity_verified": None, "projected_rows": None, "worksheet_count": len(workbook.sheetnames)}

        checked_rows = 0
        checked_tables = []
        for table in collected["plan"]["tables"]:
            worksheet = workbook[table["name"]] if table["name"] in workbook.sheetnames else None
            if worksheet is None:
                raise ValidationError("A planned export worksheet is missing.")
            iterator = worksheet.iter_rows(values_only=False)
            header_cells = next(iterator, None)
            if header_cells is None:
                raise ValidationError("A planned export worksheet has no header row.")
            headers = [cell.value for cell in header_cells]
            while headers and headers[-1] in (None, ""):
                headers.pop()
            named_headers = [header for header in headers if header not in (None, "")]
            if len(named_headers) != len(set(named_headers)):
                raise ValidationError("A planned export worksheet contains duplicate column headers.")

            visible_headers = [column["label"] for column in table["columns"]]
            visible_indexes = []
            for label in visible_headers:
                matches = [index for index, header in enumerate(headers) if header == label]
                if len(matches) != 1:
                    raise ValidationError("A planned export worksheet's visible headers do not match its plan.")
                visible_indexes.append(matches[0])
            if visible_indexes != sorted(visible_indexes):
                raise ValidationError("A planned export worksheet's visible columns are out of order.")

            record_id_indexes = [index for index, header in enumerate(headers) if header == "__office_record_id"]
            if len(record_id_indexes) != 1:
                raise ValidationError("A planned export worksheet must contain one record identity column.")
            record_id_index = record_id_indexes[0]
            parent_id_indexes = [index for index, header in enumerate(headers) if header == "__office_parent_id"]
            if table["source"] == "root":
                if len(parent_id_indexes) > 1:
                    raise ValidationError("A root worksheet contains duplicate parent identity columns.")
                parent_id_index = parent_id_indexes[0] if parent_id_indexes else None
            else:
                if len(parent_id_indexes) != 1:
                    raise ValidationError("A relation worksheet must contain one parent identity column.")
                parent_id_index = parent_id_indexes[0]

            recognized_indexes = set(visible_indexes) | {record_id_index}
            if parent_id_index is not None:
                recognized_indexes.add(parent_id_index)
            helper_indexes = set(range(len(headers))) - recognized_indexes
            actual_data = []
            for row in iterator:
                values = [cell.value for cell in row]
                if not any(value is not None for value in values):
                    continue
                if any(cell.data_type == "f" for cell in row):
                    raise ValidationError("A record-projection output contains formulas instead of source values.")
                values.extend([None] * max(0, len(headers) - len(values)))
                if any(values[index] not in (None, "") for index in helper_indexes):
                    raise ValidationError("A planned export worksheet contains values in unplanned helper columns.")
                if parent_id_index is not None and table["source"] == "root" and values[parent_id_index] not in (None, ""):
                    raise ValidationError("A root worksheet's optional parent identity column must be blank.")
                if any(value not in (None, "") for value in values[len(headers) :]):
                    raise ValidationError("A planned export worksheet contains values outside its header row.")
                actual_data.append(values)
            expected_data = _table_rows(collected, table)
            if len(actual_data) != len(expected_data):
                raise ValidationError("A planned export worksheet has a missing or extra data row.")
            for actual_row, expected_row in zip(actual_data, expected_data):
                parent_id, record_id, record, source_fields, field_types = expected_row
                for index, column in enumerate(table["columns"]):
                    source_field = column["source_field"]
                    expected_value = _cell_value(record.get(source_field), field_types.get(source_field))
                    if not _matches(
                        actual_row[visible_indexes[index]],
                        expected_value,
                        field_types.get(source_field),
                    ):
                        raise ValidationError("A planned export cell does not match its selected source value.")
                if actual_row[record_id_index] != record_id:
                    raise ValidationError("A planned export worksheet has a missing, duplicate, or misassociated identity.")
                if table["source"] != "root" and actual_row[parent_id_index] != parent_id:
                    raise ValidationError("A planned export worksheet has a missing, duplicate, or misassociated identity.")
            checked_rows += len(expected_data)
            checked_tables.append(table["name"])
        return {
            "identity_verified": True,
            "projected_rows": checked_rows,
            "verified_tables": checked_tables,
            "worksheet_count": len(workbook.sheetnames),
        }
    finally:
        workbook.close()
