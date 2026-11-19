<!--
模板来源：office_engine/docs/skill/odoo-project-workflow/references/templates/Coding/FR模板.md
模板版本/状态：v1.0.0 Frozen；同步检查 PASS（2026-11-19）
本文件状态：v0.3 关闭版。§1–15 保留最初 v0.2 评估与失败历史；§16 是负责人批准后的当前权威状态。
-->

# FR — CC-M4-01 通用业务对象发现

## 1. Closure Metadata

| 字段 | 值 |
|---|---|
| Intent ID | CC-M4-01 |
| FR ID / Version | FR-CC-M4-01.md / v0.3 final retest assessment |
| CC Version | v0.2 FROZEN |
| IHR Reference | `IHR-CC-M4-01.md` |
| ATR Reference | `ATR-CC-M4-01.md` |
| HVR | N/A — CC §11.2 不要求 UI HVR |
| Module | `office_engine_m3` |
| Current Code Baseline | HEAD `8f7ebd259cda414baae46fa91b1d55948ba481a0` + 工作树文件哈希见 evidence manifest |
| Assessment Date | 2026-11-19（Asia/Shanghai） |

## 2. Final Coding Contract Baseline

| 来源 | 版本 | 相关性 |
|---|---|---|
| CC-M4-01 | v0.2 Frozen | 唯一验收义务来源 |
| TDD | v0.2 Frozen with open items | CC 所引用的技术基线 |
| Implementation Plan | v0.1 Frozen | CC 阶段映射 |

## 3. Executive Closure Summary

| 字段 | 值 |
|---|---|
| Closure Status | **CLOSED — 项目负责人批准（2026-11-19）** |
| CC-CHANGE | 最终 Top-5 40/40；Agent 选模、歧义及负向样本达到冻结门槛 |
| CC-PRESERVE | 公开 Schema、legacy search、权限边界及完整分页稳定性均有通过证据 |
| Applicable Guardrails | 使用 757 个 Registry 模型元数据及合成请求；未读取业务记录或执行 Office 写操作；真实 Provider 证据已取得 |
| Automated Verification | **PASS — 8 项适用义务通过；CC-TEST-007 未采用 Alias，条件性不适用** |
| Human Verification | N/A（按 CC） |
| Unauthorized Deviation | None observed |
| Open Blocking Issues | None；P04 首次 Provider 超时已原样保留，独立重跑通过并补齐唯一用例 |
| Evidence Baseline Consistency | Yes — ATR-RUN-005/007 对应最终原始 Provider、Agent、双遍历、ORM 清理和回归证据 |

> **历史状态说明：** 本文件 §1–15 保存首次验收后的 v0.2 失败分析与当时的 BLOCKED 结论，不覆盖历史事实。负责人批准后的最终状态以 §16 为准。

## 4. Coding Contract Closure Matrix

| Obligation | Source | Evidence | Status | 说明 |
|---|---|---|---|---|
| 通用 Registry 候选召回与排序 | CC-CHANGE-001 | IHR-001/006/007、ATR-RUN-003 | FAIL | 真实完整 Registry Top-5 仅 18/40；两次同查询分页候选集合/数量/顺序不稳定。未达到冻结 40/40，不能关闭。 |
| 空候选与歧义处理指引 | CC-CHANGE-002 | IHR-002/006、ATR-RUN-003 | SATISFIED（本轮样本） | 40/40 明确意图最终选模正确；4/4 技术歧义通过只读发现/描述；4/4 实质业务歧义在 search 前澄清；6/6 负向表达未强行选模。 |
| 完整 Registry、盲测、Provider 集成与性能证据 | CC-CHANGE-003 / CC §13 | IHR-006/007、ATR-RUN-003 | FAIL（召回门槛） | 真实 Provider/Agent 与性能证据已取得；结果为 Top-5 18/40、分页不稳定。此前截断请求为 UNKNOWN，不计分。 |
| 保持单一 Retriever / 响应 Schema / stable paging | CC-PRESERVE-001/002/003 | ATR-RUN-002/003 | FAIL（真实稳定分页） | 唯一公开工具和响应形状保持；mock/ORM 稳定排序测试通过；真实 Provider 同查询分页集合、count 与顺序不一致。 |
| 元数据与业务数据权限边界 | CC-PRESERVE-004/005 | ATR-RUN-002 | SATISFIED（定向） | ORM 测试确认元数据可发现、search 权限拒绝；无 sudo/SQL。 |
| M2/M3 兼容 | CC-PRESERVE-006 | ATR-RUN-002 | SATISFIED（定向） | legacy search、响应契约、通用指令回归通过。 |
| CC-TEST-007 Alias 消融 | CC-TEST-007 | IHR / ATR §4 | N/A | 本实现未采用 Alias；符合 CC 条件项处理。 |

