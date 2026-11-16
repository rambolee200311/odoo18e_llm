<!--
Template source: office_engine/docs/skill/odoo-project-workflow/references/templates/Coding/Coding_Contract模板.md
Template version/status: v1.0.0 Frozen
Template synchronization check: PASS (2026-11-13)
-->

# CC-M3-02 — 完整数据至 Office v0.2

| 项目 | 内容 |
|---|---|
| CC | `CC-M3-02` |
| 版本 | v0.2 |
| 状态 | **FROZEN WITH OPEN GATES — 未授权实施** |
| 计划阶段 | M3 Implementation Plan v0.3 / CC-M3-02 |
| 技术基线 | M3 TDD v0.4（`TDD-M3-003`） |
| 计划基线 | Implementation Plan v0.3（`PLAN-M3-003`） |
| 前置 CC | CC-M3-01，已验收、关闭并推送 |
| 目标模块 | `office_engine_m3`（下游 addon） |
| 冻结记录 | `CC-M3-02-001`；仅冻结本 CC 文档范围，不授予 Coding Authorization |
| 数据库边界 | 如后续获准测试，仅使用现有开发数据库 `odoo18e_llm`；不得创建数据库或访问生产环境 |

> 负责人于 2026-11-13 批准冻结本 CC v0.2，记录为 `CC-M3-02-001`。此冻结仅建立 CC 文档基线，不构成 Coding Authorization、Provider / Hosted Code Interpreter 外发授权、数据库操作授权或发布授权。OPEN-01b/02/03/04 的最小技术可行性 Spike 仍为 Missing，未完成前不得实施；Spike 完成后还须取得单独 Coding Authorization。本文不预选未经验证的数据交接格式，不新增本地 Excel 内容生成器。

Freeze disposition: `FROZEN WITH OPEN ITEMS`; authorization register: `docs/implementation/AUTHORIZATION_RECORDS.md`; records: `CC-M3-02-001`, `EXEMPTION-TDD-M3-V04-OPEN-01B-001`, `EXEMPTION-TDD-M3-V04-OPEN-02-001`, `EXEMPTION-TDD-M3-V04-OPEN-03-001`, `EXEMPTION-TDD-M3-V04-OPEN-04-001`.


## 0. 文档治理

- 上游设计与计划为唯一技术权威；本 CC 只裁剪本轮执行范围，不重新设计 TDD。
- 本版本已冻结；任何实施仍须满足入口门禁并取得单独 Coding Authorization。
- 验收证据以本 CC 明确纳入的自动化与集成测试为准；最终真实 Agent UI HVR 属于 CC-M3-03。
- 本 CC 依据冻结 TDD v0.4 与 Plan v0.3；不改变 M2 SRS / TDD 或已关闭的 CC-M3-01。

## 1. 目标与背景

LLM 负责理解用户意图、选择模型与字段、确定关联范围、查询条件及输出计划；本地 Collector 不实现业务规划器，只执行已确定的通用查询计划，完成分页、批量收集和客观完整性检查。完整数据交给既有 M2 Route B / Hosted Code Interpreter，由 LLM + Hosted CI 生成或修改 Excel，并执行复杂聚合和语义计算。本地仅核验可客观验证的数据、handoff、文件及版本完整性。只有强制完整性 / 文件核验通过后，才按 M2 既有验证等级登记 Candidate；用户仍须决定 Accept / Reject，并通过 Finalize 交付 Accepted Current。

完整性不得依赖 Agent 对多页数据的上下文记忆、拼接或自行判断；单页上限不得成为最终导出数量上限。数据完整性与源数据新鲜度分别记录；默认不在 Accept 前重复全量查询。复杂聚合或语义结果不能独立验证时，沿用 M2 `PARTIALLY_VERIFIED` / 用户审阅语义，不增加本地计算引擎或新的 Candidate 状态。

## 2. 上游基线与实施门禁

### 2.1 权威基线

