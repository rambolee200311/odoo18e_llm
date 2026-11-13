# CC-M3-01 — Retriever 增强 v0.2

| 项目 | 内容 |
|---|---|
| CC | `CC-M3-01` |
| 版本 | v0.2 |
| 状态 | **Frozen — 已获负责人批准并授权进入实施** |
| 目标模块 | `office_engine_m3`（拟新增下游 addon） |
| 计划阶段 | M3 Implementation Plan v0.2 / CC-M3-01 |
| 技术基线 | M3 TDD v0.3（Frozen with open items）；v0.2 保留为历史版本 |
| 关联计划 | `IMPLEMENTATION_PLAN_office_engine_m3_v0.2.md`；`PLAN-M3-002` |
| 业务基线 | M2 SRS v1.1.0 Frozen；M3 SRS N/A 决策 `DECISION-M3-SRS-NA-001` |

> 本文以中文定义 CC 范围、边界和验收条件。工具名、模型技术名、字段名、错误码、测试 ID 与 API 标识保留原文。负责人于 2026-11-13 批准冻结本 CC 并进入实施，授权记录为 `CC-M3-01-001`。授权仅限本 CC 的下游代码与测试。Odoo 仅使用现有开发数据库 `odoo18e_llm`，不得新建数据库；不因此推定 Provider 外发或生产环境授权。

## 1. 目标与结果

在 `odoo18e_llm` 的下游 `office_engine_m3` addon 中，扩展现有唯一公开记录检索工具 `odoo_record_retriever`，使 Agent 能够在同一工具协议中执行 `discover`、`describe` 和 `search`。同时增强稳定分页、排序、列表型 `in` Domain、结构化错误和旧调用兼容。

Registry Schema Discovery 是通用元数据能力：现有 Retriever 工具调用者可以发现 Registry 模型和字段定义，不按业务模型 ACL、Record Rules 或字段组筛选。发现只读取 Schema，不读取业务记录，也不授予业务数据访问权。所有 `search` 和关联业务读取继续严格遵守调用者当前 ORM 权限，并且不得使用 `sudo()`。

## 2. 冻结门禁与状态划分

### 2.1 设计决策

| 项目 | 决策 / 状态 | 对 CC-M3-01 的影响 |
|---|---|---|
| Registry 元数据可见范围（OPEN-05） | **设计决策已由负责人本轮指令关闭**。`discover/describe` 不核查当前用户的业务模型 ACL、Record Rules 或字段组；不读取业务记录、不使用 `sudo()`。`search` 仍按当前用户 ORM 权限执行 | 不再作为 CC 冻结或开工门禁；按 `TEST-RET-002` 在实施验收时验证，当前仍为 NOT RUN |
| Domain JSON Schema 扩展点可行性 | Registry Discovery TV 已通过隔离试验验证下游扩展同一工具 Schema、真实 Tool Execute 分发；未验证 Provider 对数组 Schema 的完整接受 | 不要求为已验证的继承 / 分发机制重复做 Spike；Provider、Tool Execute、ORM 的实际数组兼容性仍必须按 `TEST-RET-004` 完成实施验收 |
| Hosted CI handoff（OPEN-01b） | 与本 CC 无关，完整 handoff Spike 仍为 CC-M3-02 前置项 | 不阻断 CC-M3-01 |
| 测试环境 / 人员 | 技术冻结前不要求指定测试环境或开发、评审、测试人员 | 实际测试前核实运行配置指向现有开发库 `odoo18e_llm`、测试数据为合成数据、测试事务会回滚且所需专项 Provider 授权已具备；不得新建数据库。人员安排不作为技术冻结门槛 |

### 2.2 当前门禁结论