## 5. Implementation Closure Assessment

代码变更限于 CC 指定的现有 Retriever、通用 Discovery system instruction、相关测试与证据。未发现新增公开 Tool、Schema 字段、持久化模型、依赖、ACL 变化或业务专用规则。真实 Provider 验收已完成，但 Top-5 与分页门槛 FAIL，故实施验收未通过。

## 6. Preservation & Guardrail Assessment

定向 Retriever / Silent Retrieval TransactionCase 证明既有工具 Schema、legacy search、权限检查和通用指引兼容；真实 Provider Tool Schema 对账也通过。真实语义排序下的候选分页不稳定，故 CC-PRESERVE-003 整体不能判通过。该证据不包含 M2/M3 全量回归。

## 7. Automated Verification Assessment

ATR-RUN-002 的 23 个选定 TransactionCase 方法均通过。ATR-RUN-003 完成了真实 Provider / Agent 验收：CC-TEST-003/004/006 通过，CC-TEST-008 的指标采集完成；CC-TEST-001/002 明确 FAIL，且 CC-PRESERVE-003 真实分页失败。因此整体 Contract 未满足，Closure Status 为 BLOCKED / NOT CLOSED（由实际失败导致，不是缺少 Provider 证据）。

## 8. Human Verification Assessment

Human Verification: N/A。依据：冻结 CC-M4-01 §11.2 的全部测试项均标记为不需要人工验证；本轮不执行 UI HVR。

## 9. Deviation & Stop Condition

未发现未经授权的产品代码范围偏离。757 个 Registry 模型名称、描述、`_rec_name` 至 OpenAI embedding 的发送在用户明确授权后执行；没有业务记录或 Oracle 标签发送给 Provider。此前截断请求接收状态 UNKNOWN，不作为测试结果。GPT chat 候选重排的首次请求在授权前被自动审批拒绝，历史事实保留于 IHR-008 和 `provider_chat_metadata_rerank_block.md`；负责人随后明确授权隔离测试并完成 ATR-RUN-004。该实验未修改产品逻辑或公开接口。

## 10. Open Issues / Evidence Gaps

| ID | Closure Impact | 状态 | 依据 / 下一步 |
|---|---|---|---|
| OI-001 | Resolved | Closed | 用户明确授权 757 个 Registry 模型名、描述及 `_rec_name` 发送至 OpenAI embedding；ATR-RUN-003 已完成。首次截断结果仍 UNKNOWN，不计分。 |
| OI-002 | 历史阻断项，已由 §16 复测关闭 | Closed — final retest PASS | 最终 Top-5 40/40；同一 Thread 两遍分页各 757/757 且完整顺序一致；初始 18/40 与不稳定分页证据保留。 |
| OI-003 | Candidate experiment only | Completed; non-gating | 单独授权后的 GPT chat 隔离实验已完成；见 ATR-RUN-004。它不构成产品验收项；OI-002 的后续关闭依据为 ATR-RUN-005。 |

## 11. Evidence Baseline Consistency