| 来源 | 状态 / 版本 | 本 CC 追溯 |
|---|---|---|
| M3 TDD | Frozen v0.4 / `TDD-M3-003` | §§3、5、6、9–12、14–18；`API-OFFICE-EXPORT-001`、`API-HANDOFF-001`、`API-EXPORT-RECEIPT-001`、`T-M3-DATA-001`–`004`、`T-M3-VERSION-001`、`T-M3-PRIV-001`、`T-M3-COMP-001` |
| M3 Implementation Plan | Frozen v0.3 / `PLAN-M3-003`; baseline validity `VALID` | §4 CC-M3-02、§§6–8、§13 |
| CC-M3-01 | 已验收、关闭并推送 | 前置 Retriever 契约、分页和 Domain 能力 |
| M2 SRS | v1.1.0 Frozen | 只约束原有 M2 用户决策、文件和确认语义 |
| M2 TDD | v2.1.0 Frozen，含适用修订 v2.1.1 / v2.1.2 | Route B、Candidate / Current / Accept / Reject / Finalize、版本和文件边界 |
| M3 SRS / DDD | N/A | `DECISION-M3-SRS-NA-001`；本 CC 不新增业务领域或状态 |

### 2.2 实施前最小可行性 Spike 与实施验收

| TDD OPEN | 实施前最小技术可行性 Spike（不等同于完整验收） | 实施阶段最终验收（保持原标准） | 当前状态 / 责任边界 |
|---|---|---|---|
| `OPEN-01b` Hosted CI handoff | 用真实 Route B / Hosted CI 路径和 synthetic sentinel，证明至少一种候选载体能到达并被读取；据证据选载体。不要求 Spike 先完成 148 条或更大数据验证 | `TEST-DATA-001/002`：148 条 100+48 与更大有界数据集完整收集、传递、读取；核对 counts / identity / digest / 实际 XLSX | 前置 Spike Missing；最终验收 NOT RUN；`EXEMPTION-TDD-M3-V04-OPEN-01B-001`。由 CC-M3-02 Spike 报告及 ATR 分别记录 |
| `OPEN-02` 资源边界 | 证明至少存在有限可行执行区间，并能测量行数、关系数、handoff bytes、Provider 输入 / 输出与墙钟时间；不要求预先完成精确生产限额 | `TEST-DATA-005` 与基准：定出有限服务端上限，验证限额内、临界和超限；超限失败关闭 | 前置 Spike Missing；上限与实施测试 NOT RUN；`EXEMPTION-TDD-M3-V04-OPEN-02-001`。禁止宣称无界能力 |
| `OPEN-03` 事务 / 新鲜度 | 最小验证计划调用链可复用同一个 cursor / transaction，不按页 commit / 换 cursor；不要求预先完成全部并发与 freshness 测试 | `TEST-DATA-006`：验证 root / relation 多页读视图、并发 insert/update/delete 行为、freshness 记录与显式刷新；默认不二次全量查询 | 前置 Spike Missing；运行时验收 NOT RUN；`EXEMPTION-TDD-M3-V04-OPEN-03-001`。使用现有 `odoo18e_llm` 与合成数据 |
| `OPEN-04` 输出核验 | 用现有 Candidate / 文件检查路径证明可客观检查文件可读性、身份完整性；定义语义不可独立验证时的 M2 `PARTIALLY_VERIFIED` / 用户审阅级别 | `TEST-XLSX-001`：核对 projection 全量 identity / 指定字段、真实 Hosted CI 输出、已知 synthetic 聚合 fixture 常量、文件 / SHA / 版本绑定；不在生产运行时增加聚合 / 语义重算器 | 前置 Spike Missing；实施验收 NOT RUN；`EXEMPTION-TDD-M3-V04-OPEN-04-001`。常量仅用于测试，Hosted CI 执行任务计算 |
| `OPEN-06` Silent Retrieval | 不属于本 CC 门禁 | 保持 TDD 原状态 | 由 CC-M3-03 处理，不阻断本 CC |

