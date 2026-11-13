import json
import logging
import uuid
from typing import Any

from odoo import models
from odoo.exceptions import AccessError, ValidationError
from odoo.osv import expression
from pydantic import ValidationError as PydanticValidationError

from .retriever_errors import RetrieverAccessError, RetrieverToolError

_logger = logging.getLogger(__name__)
_RETRIEVER_TOOL = "odoo_record_retriever"
_OPERATIONS = {"discover", "describe", "search"}
_LOGIC_TOKENS = {"|", "&", "!"}
_MAX_LIMIT = 500
_MAX_DOMAIN_LIST = 1000


class LLMTool(models.Model):
    _inherit = "llm.tool"

    def get_input_schema(self):
        self.ensure_one()
        if self.name != _RETRIEVER_TOOL:
            return super().get_input_schema()

        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "operation": {
                    "anyOf": [
                        {"type": "string", "enum": ["discover", "describe", "search"]},
                        {"type": "null"},
                    ],
                    "description": "Omit to use the legacy search contract.",
                },
                "model": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "query": {
                    "anyOf": [
                        {"type": "string", "maxLength": 256},
                        {"type": "null"},
                    ]
                },
                "domain": {
                    "anyOf": [
                        {
                            "type": "array",
                            "description": "Standard Odoo domain. Use JSON scalar arrays for in/not in values.",
                            "items": {
                                "oneOf": [
                                    {"type": "string", "enum": ["|", "&", "!"]},
                                    {
                                        "type": "array",
                                        "minItems": 3,
                                        "maxItems": 3,
                                        "prefixItems": [
                                            {"type": "string"},
                                            {"type": "string"},
                                            {
                                                "oneOf": [
                                                    {"type": ["string", "integer", "number", "boolean", "null"]},
                                                    {
                                                        "type": "array",
                                                        "maxItems": _MAX_DOMAIN_LIST,
                                                        "items": {"type": ["string", "integer", "number", "boolean", "null"]},
                                                    },
                                                ]
                                            },
                                        ],
                                    },
                                ]
                            },
                        },
                        {"type": "null"},
                    ]
                },
                "fields": {
                    "anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}]
                },
                "limit": {"anyOf": [{"type": "integer", "minimum": 1, "maximum": _MAX_LIMIT}, {"type": "null"}]},
                "offset": {"type": "integer", "minimum": 0},
                "order": {"anyOf": [{"type": "string", "maxLength": 512}, {"type": "null"}]},
                "include_pagination": {"anyOf": [{"type": "boolean"}, {"type": "null"}]},
            },
        }

    def execute(self, parameters):
        self.ensure_one()
        if self.name != _RETRIEVER_TOOL:
            return super().execute(parameters)
        try:
            return super().execute(parameters)
        except (RetrieverToolError, RetrieverAccessError):
            raise
        except AccessError as exc:
            raise RetrieverAccessError() from exc
        except (PydanticValidationError, TypeError, ValueError, ValidationError) as exc:
            raise RetrieverToolError("INVALID_QUERY", "The Retriever arguments are invalid.") from exc
        except Exception as exc:
            diagnostic_id = uuid.uuid4().hex
            _logger.exception("Retriever execution failed; diagnostic_id=%s", diagnostic_id)
            raise RetrieverToolError(
                "QUERY_FAILED", "The record query could not be completed.", diagnostic_id=diagnostic_id
            ) from exc

    def odoo_record_retriever_execute(
        self,
        model: str | None = None,
        domain: list[Any] | None = None,
        fields: list[str] | None = None,
        limit: int | None = None,
        offset: int = 0,
        order: str | None = "",
        include_pagination: bool | None = None,
        operation: str | None = None,
        query: str | None = None,
    ) -> Any:
        """Extend the existing Retriever; absent operation preserves M2/upstream behavior."""
        if operation is None:
            if not isinstance(model, str) or not model:
                raise RetrieverToolError("INVALID_QUERY", "A model is required for a legacy search.")
            model_obj = self._retriever_model(model)
            selected_fields = fields or []
            if not isinstance(selected_fields, list) or any(not isinstance(name, str) for name in selected_fields):
                raise RetrieverToolError("INVALID_QUERY", "fields must be a list of field names.")
            for name in selected_fields:
                self._retriever_validate_field_path(model_obj, name)
            validated_domain = self._retriever_validate_domain(model_obj, domain)
            try:
                return super().odoo_record_retriever_execute(
                    model,
                    domain=validated_domain,
                    fields=selected_fields,
                    limit=100 if limit is None else limit,
                    offset=offset,
                    order=order or "",
                    include_pagination=False if include_pagination is None else include_pagination,
                )
            except AccessError as exc:
                raise RetrieverAccessError() from exc
            except (ValidationError, ValueError, TypeError) as exc:
                raise RetrieverToolError("INVALID_QUERY", "The requested query is invalid.") from exc
            except Exception as exc:
                diagnostic_id = uuid.uuid4().hex
                _logger.exception("Legacy Retriever search failed; diagnostic_id=%s", diagnostic_id)
                raise RetrieverToolError(
                    "QUERY_FAILED", "The record query could not be completed.", diagnostic_id=diagnostic_id
                ) from exc

        if operation not in _OPERATIONS:
            raise RetrieverToolError("INVALID_QUERY", "The requested Retriever operation is not supported.")
        if type(offset) is not int or offset < 0:
            raise RetrieverToolError("INVALID_QUERY", "offset must be a non-negative integer.")

        try:
            if operation == "discover":
                return self._retriever_discover(query=query, limit=limit, offset=offset)
            if operation == "describe":
                return self._retriever_describe(model=model, fields=fields, limit=limit, offset=offset)
            return self._retriever_search(
                model=model,
                domain=domain,
                fields=fields,
                limit=limit,
                offset=offset,
                order=order,
                include_pagination=include_pagination,
            )
        except (RetrieverToolError, RetrieverAccessError):
            raise
        except AccessError as exc:
            raise RetrieverAccessError() from exc
        except (ValidationError, ValueError, TypeError, KeyError) as exc:
            raise RetrieverToolError("INVALID_QUERY", "The requested query is invalid.") from exc
        except Exception as exc:
            diagnostic_id = uuid.uuid4().hex
            _logger.exception("Retriever operation failed; operation=%s diagnostic_id=%s", operation, diagnostic_id)
            raise RetrieverToolError(
                "QUERY_FAILED", "The Retriever operation could not be completed.", diagnostic_id=diagnostic_id
            ) from exc

    def _retriever_discover(self, query=None, limit=None, offset=0):
        if query is not None and (not isinstance(query, str) or len(query) > 256):
            raise RetrieverToolError("INVALID_QUERY", "query must be a string of at most 256 characters.")
        page_limit = self._retriever_limit(limit, default=100)
        needle = (query or "").casefold()
        matches = []
        for model_name, model_class in self.env.registry.models.items():
            description = getattr(model_class, "_description", "") or ""
            if needle not in model_name.casefold() and needle not in str(description).casefold():
                continue
            matches.append(
                {
                    "model": model_name,
                    "description": str(description),
                    "rec_name": getattr(model_class, "_rec_name", None),
                }
            )
        matches.sort(key=lambda item: item["model"])
        page = matches[offset : offset + page_limit]
        return self._retriever_page("discover", page, len(matches), offset, page_limit, "models") | {"query": query or ""}

    def _retriever_describe(self, model=None, fields=None, limit=None, offset=0):
        model_obj = self._retriever_model(model)
        if fields is not None and (not isinstance(fields, list) or any(not isinstance(name, str) for name in fields)):
            raise RetrieverToolError("INVALID_QUERY", "fields must be a list of field names.")
        all_names = sorted(model_obj._fields)
        if fields:
            unknown = [name for name in fields if name not in model_obj._fields]
            if unknown:
                raise RetrieverToolError("FIELD_NOT_FOUND", "One or more requested fields do not exist.")
            selected_names = list(dict.fromkeys(fields))
        else:
            selected_names = all_names
        page_limit = self._retriever_limit(limit, default=200)
        field_rows = [self._retriever_field_schema(model_obj._fields[name], name) for name in selected_names]
        page = field_rows[offset : offset + page_limit]
        model_class = type(model_obj)
        result = self._retriever_page("describe", page, len(field_rows), offset, page_limit, "fields")
        result.update(
            {
                "model": model_obj._name,
                "description": getattr(model_class, "_description", "") or "",
                "rec_name": getattr(model_class, "_rec_name", None),
            }
        )
        return result

    def _retriever_search(self, model=None, domain=None, fields=None, limit=None, offset=0, order="", include_pagination=None):
        model_obj = self._retriever_model(model)
        page_limit = self._retriever_limit(limit, default=100)
        if order is None:
            order = ""
        if not isinstance(order, str) or len(order) > 512:
            raise RetrieverToolError("INVALID_QUERY", "order must be a string of at most 512 characters.")
        if include_pagination is not None and type(include_pagination) is not bool:
            raise RetrieverToolError("INVALID_QUERY", "include_pagination must be boolean.")
        if fields is None:
            fields = []
        if not isinstance(fields, list) or any(not isinstance(name, str) for name in fields):
            raise RetrieverToolError("INVALID_QUERY", "fields must be a list of field names.")
        for name in fields:
            self._retriever_validate_field_path(model_obj, name)

        domain = self._retriever_validate_domain(model_obj, domain)
        self._retriever_validate_order_fields(model_obj, order)
        stable_order = self._retriever_stable_order(order)
        search_kwargs = {
            "domain": domain,
            "limit": page_limit,
            "offset": offset,
            "order": stable_order,
        }
        if fields:
            records = model_obj.search_read(fields=fields, **search_kwargs)
        else:
            found = model_obj.search(**search_kwargs)
            records = found.read()
        records = json.loads(json.dumps(records, default=str))
        if include_pagination is False:
            return records
        count = model_obj.search_count(domain)
        return {
            "status": "success",
            "operation": "search",
            "records": records,
            "count": count,
            "offset": offset,
            "limit": page_limit,
            "returned_count": len(records),
            "has_more": offset + len(records) < count,
            "next_offset": offset + len(records) if offset + len(records) < count else None,
        }

    def _retriever_model(self, model_name):
        if not isinstance(model_name, str) or not model_name:
            raise RetrieverToolError("INVALID_QUERY", "A model is required for this operation.")
        model_class = self.env.registry.models.get(model_name)
        if model_class is None:
            raise RetrieverToolError("MODEL_NOT_FOUND", "The requested model is not present in the Odoo Registry.")
        return self.env[model_name]

    @staticmethod
    def _retriever_limit(limit, default):
        if limit is None:
            return default
        if type(limit) is not int or not 1 <= limit <= _MAX_LIMIT:
            raise RetrieverToolError("INVALID_QUERY", "limit must be an integer from 1 to 500.")
        return limit

    @staticmethod
    def _retriever_page(operation, rows, count, offset, limit, key):
        returned_count = len(rows)
        has_more = offset + returned_count < count
        return {
            "status": "success",
            "operation": operation,
            key: rows,
            "count": count,
            "offset": offset,
            "limit": limit,
            "returned_count": returned_count,
            "has_more": has_more,
            "next_offset": offset + returned_count if has_more else None,
        }

    @staticmethod
    def _retriever_field_schema(field, name):
        result = {"name": name, "label": str(field.string or name), "type": field.type}
        if field.type in {"many2one", "one2many", "many2many"}:
            result["relation"] = field.comodel_name
        if field.type == "one2many":
            result["inverse_field"] = getattr(field, "inverse_name", None)
        if field.type == "many2many":
            for attr, output in (("relation", "relation_table"), ("column1", "column1"), ("column2", "column2")):
                value = getattr(field, attr, None)
                if value:
                    result[output] = value
        if field.type == "selection":
            selection = field.selection
            if isinstance(selection, (list, tuple)):
                result["selection"] = [
                    {"value": key if key is None or isinstance(key, (str, int, float, bool)) else str(key), "label": str(label)}
                    for key, label in selection
                ]
                result["selection_dynamic"] = False
            else:
                result["selection_dynamic"] = True
        return result

    @staticmethod
    def _retriever_stable_order(order):
        stable = order.strip()
        if not stable:
            return "id asc"
        has_id = any(
            part.strip().split()[0] == "id"
            for part in stable.split(",")
            if part.strip()
        )
        return stable if has_id else f"{stable}, id asc"

    @classmethod
    def _retriever_validate_order_fields(cls, model, order):
        if not order:
            return
        if not isinstance(order, str):
            raise RetrieverToolError("INVALID_QUERY", "order must be a string.")
        for part in order.split(","):
            tokens = part.strip().split()
            if not tokens:
                raise RetrieverToolError("INVALID_QUERY", "order contains an empty field.")
            cls._retriever_validate_field_path(model, tokens[0])

    @classmethod
    def _retriever_validate_domain(cls, model, domain):
        if domain is None:
            return []
        if not isinstance(domain, list):
            raise RetrieverToolError("INVALID_QUERY", "domain must be an Odoo domain list.")
        for item in domain:
            if isinstance(item, str) and item in _LOGIC_TOKENS:
                continue
            if not isinstance(item, (list, tuple)) or len(item) != 3:
                raise RetrieverToolError("INVALID_QUERY", "domain must contain valid Odoo domain terms.")
            field_name, operator, value = item
            if not isinstance(field_name, str) or not field_name or not isinstance(operator, str):
                raise RetrieverToolError("INVALID_QUERY", "domain fields and operators must be strings.")
            cls._retriever_validate_field_path(model, field_name)
            if operator in {"in", "not in"} and not isinstance(value, list):
                raise RetrieverToolError("INVALID_QUERY", "The value for in/not in must be a JSON array.")
            if isinstance(value, list):
                if len(value) > _MAX_DOMAIN_LIST:
                    raise RetrieverToolError("INVALID_QUERY", "A domain value array exceeds 1000 items.")
                if any(not isinstance(entry, (str, int, float, bool)) and entry is not None for entry in value):
                    raise RetrieverToolError("INVALID_QUERY", "Domain arrays may contain JSON scalar values only.")
            elif not isinstance(value, (str, int, float, bool)) and value is not None:
                raise RetrieverToolError("INVALID_QUERY", "Domain values must be JSON scalar values or arrays.")
        try:
            expression.normalize_domain(domain)
        except Exception as exc:
            raise RetrieverToolError("INVALID_QUERY", "The Odoo domain syntax is invalid.") from exc
        return domain

    @staticmethod
    def _retriever_validate_field_path(model, path):
        if not isinstance(path, str) or not path:
            raise RetrieverToolError("FIELD_NOT_FOUND", "A requested field name is empty or invalid.")
        current = model
        segments = path.split(".")
        for index, segment in enumerate(segments):
            field = current._fields.get(segment)
            if field is None:
                raise RetrieverToolError("FIELD_NOT_FOUND", "One or more requested fields do not exist.")
            if index < len(segments) - 1:
                if field.type not in {"many2one", "one2many", "many2many"} or field.comodel_name not in current.env.registry.models:
                    raise RetrieverToolError("FIELD_NOT_FOUND", "The requested field path is not a valid relation.")
                current = current.env[field.comodel_name]