| 来源 | 基线 | 当前有效 | 依据 |
|---|---|---|---|
| IHR | 当前工作树与 IHR-011～013 | Yes | 当前代码、隔离 Provider 请求和清理状态均与补充记录一致 |
| ATR-RUN-006 | `office_engine_m3` 全模块测试日志 | Yes | 63 项统计，55 项执行、0 failed / 0 error |
| Provider / Agent final | ATR-RUN-005 与 evidence manifest | Yes | 最终 40 条 Retriever、66 Thread + P04 重跑、分页双遍历及 SDK 审计均可复核；历史 18/40 和首次超时保留 |

## 12. Done Criteria Assessment

| CC §13 标准 | 证据 | 状态 | 缺口 |
|---|---|---|---|
| #1 完整 Registry 盲测、隔离、指标和性能记录 | Blind set / Oracle / registry snapshot；ATR-RUN-003 | FAIL | 已真实执行并完整记录；Retriever Top-5 18/40，未达到冻结 40/40。 |
| #2 自动化召回、排序、分页、歧义、空结果、权限及 legacy 验收 | ATR-RUN-002/003 | FAIL | 权限、legacy、Agent 选模/歧义和负向路径有通过证据；真实 Top-5 与分页稳定性 FAIL。 |
| #3 真实 Provider GPT-5.6 Luna Agent 工具集成 | `provider_agent_calls_v0.1.jsonl`、`provider_agent_tool_call_correlation_v0.1.json` | PASS（测试链） | 187/187 请求/响应，185/185 Provider Tool Call 与 Odoo Execute 按 Thread、调用 ID、名称和参数完全对应。此 PASS 不覆盖业务数据读取或 Office 写入。 |
| #4 M3/M2 定向回归、IHR/ATR/FR 证据齐备 | IHR、ATR、FR 与 ATR-RUN-002 | PASS（定向范围） | 23 个相关 TransactionCase 方法通过；不代表全 M2/M3 回归。Provider 功能门槛仍失败，故总关闭条件未满足。 |

## 13. Final Closure Determination

**v0.2 Closure Status: BLOCKED（历史评估，保留）**

该状态基于首次 18/40 Top-5 与不稳定分页结果。当前状态由 §16 的 v0.3 复测更新；负责人已批准正式关闭。

## 14. Handoff to Human Review

Closure Assessment Complete: Yes。Human Review Required: Yes。v0.2 的历史 FAIL 已在 §16 按冻结标准复测；负责人已批准本 CC 关闭。该批准不代表 Merge / Release 决定。

## 附录 A — Evidence Reference Index

| 类型 | 路径 | 用途 |
|---|---|---|
| CC | `office_engine/docs/implementation/CC-M4-01_通用业务对象发现_v0.2.md` | 冻结验收权威 |
| IHR | `office_engine/docs/implementation/IHR-CC-M4-01.md` | 实施历史 |
| ATR | `office_engine/docs/implementation/ATR-CC-M4-01.md` | 自动化证据 |
| Evidence | `office_engine/docs/implementation/evidence/CC-M4-01/` | 盲测、Oracle、Registry、日志及 Provider 阻断记录 |

## 15. ATR-RUN-004 补充评审记录

经项目负责人单独授权，使用合成查询与 Retriever 实际返回的最多 50 个 Registry 候选进行 GPT chat 隔离重排。39 次 Provider 请求均有对应响应且无 SDK 错误；Retriever 候选池覆盖目标 34/40，GPT 首选命中 30/40，同轮 Retriever 原始 Top-5 为 18/40。模型仅在 12/40 案例返回完整五项列表。结果不满足冻结 Top-5 40/40，不执行产品集成；原 CC 关闭状态保持 BLOCKED。

## 16. Final Retest Assessment v0.3（当前权威结论）

本节依据 ATR-RUN-005～007、IHR-011～015 和独立 evidence 文件，取代本报告旧章节中的当前状态字段；旧 18/40 与不稳定分页结果仍作为历史事实保留。