CC-M3-01 已关闭，但不替代 CC-M3-02 的 Spike 或实施验收。前置 Spike 只关闭技术可行性门槛，不降低最终接受要求。只有四项最小 Spike 均有可复核结果并另获 Coding Authorization 后，才可开始实施；本 CC 及适用 TDD / Plan 已冻结。TEST-DATA-001/002/003/004/005/006、TEST-XLSX-001 与生命周期回归仍须在 CC 内完成。当前前置 Spike Missing、最终测试 NOT RUN，均不得标记 Passed。

## 3. 范围冻结

### 3.1 范围内

1. LLM / Agent 根据自然语言确定业务意图、模型、字段、关系范围、查询条件、输出规划和任务类别；信息不足时先澄清。本地不得增加业务规划器，也不得自行猜选模型、字段或关系。
2. Collector 只接收已确定的通用查询计划，校验 Schema / Registry 关系与当前用户权限后执行 root 分页、Many2one / One2many / Many2many `in` / 有界 chunk 批量查询、identity 去重和 parent-child 完整性核对；只支持用户规划中明确选择的直接关系，不递归展开任意关系图。
3. 所有 root / relation 查询使用当前用户 ORM 权限及同一已验证 read view；针对 Registry 关系元数据校验关系类型、comodel、inverse，不用元数据绕过 ACL / Record Rules。
4. 建立格式无关的内部 handoff contract / manifest；仅实现 OPEN-01b Spike 已证明的最小 transport profile。将完整有界数据集通过既有 Route B 请求送到 Hosted Code Interpreter，不经 LLM 对话历史传递多页记录。
5. 通过同一既有 `office` Tool 扩展 `action="export_records"`，服务端解析 `workbook_source="new"` 或受控的 `"current"`。`current` 只能解析当前用户 Thread / Session 的 Accepted Current 附件与 SHA；Agent 不可指定文件路径或版本 ID。
6. 保留 M2 Route B：LLM + Hosted Code Interpreter 负责 Excel 内容生成 / 修改及复杂聚合 / 语义计算；本地只做权限、通用计划执行、分页 / 批量收集、客观 source / handoff / 文件 / 版本完整性核验、receipt 和既有确认门禁。禁止本地报表规划器、Excel writer、通用聚合器或语义计算引擎。覆盖新建与现有工作簿编辑两种 Route B 用法。
7. 按任务类别执行客观核验：projection 可比较完整 identity / 被要求保持的字段；聚合 / 语义由 Hosted CI 计算，本地核对 source / handoff completeness、文件字节 / 结构 / SHA、可客观读取的 provenance 与版本绑定。仅在有固定 synthetic fixture 时可用预先期望值作测试断言；生产不本地重算。将紧凑 `API-EXPORT-RECEIPT-001` 绑定到现有 M2 版本服务。
8. 仅当强制的 source / handoff 完整性、客观文件检查及版本绑定通过后，才登记 Candidate；任务语义验证级别按 M2 既有契约如实记录，不能独立验证的复杂计算沿用 `PARTIALLY_VERIFIED` / 用户审阅语义。复用 Candidate、Current、Accept、Reject、Finalize、版本绑定和用户确认门禁。
9. 对分页、关联、资源、交接、Provider、文件或验证失败执行 fail-closed：不得生成完整 Candidate、不得推进 Current；要求用户收窄范围时发起新请求。不增加 Partial Candidate / Partial Accept 流程。
10. 增加自动化、ORM / 集成测试、M2 定向回归和 ATR 证据；真实 Hosted CI 测试仅在取得独立外发授权后执行。

### 3.2 范围外

- 修改上游 `odoo-llm`、`office_engine_m2` 或其它 addon；增加新公开 Tool、第二个 Adapter、报表引擎或独立查询服务。
- 在 OPEN-01b 之前选定、固定或实现 JSON、CSV、XLSX 或其它物理 handoff 格式；将大数据集拼入 Tool message / LLM context；依赖模型记忆分页结果。
- 本地使用 `openpyxl` 或其它方式生成、改写、修补 Excel 内容；替代或改变 M2 Route B 的通用文件编辑能力。
- 模型、字段、模板、列、工作表、坐标、业务规则专用分支；递归关系展开、持久化源快照、数据缓存、Partial Candidate。
- 更改 M2 的用户决策、确认语义或 Candidate / Current / Accept / Reject / Finalize 状态机；M3 新建导出不得走 CC-09 fileless direct-V1 例外。
- Silent Retrieval、SSE / Discuss / Bus 消息过滤、最终 Agent UI E2E / 148 条真实用户 HVR（属于 CC-M3-03）。
- 本次文档冻结不授权任何代码、Provider 请求、数据库读写、模块安装 / 升级、部署或 Git 发布。