- M3 TDD v0.3 与 Implementation Plan v0.2 已按 `TDD-M3-002` / `PLAN-M3-002` 冻结并基线化；本 CC 已按 `CC-M3-01-001` 冻结，实施范围限于本契约。
- OPEN-05 的设计问题已由负责人决定关闭；实施测试尚未运行，不写成通过。
- OPEN-01 Domain Schema 三层兼容性是 CC-M3-01 完成验收条件，不是编码前或 CC 技术冻结前置条件。Provider 未获执行授权或测试未完成时，`TEST-RET-004` 保持 NOT RUN，CC 不得验收关闭。
- OPEN-01b Hosted CI handoff Spike、OPEN-02/03/04/06 不在本 CC 的实现范围，不阻断本 CC 的技术冻结或实施；其阶段门禁仍按对应计划执行。
- 正式实施前仍需有效冻结的 TDD、已批准并基线化的 Implementation Plan、本 CC 冻结授权。开始实际测试前核实现有开发库 `odoo18e_llm`、合成数据和事务回滚边界；Provider Schema 验证仅在获授权时执行。

## 3. 上游追溯

| 上游 | 本 CC 范围 |
|---|---|
| M3 TDD `API-RET-001`、§5.2、`T-M3-SEC-001` | Registry `discover/describe`、`search`、Schema 可见范围与权限分离 |
| M3 TDD `T-M3-RET-001` | 分页、稳定排序、旧响应兼容 |
| M3 TDD `T-M3-RET-002` | 标准 Odoo Domain、`in` / `not in` 数组及工具协议兼容 |
| M3 TDD `TEST-RET-001`–`TEST-RET-005` | 本 CC 的 Retriever 自动化与集成验收 |
| M2 SRS v1.1.0 / M2 TDD v2.1.0 及适用修订 | 保持既有业务语义、工具身份、ORM 权限和文件 / Candidate 边界 |

本 CC 以冻结 TDD v0.3 与冻结 Plan v0.2 为基线；v0.2 文件仍保留为历史版本。

## 4. 实施范围（拟议）

### 4.1 范围内

1. 在现有 `odoo_record_retriever` 上扩展可选 `operation`：`discover`、`describe`、`search`。缺省 `operation` 继续按旧 `search` 路径解释。
2. `discover` 根据运行时 Registry 的 `_name` / `_description` 做通用查询，并返回技术模型名、描述、`_rec_name` 及分页信息。
3. `describe` 返回模型的完整 Registry 字段定义：技术字段名、标签、类型、静态 Selection 选项、关联模型及可得反向字段信息；不得按当前用户业务 ACL、Record Rules 或字段组过滤。对动态 Selection，不调用可能读取业务记录的函数来生成选项；Schema 描述其动态定义。
4. Registry 操作只读 Registry 模型 / 字段结构，不访问业务记录；不得使用 `sudo()`、SQL、特权用户或服务账号。
5. 显式 `search` 按 M3 分页契约返回结果，使用稳定排序：空排序默认为 `id asc`，显式排序追加 ID tie-breaker；最大单页限制沿用 TDD。
6. Domain 按标准 Odoo Domain 处理，并支持 `in` / `not in` 的 JSON 标量数组；不引入业务模型专用分支。
7. 返回稳定错误码 `MODEL_NOT_FOUND`、`FIELD_NOT_FOUND`、`ACCESS_DENIED`、`INVALID_QUERY`、`QUERY_FAILED`；成功零结果仍为成功响应。
8. 通过下游 addon 扩展现有工具和分发，不修改上游 `odoo-llm`，不新增公开 Tool。

### 4.2 范围外

- 不修改 `odoo-llm/**`、M2 addon、M2 Candidate / Current / Accept / Reject / Finalize 生命周期或既有文件生成架构。
- 不实现完整数据 collector、Office handoff、Hosted Code Interpreter Excel 生成、Silent Retrieval、最终 Agent UI HVR；分别属于 CC-M3-02 / CC-M3-03。
- 不新增 Registry Tool、批量查询 Tool、报表工具、本地 Excel Writer、特定业务模型或字段逻辑。
- 不访问生产环境，不修改既有业务记录或 ACL，不调用 Provider，测试只可连接现有 `odoo18e_llm` 开发数据库；addon 安装 / 升级与合成测试事务仅作用于该库，不得创建数据库或触及生产库。