| 验收项 | 最终结果 | 证据与边界 |
|---|---|---|
| CC-TEST-001/002：全 Registry Top-5 与语言表达 | PASS：40/40 | 真实 OpenAI GPT-5.6 Luna，完整 Registry 757；没有模型/测试答案映射。 |
| CC-PRESERVE-003：排序分页稳定性 | PASS | 同一 Thread 两遍遍历各 757/757、唯一 757、count 恒为 757，逐页顺序完全一致。首次完整排序持久化在现有隐藏 `mail.message`；后续页和重复遍历复用，未依赖 GPT 再次返回同序。 |
| CC-TEST-003：Agent describe 选模 | PASS（含记录的 P04 重试） | 初跑 40 个明确任务中 39 个完成；P04 首次 Provider 超时，未进入 Discovery，保留 NOT REACHED。P04 独立重试通过后，40 个唯一案例均正确 describe 目标模型。 |
| CC-TEST-003：歧义处理 | PASS | 技术歧义 4/4 由只读 discover/describe 消解；业务歧义 4/4 在业务 search 前澄清。 |
| CC-TEST-004：负向表达 | PASS | 6/6 未编造模型、未执行业务 search。 |
| CC-TEST-005/006：权限、Schema、工具链及兼容性 | PASS（定向） | `office_engine_m3` 全模块测试；Agent 请求仅携带 Retriever 与 Office Tool Schema；Provider/Odoo Tool Call 171/171 + P04 重试 3/3 对账。未读取业务记录、未使用 sudo/SQL。 |
| CC-TEST-007：Alias 消融 | N/A | 未采用 Alias，按冻结 CC 条件项规则 SKIPPED。 |
| CC-TEST-008：性能记录 | PASS（仅采集义务） | Registry 757；direct discover p50/p95 6.155/8.826s，embedding 3.963/5.496s，GPT rerank 1.813/3.526s；Agent 66 Thread p50/p95 17.372/26.869s（含首轮 Provider 超时）。无硬性 p95 门槛。 |
| CC-TEST-009：组件回归 | PASS（M3 范围） | `office_engine_m3` 全模块 Odoo test runner：63 项统计，55 项实际执行，0 failed / 0 error；审计隔离调整后 ATR-RUN-007 再次通过。M2 全量未执行，不作通过声明。 |
| GPT 重排请求 Thread 历史隔离 | PASS | 实际 OpenAI SDK 审计：40/40 直接重排、Agent 69/69 内部重排及 P04 重试 1/1 请求均为两条 `[system,user]` 消息、无 tools；user JSON 仅有业务查询和 757 条 Registry 元数据候选。请求、响应 ID 可对账。 |
| Python 注释语法与覆盖计数 | 有限通过；语义质量不作为 CC-M4-01 验收项 | 189 个 Python 文件 AST/py_compile 通过且覆盖计数符合脚本标准；后续复核发现其他模块仍有模板式 Docstring。CC-M4-01 修改代码内的中文说明已审阅；仓库级注释质量清理仍未完成，不应表述为全面 PASS。 |

**关闭决定：** 项目负责人于 2026-11-19 批准关闭 CC-M4-01。冻结 CC 适用验收项均有通过证据；CC-TEST-007 按条件不适用。M2 全量回归和 UI HVR 未执行，不计为本 CC 通过项。本报告不作 Merge / Release 决定。

### 17. CC 关闭后的独立注释质量事项

负责人此前另行要求补齐仓库 Python 注释。机械覆盖与语法检查已执行，但后续质量复核识别到 1,087 处模板式通用 Docstring；这些问题不属于冻结 CC-M4-01 的产品验收条件，也没有随本 CC 选择性提交。CC-M4-01 范围内变更的代码说明已修正并纳入提交；仓库其余 Python 文件的注释质量清理仍待完成。