## 4. 变更边界

### 4.1 允许的实施文件面（取得 Coding Authorization 后）

| 类型 | 允许范围 |
|---|---|
| 新增下游代码 | `office_engine/office_engine_m3/**` 中实现 collector、handoff、Route B 调度、任务输出核验及版本凭据所必需的最小文件 |
| 新增下游测试 | `office_engine/office_engine_m3/tests/**` 与本 addon 注册测试所需的 `__init__.py` / manifest 调整 |
| 版本 receipt 字段 | 按 TDD §3.2 / §16.3，只有实现所需的最小 nullable receipt 字段及 addon ACL / migration 定义；不得新增源数据快照模型 |
| 实施证据 | 本 CC 的 IHR、ATR、Route B 合成数据集成证据；Provider 原始证据须控制敏感信息 |

任何需要改动 M2 文件、上游 Adapter、M2 公共接口、现有 Candidate 状态或其他文件面的提案均须停止并做影响评审；不得直接扩大允许列表。

### 4.2 禁止

| 对象 | 禁止事项 |
|---|---|
| `odoo-llm/**`、`office_engine_m2/**` | 修改、复制或替换上游 / M2 实现；建立第二条 Route B |
| 数据权限 | `sudo()`、SQL / cursor 直接查业务数据、提升权限用户、改 ACL / Record Rules、绕过公司上下文 |
| Excel 内容 | 本地 writer 生成或修补表格内容；把 `openpyxl` 当生成器或修复器 |
| 输入与输出范围 | 静默截断；不完整时仍交付为完整；创建独立 Partial Candidate |
| 数据保存 | 持久化完整 source dataset、快照或缓存；receipt 不得放原始业务记录 / 敏感 domain |
| 用户门禁 | Candidate 未通过验证或未经用户 Accept 时推进 Current；Finalize 改变被接受文件字节 |

## 5. 必需的行为变更

| ID | 当前 / 缺口 | 目标行为 | TDD 来源 |
|---|---|---|---|
| CC-CHANGE-001 | 现有 Retriever 单次分页不构成 Office 全量数据交付 | Office 服务端在当前授权范围内循环所有页，验证分页进展、总数、唯一身份、终止与任务字段；不依赖 Agent 上下文 | `T-M3-DATA-001`；§6.2 |
| CC-CHANGE-002 | 多父记录关联明细无法由对话分页可靠拼全 | 对用户选择的直接关系按 `in` 批量查询、保留关系 pair；用有限 chunk，不按父记录逐条 N+1，不递归 | `TEST-DATA-003`；§6.3 |
| CC-CHANGE-003 | 当前 Route B 未证明可承载完整多页 dataset | 定义格式无关 manifest / contract；经 OPEN-01b 选定且真实证实的载体完整进入当前 Route B / Hosted CI；传输前后核对 count、identity digest、bytes / SHA | `API-HANDOFF-001`；`TEST-DATA-001/002` |
| CC-CHANGE-004 | 当前无全量导出 action 与客观完整性门禁 | 在唯一现有 `office` Tool 中扩展 `export_records`；LLM + Hosted CI 写 Excel 并执行复杂计算；本地只检查客观 identity / 字段 / handoff / 文件 / 版本完整性 | `API-OFFICE-EXPORT-001`；`TEST-XLSX-001` |
| CC-CHANGE-005 | 输出完整性事实未绑定到 Candidate | 只在收集、交接、文件、profile 验证全部通过后登记真实 XLSX Candidate；以紧凑 receipt 绑定 Candidate version / SHA / scope | `API-EXPORT-RECEIPT-001`；`T-M3-VERSION-001` |
| CC-CHANGE-006 | 当前无全量收集的资源与失败关闭闭环 | 按 OPEN-02 限额；资源超限、查询 / handoff / Provider / 输出失败时失败关闭，不截断、不创建完整或部分 Candidate、不推进 Current | `T-M3-DATA-003`；`TEST-DATA-004/005` |
| CC-CHANGE-007 | 分页一致性与 source freshness 易混淆 | 各页 / 关系在一个已验证 read view 内收集；receipt 单独记录完整性和 freshness；默认不二次全量查询 | `T-M3-DATA-004`；`TEST-DATA-006` |