## 5. 对既有 `limit` / `offset` 的源码核对

已检查 `odoo-llm/llm_tool/models/llm_tool_record_retriever.py` 中 `LLMToolRecordRetriever.odoo_record_retriever_execute()`（当前源码约第 19–98 行）。以下是现状，不是 M3 目标契约：

- 缺省值为 `limit=100`、`offset=0`、`order=""`、`include_pagination=False`。
- `limit` 必须为精确 Python `int` 且范围 1–500；`offset` 必须为精确 `int` 且不小于 0；无效值抛出 `ValidationError`。
- 显式非空 `order` 在未含 ID 时追加 `id`；空 `order` 传为 `None`，因此当前实现不保证默认按 ID 排序。
- `include_pagination=False` 返回序列化记录列表；为 True 时返回 `records/count/offset/limit/has_more`，没有 `returned_count` 和 `next_offset`。

M3 的显式 `search` 按修订后冻结 TDD 的新分页响应执行。未提供 `operation` 的调用保留现有参数解释与成功返回形状。

## 6. 行为变更与兼容要求

| 项 | 现状 | 本 CC 要求 |
|---|---|---|
| 操作分发 | 只有旧 `search` | 同一工具支持 `discover / describe / search`；未知 operation 返回 `INVALID_QUERY` |
| Registry Schema | 尚无 Retriever 级 Discovery | Registry 结构对现有工具调用者开放，不检查业务 ACL / Record Rules / 字段组，不读业务记录 |
| `limit/offset` | 有 1–500 / 非负校验，但空排序不稳定，分页 envelope 可选且无 next offset | 显式 M3 `search` 按 TDD 返回分页元数据、稳定排序；旧调用保持原 shape |
| Domain | 现有工具 Schema 未端到端证明数组 `in` | 标准 Domain 支持列表型 `in` / `not in`；三层兼容性由 `TEST-RET-004` 实证 |
| 错误 | 错误信息不稳定，容易与空结果混淆 | 五类稳定错误码；成功零结果保持 `status=success` 与空记录 |

## 7. 必须保留的既有行为

- 公开工具名称、现有工具身份、旧参数调用、缺省 `operation` 的语义及原有成功返回形状。
- 所有业务记录读取继续使用调用者当前 ORM 环境，遵循模型 ACL、Record Rules、公司上下文及字段访问；不得以 Registry Schema 或发现成功推导业务访问权。
- `search` 的权限拒绝必须报告为权限错误，不得改报模型不存在或零条记录；Record Rule 下的零可见行仍是成功零结果。
- 无 `sudo()`、直接 SQL / cursor、权限更高的替代用户或 fallback service identity。
- M2 功能和 M2 Retriever 回归契约不变。

## 8. 权限 / 安全契约

| 操作 | Registry Schema 可见范围 | 是否读业务记录 | 业务权限要求 | `sudo()` |
|---|---|---:|---|---:|
| `discover` | 所有现有 Retriever 工具调用者可发现运行 Registry 模型定义 | 否 | 不核查调用者对该业务模型的 ACL、Record Rules 或字段组 | 禁止 |
| `describe` | 返回模型的完整 Registry 字段定义、关系及 Selection 定义 | 否 | 不核查调用者对该模型或字段的 ACL、Record Rules 或字段组 | 禁止 |
| `search` / 关联读取 | Registry 仅用于字段 / 关系语义，不代替 ORM 授权 | 是 | 严格遵守调用者当前 ORM 的 ACL、Record Rules、字段访问及公司上下文 | 禁止 |

元数据属于通用 Schema Discovery 范围。不得在 Registry 操作中调用 `check_access_rights`、Record Rule 过滤、字段组过滤或业务记录读取来限制 Schema 返回；不得通过 `sudo()` 获取元数据。实现可以直接读取正常运行环境中的 Registry 模型 / 字段定义。Schema 返回不证明模型记录可读，也不扩大 `search` 权限。

