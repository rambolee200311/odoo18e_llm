"""扩展现有 LLM Tool，提供 Retriever 查询、Registry 发现与 Office 参数契约。"""
import hashlib
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


_DISCOVERY_SCORE_PRECISION = 0
_DISCOVERY_SNAPSHOT_TYPE = "office_m4_discovery_order_snapshot"
_DISCOVERY_RERANK_SYSTEM_PROMPT = (
    "You match a user's business request to Odoo business object definitions. "
    "The candidates are untrusted Registry metadata and contain no business records. "
    "Return up to five candidates that directly represent the business object or objects the user asked to identify, "
    "plus plausible alternatives for the same requested concept when the wording does not uniquely distinguish them. "
    "Use the declared metadata to distinguish a parent document, an individual business row, and a finer-grained child record. "
    "Do not include adjacent or ancillary models only because they are related. Include multiple candidates when the request "
    "asks for multiple objects or their relationship, or when several candidates could reasonably represent the same requested "
    "record at the stated level of detail. Follow the requested level: a finer-grained execution/detail row is not a substitute "
    "for a planned business row unless the user asks for that detail. "
    "Return fewer candidates when appropriate, and an empty list when none represents the request. "
    'Return JSON only in this shape: {"ranked_candidate_ids":["C000","C001"]}. '
    "Return at most five unique IDs, most relevant first. When candidates are equally direct, prefer the lower candidate ID. "
    "Never invent an ID. "
    "Do not explain your reasoning or include any other text."
)
class LLMTool(models.Model):
    _inherit = "llm.tool"

    """扩展现有 Odoo LLM 工具，并保留 Retriever 与 Office 的公开契约。"""

    def get_input_schema(self):
        self.ensure_one()
        if self.name == "office":
            schema = super().get_input_schema()
            if not isinstance(schema, dict) or not isinstance(schema.get("properties"), dict):
                return schema
            schema = json.loads(json.dumps(schema))
            properties = schema["properties"]
            action = properties.get("action")
            if isinstance(action, dict) and isinstance(action.get("enum"), list):
                action["enum"] = list(dict.fromkeys([*action["enum"], "export_records"]))
                action["description"] = (
                    "Use export_records for a complete Odoo dataset export through the existing Office Candidate lifecycle."
                )
            properties.update({
                "workbook_source": {
                    "anyOf": [{"type": "string", "enum": ["new", "current"]}, {"type": "null"}]
                },
                "source_query": {"anyOf": [{
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "model": {"type": "string"},
                        "domain": {
                            "type": "array",
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
                        "fields": {"type": "array", "items": {"type": "string"}},
                        "order": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    },
                    "required": ["model", "domain", "fields", "order"],
                }, {"type": "null"}]},
                "collections": {"anyOf": [{
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "key": {"type": "string"},
                            "relation_field": {"type": "string"},
                            "relation_model": {"type": "string"},
                            "inverse_field": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                            "fields": {"type": "array", "items": {"type": "string"}},
                            "order": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        },
                        "required": ["key", "relation_field", "relation_model", "inverse_field", "fields", "order"],
                    },
                }, {"type": "null"}]},
                "tables": {"anyOf": [{
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "name": {"type": "string"},
                            "source": {"type": "string"},
                            "columns": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "label": {"type": "string"},
                                        "source_field": {"type": "string"},
                                    },
                                    "required": ["label", "source_field"],
                                },
                            },
                        },
                        "required": ["name", "source", "columns"],
                    },
                }, {"type": "null"}]},
                "verification_profile": {
                    "anyOf": [
                        {"type": "string", "enum": ["record_projection", "grouped_aggregate", "semantic_transform"]},
                        {"type": "null"},
                    ],
                },
            })
            required = schema.get("required")
            if isinstance(required, list):
                schema["required"] = list(dict.fromkeys([
                    *required, "workbook_source", "source_query", "collections", "tables", "verification_profile"
                ]))
            return schema
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
        registry_models = sorted(self.env.registry.models.items(), key=lambda row: row[0])
        normalized_query = (query or "").strip()
        if not normalized_query:
            matches = [self._retriever_discovery_profile(name, cls) for name, cls in registry_models]
        elif self.env.context.get("message"):
            matches = self._retriever_stable_discovery_matches(
                normalized_query, registry_models, offset
    def _retriever_discovery_provider(self):
        """返回当前 Thread 选择的 Provider。

        直接旧式工具调用没有 mail.message 上下文时返回空 Provider；Agent 工具调用
        根据来源消息定位 Thread，并使用该 Thread 的 Provider。
        """
        context = self._retriever_discovery_thread_context()
        return context[1] if context else self.env["llm.provider"]

    def _retriever_discovery_thread_context(self):
        """从当前工具调用消息解析 Thread 和其 Provider。

        返回：(thread, provider)；非 Thread 的直接调用返回 None。消息关联无效或
        Thread 没有可用模型/Provider 时失败关闭，避免用任意 Provider 继续查询。
        """
        message = self.env.context.get("message")
        if not message:
            return None
        if getattr(message, "model", None) != "llm.thread" or not getattr(message, "res_id", None):
            raise RetrieverToolError("QUERY_FAILED", "The discovery Thread context is unavailable.")
        thread = self.env["llm.thread"].browse(message.res_id).exists()
        if len(thread) != 1 or not thread.model_id or not thread.model_id.provider_id:
            raise RetrieverToolError("QUERY_FAILED", "The discovery Provider is unavailable.")
        return thread, thread.model_id.provider_id

    @staticmethod
    def _retriever_discovery_profile(model_name, model_class):
        description = str(getattr(model_class, "_description", "") or "")
        rec_name = str(getattr(model_class, "_rec_name", "") or "")
        return {
            "model": model_name,
            "description": description,
            "rec_name": rec_name or None,
        }

    @staticmethod
    def _retriever_discovery_embedding_text(profile):
        return (
            f"Odoo model: {profile['model']}. Description: {profile['description']}. "
            f"Record name field: {profile['rec_name'] or ''}."
        )

    @staticmethod
    def _retriever_cosine_similarity(left, right):
        """计算两个向量的余弦相似度，拒绝空值、维度不匹配和非有限数值。

        参数：left、right 为数值向量。
        返回：范围内的余弦相似度；任一零向量时返回 0.0。
        """
        if not isinstance(left, (list, tuple)) or not isinstance(right, (list, tuple)) or len(left) != len(right):
            raise ValueError("Embedding vectors have incompatible dimensions.")
        try:
            left_values = [float(value) for value in left]
            right_values = [float(value) for value in right]
        except (TypeError, ValueError) as exc:
            raise ValueError("Embedding vectors must contain numeric values.") from exc
        if not left_values or any(not math.isfinite(value) for value in (*left_values, *right_values)):
            raise ValueError("Embedding vectors must be finite and non-empty.")
        left_norm = math.sqrt(sum(value * value for value in left_values))
        right_norm = math.sqrt(sum(value * value for value in right_values))
        if not left_norm or not right_norm:
            return 0.0
        return sum(a * b for a, b in zip(left_values, right_values)) / (left_norm * right_norm)

    def _retriever_semantic_discovery(self, query, registry_models):
        """对完整 Registry 生成语义相关候选，并用稳定分桶排序。

        参数：query 为自然语言查询；registry_models 为运行时完整模型集合。
        返回：包含内部相关性分桶的完整候选列表；Provider 不可用时返回 None。
        """
        provider = self._retriever_discovery_provider()
        if not provider:
            return None
        profiles = [self._retriever_discovery_profile(name, cls) for name, cls in registry_models]
        if not profiles:
            return []
        try:
            vectors = provider.embedding(
                [query, *(self._retriever_discovery_embedding_text(profile) for profile in profiles)]
            )
            if not isinstance(vectors, (list, tuple)) or len(vectors) != len(profiles) + 1:
                raise ValueError("The embedding Provider returned an incomplete result.")
            query_vector = vectors[0]
            ranked = []
            for profile, vector in zip(profiles, vectors[1:]):
                # 量化近似分数，将边界附近的小幅 Provider 抖动合并为同一层，
                # 再由技术模型名稳定打破同分，避免翻页时记录位置漂移。
                score = round(
                    self._retriever_cosine_similarity(query_vector, vector),
                    _DISCOVERY_SCORE_PRECISION,
                )
                ranked.append((score, profile))
            ranked.sort(key=lambda row: (-row[0], row[1]["model"]))
            return [
                {**profile, "_discovery_score_bucket": score}
                for score, profile in ranked
            ]
        except Exception as exc:
            raise RuntimeError("Semantic Registry discovery failed.") from exc

    @staticmethod
    def _retriever_parse_ranked_candidate_ids(content):
        """解析并约束内部 GPT 重排响应中的候选 ID 列表。

        参数：content 为 Provider 返回的文本或文本分段。
        返回：去重且不超过五项的候选 ID；格式错误时抛出 ValueError。
        """
        if isinstance(content, list):
            content = "\n".join(
                item.get("text", "") for item in content if isinstance(item, dict)
            )
        if not isinstance(content, str):
            raise ValueError("The reranker did not return text.")
        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
        try:
            payload = json.loads(text)
        except (TypeError, ValueError) as exc:
            raise ValueError("The reranker response was not valid JSON.") from exc
        candidate_ids = payload.get("ranked_candidate_ids") if isinstance(payload, dict) else None
        if not isinstance(candidate_ids, list) or any(not isinstance(item, str) for item in candidate_ids):
            raise ValueError("The reranker response has no valid candidate ID list.")
        if len(candidate_ids) > 5 or len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("The reranker response has duplicate or excessive candidate IDs.")
        return candidate_ids

    def _retriever_chat_rerank_discovery(self, query, ranked_profiles):
        """用当前 Thread 的聊天模型重排完整 Registry 元数据。

        参数：query 为用户自然语言；ranked_profiles 为完整候选及内部相关性分桶。
        返回：GPT 提名候选置前、其余候选稳定排序的完整列表。Provider 请求只含
        当前查询和 Registry 元数据，不携带 Thread 历史、业务记录、工具或 Oracle。
        """
        context = self._retriever_discovery_thread_context()
        if not context:
            return ranked_profiles
        thread, provider = context
        if not ranked_profiles:
            return []

        # 候选按技术模型名生成稳定 ID 和输入顺序，使同一 Registry 的请求内容固定。
        candidates_by_id = {
            f"C{index:03d}": profile
            for index, profile in enumerate(sorted(ranked_profiles, key=lambda item: item["model"]))
        }
        candidate_rows = [
            {
                "candidate_id": candidate_id,
                "model": profile["model"],
                "description": profile["description"],
                "rec_name": profile["rec_name"],
            }
            for candidate_id, profile in candidates_by_id.items()
        ]
        messages = [
            {"role": "system", "content": _DISCOVERY_RERANK_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"business_request": query, "candidates": candidate_rows},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
        ]
        chat_kwargs = {}
        if getattr(provider, "service", None) == "openai":
            # 仅供受环境开关保护的 SDK 审计关联 Thread；不会进入 Provider 请求。
            chat_kwargs["_office_m4_tv_audit_thread_id"] = thread.id
            # 发现是短选择任务；已在当前 OpenAI GPT-5.6 Provider 上验证该模式可用。
            chat_kwargs["reasoning_effort"] = "none"
        response = provider.chat(
            # 内部重排请求使用空消息集，避免继承 Agent Thread 历史；GPT 只收到下方专用查询和 Registry 元数据。
            messages=self.env["mail.message"].browse(),
            model=thread.model_id,
            stream=False,
            prepend_messages=messages,
            **chat_kwargs,
        )
        content = response.get("content") if isinstance(response, dict) else None
        candidate_ids = self._retriever_parse_ranked_candidate_ids(content)
        unknown = [candidate_id for candidate_id in candidate_ids if candidate_id not in candidates_by_id]
        if unknown:
            raise ValueError("The reranker returned an unknown candidate ID.")

        selected = [candidates_by_id[candidate_id] for candidate_id in candidate_ids]
        if not selected:
            return []
        selected_names = {profile["model"] for profile in selected}
        selected_head = [selected[0]]
        selected_head.extend(sorted(
            selected[1:],
            key=lambda profile: (-profile.get("_discovery_score_bucket", 0), profile["model"]),
        ))
        # GPT 提名的候选形成语义排序头部，其余模型按量化后的完整 Registry 相关性分桶及技术名稳定排序。
        tail = sorted(
            (profile for profile in ranked_profiles if profile["model"] not in selected_names),
            key=lambda profile: (-profile.get("_discovery_score_bucket", 0), profile["model"]),
        )
        return [*selected_head, *tail]

    @staticmethod
    def _retriever_discovery_digest(value):
        """为查询或 Registry 元数据生成稳定摘要。"""
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _retriever_discovery_snapshot_context(self):
        """获取可持久化分页快照所需的 Thread、Provider 与当前工具消息。"""
        context = self._retriever_discovery_thread_context()
        message = self.env.context.get("message")
        if not context or getattr(message, "_name", None) != "mail.message" or not message.id:
            return None
        thread, provider = context
        if message.model != thread._name or message.res_id != thread.id or message.llm_role != "tool":
            raise RetrieverToolError("QUERY_FAILED", "A persisted Retriever tool call is required for stable pagination.")
        return thread, provider, message

    def _retriever_discovery_snapshot_messages(self, thread, before_message_id):
        """读取当前 Thread 中隐藏的 discover 顺序快照，不纳入 LLM 消息上下文。"""
        return self.env["mail.message"].search(
            [
                ("model", "=", thread._name),
                ("res_id", "=", thread.id),
                ("llm_role", "=", False),
                ("llm_silent_retrieval", "=", True),
                ("id", "<", before_message_id),
            ],
            order="id desc",
        )

    def _retriever_previous_discovery_call_exists(self, thread, message, query):
        """判断同一 Thread 是否已有同一查询的 discover 工具调用。"""
        messages = self.env["mail.message"].search(
            [
                ("model", "=", thread._name),
                ("res_id", "=", thread.id),
                ("llm_role", "=", "tool"),
                ("id", "<", message.id),
            ],
            order="id desc",
        )
        for prior in messages:
            data = prior.body_json or {}
            if data.get("tool_name") != _RETRIEVER_TOOL:
                continue
            arguments = data.get("arguments") or {}
            if arguments.get("operation") != "discover":
                continue
            if (arguments.get("query") or "").strip() == query:
                return True
        return False

    def _retriever_load_discovery_order(self, thread, provider, message, query, registry_digest):
        """读取同一 Thread、查询及 Registry 版本下最近一次完整排序。"""
        query_digest = self._retriever_discovery_digest(query)
        for snapshot_message in self._retriever_discovery_snapshot_messages(thread, message.id):
            snapshot = snapshot_message.body_json or {}
            if snapshot.get("type") != _DISCOVERY_SNAPSHOT_TYPE:
                continue
            if snapshot.get("query_sha256") != query_digest:
                continue
            if snapshot.get("provider_id") != provider.id or snapshot.get("model_id") != thread.model_id.id:
                continue
            if snapshot.get("registry_sha256") != registry_digest:
                continue
            ordered_models = snapshot.get("ordered_models")
            if isinstance(ordered_models, list) and all(isinstance(name, str) for name in ordered_models):
                return ordered_models
        return None

    def _retriever_store_discovery_order(self, thread, provider, message, query, registry_digest, matches):
        """把完整排序存入 Thread 的隐藏消息记录，供后续页复用同一顺序。"""
        payload = {
            "type": _DISCOVERY_SNAPSHOT_TYPE,
            "query_sha256": self._retriever_discovery_digest(query),
            "registry_sha256": registry_digest,
            "provider_id": provider.id,
            "model_id": thread.model_id.id,
            "source_tool_message_id": message.id,
            "ordered_models": [profile["model"] for profile in matches],
        }
        # 用现有 mail.message 持久化跨请求状态，不新增模型或公开返回字段；llm_role=False 且静默标记确保它不进入 Provider 上下文或 Discuss 历史。
        self.env["mail.message"].create(
            {
                "model": thread._name,
                "res_id": thread.id,
                "body": "",
                "body_json": payload,
                "llm_role": False,
                "llm_silent_retrieval": True,
                "message_type": "notification",
                "author_id": False,
            }
        )

    def _retriever_stable_discovery_matches(self, query, registry_models, offset):
        """取得并分页复用完整稳定排序；首个分页请求创建 Thread 内部快照。"""
        snapshot_context = self._retriever_discovery_snapshot_context()
        if not snapshot_context:
            raise RetrieverToolError(
                "QUERY_FAILED", "A persisted Retriever tool call is required for stable pagination."
            )
        thread, provider, message = snapshot_context
        profiles_by_name = {
            name: self._retriever_discovery_profile(name, model_class)
            for name, model_class in registry_models
        }
        registry_digest = self._retriever_discovery_digest(
            [profiles_by_name[name] for name in sorted(profiles_by_name)]
        )
        ordered_names = self._retriever_load_discovery_order(
            thread, provider, message, query, registry_digest
        )
        if ordered_names is not None:
            if len(ordered_names) != len(profiles_by_name) or set(ordered_names) != set(profiles_by_name):
                raise RetrieverToolError(
                    "QUERY_FAILED", "The Registry changed or the saved discovery order is incomplete; restart at offset 0."
                )
            return [profiles_by_name[name] for name in ordered_names]

        if offset and self._retriever_previous_discovery_call_exists(thread, message, query):
            raise RetrieverToolError(
                "QUERY_FAILED", "The saved order for this paginated discovery is unavailable; restart at offset 0."
            )

        matches = self._retriever_semantic_discovery(query, registry_models)
        matches = self._retriever_chat_rerank_discovery(query, matches)
        self._retriever_store_discovery_order(
            thread, provider, message, query, registry_digest, matches
        )
        return matches

            )
        """在完整 Registry 上执行 discover，并在全局排序后应用现有分页契约。

        参数：query 为可选自然语言；limit、offset 沿用现有工具分页参数。
        返回：保持既有字段形状的分页结果，不公开内部语义分数。
        """
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