## 6. 既有行为保留

| ID | 保留义务 | 依据 | 验证 |
|---|---|---|---|
| CC-PRESERVE-001 | 只扩展现有 `office` / `odoo_record_retriever`，不新增公开工具；调用数据仍经标准 ORM 和现有 Retriever 权限边界 | M3 TDD §§2、5、6、12；已关闭 CC-M3-01 | 冒烟 / 集成测试与权限断言 |
| CC-PRESERVE-002 | Excel 内容始终由 LLM + Hosted Code Interpreter 在 M2 Route B 生成 / 修改；本地不写内容，不改变 M2 通用 edit 路由 | TDD `TD-003`、`T-M3-DATA-002` | Route B 集成证据、代码审查、M2 回归 |
| CC-PRESERVE-003 | 新建和修改导出均登记可审阅 Candidate；保留 Candidate / Current / Accept / Reject / Finalize、版本 / SHA / Thread / user / Session 门禁 | `T-M3-VERSION-001`、M2 TDD | `TEST-LIFE-001` |
| CC-PRESERVE-004 | 原 Retriever 旧调用兼容；`discover/describe` 不授予业务读取权限；search / 关联按当前用户 ACL / Record Rules | CC-M3-01 v0.2；TDD `T-M3-SEC-001` | `TEST-REG-001` 及关系 ORM 权限测试 |
| CC-PRESERVE-005 | 不完整、不确定、超限或失败结果不标作完整；Accept 是用户决策；Finalize 交付已接受的同 SHA 文件 | M2 SRS / TDD；M3 TDD §§6、9、10 | `TEST-DATA-004/005`、`TEST-LIFE-001` |
| CC-PRESERVE-006 | 不默认 Accept 前二次全量查询；新鲜度与完整性分开；超限要求缩小范围，不使用 partial 流程 | TDD `T-M3-DATA-003/004` | `TEST-DATA-005/006` |

## 7. 适用的 TDD 防护栏

| TDD 防护栏 | 落实处 | 验收证据 |
|---|---|---|
| `T-M3-DATA-001` | deterministic collection、page guard、身份 / 关系对账及 handoff | `TEST-DATA-001/002/003` |
| `T-M3-DATA-002` | 真实 Hosted CI 产出 XLSX；本地只读验证 | `TEST-DATA-001/002`、`TEST-XLSX-001` |
| `T-M3-DATA-003` | 故障与预算边界 fail-closed，无完整 / partial Candidate | `TEST-DATA-004/005` |
| `T-M3-DATA-004` | receipt 分离 completeness 与 freshness；显式刷新另建 Candidate | `TEST-DATA-006` |
| `T-M3-VERSION-001` | 通过 M2 version service 建立 Candidate，禁止 fileless direct-V1 绕行 | `TEST-LIFE-001` |
| `T-M3-PRIV-001` | 仅传送最小、完整且获准外发的数据；不记录或缓存 payload | 代码审查、Route B 外发策略检查 |
| `T-M3-COMP-001` | 覆盖 M2 Route B、确认、版本与文件安全回归 | `TEST-REG-001` |

## 8. 实施行为与数据核验契约