## 9. 错误与返回边界

- `MODEL_NOT_FOUND`：Registry 中没有请求模型。
- `FIELD_NOT_FOUND`：Registry 模型定义中没有请求字段。
- `ACCESS_DENIED`：仅用于 `search` / 关联业务读取被当前用户 ORM 权限拒绝。
- `INVALID_QUERY`：参数、Domain、operator、order、limit / offset 或字段组合非法。
- `QUERY_FAILED`：无法归类的 ORM / Runtime 查询失败；保留受控诊断信息。
- 成功零结果必须与错误区分；不得将 ACL / Record Rule 拒绝误报成 `MODEL_NOT_FOUND` 或空结果。
- 不向 Agent / 用户回传 SQL、traceback、内部路径、凭证或不必要的敏感查询值。

## 10. 测试契约

本节所有项目当前均为 Planned / NOT RUN。正式测试前确认现有 `odoo18e_llm` 开发数据库、确切代码 / addon / runtime、合成 fixture、事务回滚和所需授权。不得创建数据库。Provider 层须有独立执行授权。

| 测试 ID | 测试内容 | 执行方法 | 通过条件 |
|---|---|---|---|
| `TEST-RET-001` | 操作分发与旧接口兼容 | Odoo 单元测试 + 真实 `llm.tool.execute()` | 旧调用不带 operation 时保留输入解释和成功返回 shape；显式 discover/describe/search 经同一工具分发；未知 operation 为 `INVALID_QUERY` |
| `TEST-RET-002` | Registry Schema 与业务记录权限隔离 | Odoo TransactionCase；以没有目标业务模型读 ACL 的调用用户执行 Registry 操作及 search | discover/describe 返回 Registry 声明的完整模型 / 字段 Schema（包含组受限字段定义），不查询业务记录且不执行 ACL、Record Rule、字段组过滤；search 仍由当前用户 ORM 授权或拒绝。此测试验证“不做元数据权限检查”，不把 Schema 可见性视为记录权限 |
| `TEST-RET-003` | 分页与稳定排序 | 单元测试 + TransactionCase | 空 order 为 ID 升序；显式排序稳定追加 ID；页边界、count、returned_count、has_more、next_offset 正确；旧返回 shape 不变 |
| `TEST-RET-004` | Provider / Tool Execute / ORM 的 Domain Schema 兼容 | 获授权 Provider Schema 验证 + 真实 `llm.tool.execute()` + ORM 集成测试 | scalar 与列表型 `in` / `not in` 在三层均符合契约；ORM 返回遵守当前用户 ACL / Record Rules。任何一层失败或证据缺失都阻断本 CC 验收关闭；但不作为编码前或 CC 技术冻结门禁 |
| `TEST-RET-005` | 结构化错误与零结果 | 单元测试 + TransactionCase + 故障注入 | 不存在模型 / 字段、search 中不可访问字段、无权 search、非法 Domain / order、运行时异常映射至稳定错误码；Record Rule 零行是成功结果；权限错误不误报模型不存在 |
| M2 Retriever 回归 | 旧接口及 M2 现有使用 | 现有选定集成测试 | 实际记录运行测试名称和结果；不将选定套件通过表述为整个 addon 全绿 |

### 验收证据

- `TEST-RET-004` 必须经过真实 Tool Execute 和 ORM；不能只直调 Python 方法。
- Provider Schema 证据必须绑定 Provider / Tool Schema 版本、运行环境与输入；无授权则维持 NOT RUN，不能声明通过或关闭 CC。
- TransactionCase 使用合成数据验证 Registry 返回全 Schema，同时确认没有执行业务记录读取；另验证 `search` 实际遵循 ORM 权限。
- 每项 ATR 记录代码 / addon / Odoo runtime / 测试数据库身份、输入、结果和原生状态。失败、跳过或缺失证据不得改写为 Passed。

## 11. 数据库、迁移与回滚