1. Server collector 使用当前用户已确认的 query / table plan；所有 Retriever root 与 relation query 必须重用当前用户 ORM 环境和 §2 已验证的单事务 read view。
2. 分页每页不超过冻结 Retriever 契约允许的 500 条；按有限 page size、稳定 order、offset 与 `next_offset` 迭代。仅 `has_more=false` 可终止；`returned_count` / `records` 长度不符、无进展、重复 identity、count 或 scope 不符均失败关闭。
3. 针对直接关系，从 Registry Schema 校验关系字段；使用批量 `in` / 有界 chunk，子记录按当前用户权限重新读取，保留完整 parent-child identity pair。One2many 必须验证 inverse；Many2many 恢复所有父子对。不得把 display label 当身份。
4. 所有读取、relation 集合、handoff 与 Provider input 有界。没有通过 OPEN-02 定标并启用可信服务端限额时，不得实施 / 宣称可支持的最大规模。
5. 输出验证范围限于客观可证事项。`record_projection` 如用户要求逐条导出，可核对每个 source identity 恰好一次及选定字段值；复杂 `grouped_aggregate` 和 `semantic_transform` 由 LLM + Hosted CI 规划 / 计算，本地不重算、不实现报表 / 语义引擎。测试可对固定 synthetic fixture 使用预先算好的 expected constants 检查 Hosted CI 结果。不能独立验证的生产任务按 M2 `PARTIALLY_VERIFIED` / 用户审阅语义记录，不宣称 VERIFIED；source / handoff / 文件 / 版本完整性仍须满足。
6. Receipt 只含规范 scope / query digest、计数、身份与关系摘要、hand-off profile / bytes / SHA、输出验证、采集时间窗 / read view 与输出 SHA；不得保存完整业务数据、原始敏感 Domain 或 Provider prompt。
7. Current workbook 仅由服务端从当前 Thread / Session 的 Accepted Current 解析；核对其既有版本与 SHA。新建 workbook 也须 Candidate → 用户 Accept，不走 M2 fileless direct-V1 例外。
8. 只有 handoff 确认完整且外发许可、预算均通过，才可调用既有 Route B。Provider 超时 / 结果不确定不得盲目重试。Provider 输出必须是实际返回的真实 XLSX 字节；本地不生成、改写或修补 workbook 内容。
9. 任一阶段不完整、无法证明或超限：不得以成功 / 完整结果交付，不登记完整 Candidate，不更改 Current；返回稳定可诊断错误，必要时请用户缩小范围重新发起。

## 9. 权限、外部调用与数据库约束

- 所有源业务数据访问必须遵守当前用户 ORM ACL、Record Rules、字段权限、公司上下文；`sudo()`、SQL、提升权限环境或服务账号均禁止。
- Registry 仅校验 schema / 关系结构，不读取记录、不授予数据读取权。
- Hosted CI / Provider 的真实调用属于外部数据传输。本次文档冻结不授权调用；后续需按项目流程取得专项外发授权，且必须确认数据最小化与已有 M2 policy。
- 不创建或访问新数据库，不访问生产环境。后续获准运行 Odoo 测试时仅使用现有开发数据库 `odoo18e_llm` 和合成 fixture；事务测试回滚。运行前核对实际 Odoo process / 配置，禁止只依赖历史配置推断。
- 不修改 ACL / Record Rules，不进行源业务记录迁移或数据修改。若 TDD 要求的最小 receipt 字段需升级，须在正式 CC 授权后仅对既有 `odoo18e_llm` 执行，记录升级、验证及回滚信息。

## 10. 测试契约

| 测试 ID | 覆盖 | 测试方法与关键断言 | 证据状态 |
|---|---|---|---|
| `TEST-DATA-001` | 148 条跨两页完整导出 | 合成 148 identities、page size 100；真实 Hosted CI 载荷读取；source / handoff count 与 digest 一致；XLSX 的每个 identity 恰好一次，字段符合任务映射；输出 SHA 与 Candidate receipt 一致 | Planned / NOT RUN |
| `TEST-DATA-002` | 更大且仍在预算内的数据集 | 超过两页的合成数据；同机制无静默截断；超 provider / payload 限制返回有诊断失败且没有 Candidate | Planned / NOT RUN |
| `TEST-DATA-003` | 多父直接关联批量读取 | 多个 parent，包含多条与零 child；覆盖所用 Many2one / One2many / Many2many 直接关系；按 `in` / bounded chunks 查询，断言所有 parent-child pairs、无丢失 / 误连、无逐父 N+1 | Planned / NOT RUN |
| `TEST-DATA-004` | 失败关闭 | page error、计数 / scope drift、重复 ID、漏 relation / inverse、handoff digest mismatch、Provider output 缺失或验证失败；均不建完整 Candidate、不改 Current / Last Valid / Document Revision | Planned / NOT RUN |
| `TEST-DATA-005` | 资源上限 | 对 root / relation rows、payload bytes、Provider input / output 和 wall-clock 边界注入或实测超限；用户获知可收窄范围；无截断、无 Partial Candidate | Planned / NOT RUN |
| `TEST-DATA-006` | 单一读视图与 freshness | 隔离事务在分页中并发 insert / update / delete；证明本次收集页与关系在同一 REPEATABLE READ read view；receipt 记录 freshness；Accept 前无默认全量二次扫描 | Planned / NOT RUN |
| `TEST-XLSX-001` | 客观数据 / 文件 / 版本完整性及任务验证等级 | Projection 与 Hosted CI 聚合 / 语义转换；覆盖重复值、null / false / 0、Selection、relation；核对 identity / 指定字段；固定 synthetic fixture 可断言预期常量，生产不本地重算；复杂计算不可独立验证时使用 M2 `PARTIALLY_VERIFIED` / 用户审阅语义；handoff / 文件 / SHA / 版本仍核验 | Planned / NOT RUN |
| `TEST-LIFE-001` | Candidate 生命周期 | 新建与 current edit 均成为完整 Candidate；Candidate 前 Current 不变；Accept 仅推进已核验 Candidate；Reject 不改 pointers；Finalize 交付 Accepted Current 同 SHA；版本 / 用户 / Thread / Session 绑定生效 | Planned / NOT RUN |
| `TEST-REG-001` | M2 / Retriever 回归 | Retriever 旧调用，M1 mapping、Route B、version / confirmation / file-security 定向回归；报告真实选择集，不扩称全套测试通过 | Planned / NOT RUN |

除纯单元 / TransactionCase 外，真实 Hosted CI / Route B 的输入可读性和真实 XLSX 输出属于必要集成证据，不能由 Mock 替代；每次真实 Provider 调用须在执行前取得单独授权。所有测试使用合成数据并只触及现有 `odoo18e_llm`，不访问生产。

## 11. 验收证据与交付物

每项测试在 ATR 中保留 native `PASS / FAIL / BLOCKED / NOT RUN`、实际命令 / 运行路径、代码 / addon / Odoo runtime / 目标数据库身份、输入规模、结果与证据文件。真实 Hosted CI 证据保留 Provider / model / transport profile、请求 lineage、handoff count / digest、Hosted CI 实际读取结果和下载 XLSX 字节 / SHA；敏感凭据和不必要的业务内容不得记录。

交付物：下游 addon 实施、测试与依赖注册；IHR；完整 ATR / Route B 合成数据集成证据； Candidate receipt / 文件核验记录；Final Report。CC-M3-02 不生成最终 Agent UI HVR；HVR 在 CC-M3-03 执行。

## 12. 停止条件

| 触发情况 | 处置 |
|---|---|
| 任一 OPEN-01b/02/03/04 前置 Spike 缺少最小可行性证据 | 不开始实施；补充对应 Spike。实施测试尚未运行不阻止本 CC 设计稿评审 / 冻结，但必须按完成定义在 CC 内完成 |
| Hosted CI 无可用方式完整接收 bounded handoff | 停止，返回 TDD 版本化评审；不得改上游、增加 Adapter 或换本地 writer |
| 当前业务用户权限、公司隔离或数据外发许可不足 | 拒绝该范围；不得提权或绕过；按最小权限重新确认任务 |
| 不同页 / relation 无法保证同一读视图 | 停止完整性承诺，回 OPEN-03 / TDD 评审 |
| profile 无法证明用户要求的完整结果 | 不标 VERIFIED / 完整；按 TDD 返回失败或既有 M2 审阅级别 |
| 任一资源、传输、Provider、文件或验证边界超限 / 不确定 | Fail closed；无完整 / Partial Candidate；不推进 Current |
| 要求修改 `odoo-llm`、`office_engine_m2`、业务模型专用规则或新增工具 | 停止并作范围 / TDD 影响评审，不直接扩大 |
| 目标为新数据库、生产环境或真实业务数据测试 | 不执行；本 CC 测试仅限现有开发库 `odoo18e_llm` 的 synthetic fixtures |
| M2 Candidate / confirmation / file-security 行为需改变 | 停止，退回适用的上游 SRS / TDD 评审 |