- 不计划业务数据迁移。本 CC 允许在现有开发数据库 `odoo18e_llm` 中安装 / 更新本 CC addon 并运行事务回滚测试；不得新建数据库、修改既有业务记录或连接生产数据库。
- 测试与模块安装 / 升级只使用已确认的 `odoo18e_llm` 开发数据库；合成测试记录须在 Odoo 测试事务中回滚。
- 任何新增字段、模型或持久化影响必须先证明属于本 CC 范围；否则停止并评审。
- 回滚限于在同一 `odoo18e_llm` 开发数据库中卸载 / 禁用新增 M3 addon 并按 IHR 记录；不触及生产。

## 12. 停止条件

| 条件 | 处置 |
|---|---|
| 实际运行的 TDD / Plan 与本 CC 基线不一致 | 停止实施，先完成版本影响评审 |
| 下游 addon 无法扩展既有 Schema / dispatch，而必须改上游 | 停止，退回 TDD 评审；不得修改 `odoo-llm` |
| `TEST-RET-004` 任一兼容层失败 | 不关闭 CC；定位 Provider / Tool / ORM 边界，修正后重跑，必要时退回 TDD；不把失败改成通过 |
| 业务 `search` 需要 `sudo()`、SQL 或 ACL / Record Rule 放宽 | 立即停止并升级安全 / TDD 评审 |
| `discover/describe` 开始查询业务记录或执行当前用户元数据权限过滤 | 与本 CC 架构决策冲突，停止并修正实现 |
| 配置未指向 `odoo18e_llm` 或测试触及生产数据 | 不执行测试；先核对现有开发环境配置。不得新建数据库替代 |
| 工作要求涉及全量 collector、Office、Candidate 生命周期或静默消息 | 延后至 CC-M3-02 / CC-M3-03，不扩大本 CC |

## 13. 完成定义

CC-M3-01 只有同时满足下列条件才可提交关闭评审：

1. 正式 CC 已获批准并冻结，Implementation Plan 与当前冻结 TDD 对齐；代码仅改授权下游 addon 和其测试。
2. `TEST-RET-001` 至 `TEST-RET-005` 与 M2 Retriever 回归均有真实 ATR 证据；`TEST-RET-004` 三层证据齐全。
3. Registry Schema 不做业务权限过滤、不读取记录、不使用 `sudo()`；`search` / 关联查询严格遵守当前用户 ORM 权限。
4. 旧调用兼容、稳定分页与错误分类满足本 CC 契约；所有失败和缺失证据如实保留。
5. IHR、ATR、FR 引用实际代码与测试基线。此 CC 不要求人工 UI HVR；真实 Agent UI E2E 属于 CC-M3-03。

冻结时尚无测试、Provider 调用或实施结果。只有实际 ATR 证据齐备后才能评估是否满足完成定义。

## 14. 双向追溯

| TDD / 测试项 | 对应变更 | 覆盖 |
|---|---|---|
| `API-RET-001`、`M3-REQ-01` | Registry operation 扩展与旧调用兼容 | `discover/describe/search`、metadata contract、legacy shape |
| `T-M3-RET-001` | 分页与稳定排序 | `TEST-RET-001`、`TEST-RET-003` |
| `T-M3-RET-002` | Domain Schema / `in` arrays | `TEST-RET-004` |
| `T-M3-SEC-001` | 元数据与业务记录权限边界 | `TEST-RET-002`、`TEST-RET-005` |
| `TEST-RET-001`–`TEST-RET-005` | CC-M3-01 验收 | ATR，状态 NOT RUN 直至实际执行 |

## 15. 版本记录

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-13 | 核对既有 limit/offset 源码；曾将 OPEN-01 / OPEN-05 误列为 CC 冻结前门禁 | 历史 Draft，未冻结 |
| v0.2 | 2026-11-13 | 按负责人决策修订元数据权限；关闭 OPEN-05 设计门禁；将 OPEN-01 三层兼容验证移为实施验收；CC 全文改为中文；限定使用现有 `odoo18e_llm` 数据库 | Frozen；授权记录 `CC-M3-01-001` |