## 13. 完成定义

1. 本 CC 正式冻结并已获得独立 Coding Authorization；实施前 OPEN-01b/02/03/04 的最小技术可行性 Spike 均有可复核证据。Spike 只证明可行，不替代实施验收。
2. 所有源查询自动分页、身份去重 / completeness 核验与 direct relation batch 行为按 TDD 契约通过；148 条数据以 100 + 48 完整经过 source → handoff → Hosted CI → workbook，identity 恰好一次且字段值 / relation 核验通过；更大的有界集同样不静默截断。
3. 经批准的 transport profile 被 Hosted CI 真实读取；源 / handoff identity 与计数相符；projection 输出按要求核对身份 / 字段；复杂聚合 / 语义由 Hosted CI 计算，已知 fixture 测试可用常量断言但不形成运行时引擎；不可独立验证的语义如实标为 M2 `PARTIALLY_VERIFIED` / 用户审阅。文件字节 / 结构 / SHA 与版本绑定检查通过。
4. 失败注入、资源上限、同一 read view、用户 ORM 权限及 freshness 边界满足要求；任何不完整 / 超限路径均不建完整或部分 Candidate，不改 Current。
5. 新建 / 修改 Route B 都由 LLM + Hosted CI 生成 XLSX；Candidate / Accept / Reject / Finalize、M2 版本 / 用户确认门禁与定向 M2 回归通过；无本地 Excel 内容 writer。
6. IHR、ATR、FR 绑定准确的实现提交和测试证据；CC 范围无未解决阻塞项。Final UI / Agent HVR 仍归 CC-M3-03，不作为本 CC 的证据替代。

## 14. 双向追溯

| 上游来源 | 本 CC 条目 | 验证 |
|---|---|---|
| `API-OFFICE-EXPORT-001` | CC-CHANGE-004、CC-PRESERVE-001–003 | `TEST-DATA-001/002`、`TEST-LIFE-001` |
| `API-HANDOFF-001` | CC-CHANGE-003、CC-CHANGE-006 | `TEST-DATA-001/002/004/005` |
| `API-EXPORT-RECEIPT-001` | CC-CHANGE-005、CC-CHANGE-007 | `TEST-DATA-001/006` |
| `T-M3-DATA-001/002/003/004` | CC-CHANGE-001–007 | `TEST-DATA-001`–`006`、`TEST-XLSX-001` |
| `T-M3-VERSION-001` | CC-CHANGE-005、CC-PRESERVE-003/005 | `TEST-LIFE-001` |
| `T-M3-PRIV-001` / `T-M3-COMP-001` | §9、CC-PRESERVE-001/002/004 | 权限集成测试、`TEST-REG-001` |
| Frozen Plan v0.3 §4 / §6 / §13 | 全部本 CC 条目 | 自动化 / 集成测试、ATR、FR |

## 15. 版本记录

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-13 | 基于冻结 M3 TDD v0.3 与 Implementation Plan v0.2 起草；未含实现授权 | Draft — 历史草案 |
| v0.2 | 2026-11-13 | 明确 LLM 业务规划与通用 Collector 执行边界；收紧本地核验为客观完整性；拆分 OPEN-01b/02/03/04 最小前置 Spike 与实施验收；依据冻结 TDD v0.4 / Plan v0.3；保持 Route B 与 M2 Candidate 生命周期不变 | FROZEN WITH OPEN GATES；未授权实施 |

