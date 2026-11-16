<!--
Template source: office_engine/docs/skill/odoo-project-workflow/references/templates/Coding/Coding_Contract模板.md
Template version/status: v1.0.0 Frozen
Template synchronization check: PASS (2026-11-16; --repo-root office_engine)
-->

# CC-M3-03 — Silent Retrieval + Final HVR v0.2

| 项目 | 内容 |
|---|---|
| CC | `CC-M3-03` |
| 版本 | v0.2 |
| 状态 | **FROZEN WITH OPEN ITEMS — 本轮范围 / 验收已冻结；实施已授权** |
| 计划阶段 | M3 Implementation Plan v0.3 / CC-M3-03 |
| 技术基线 | M3 TDD v0.4（`TDD-M3-003`） |
| 计划基线 | Implementation Plan v0.3（`PLAN-M3-003`） |
| 前置 CC | CC-M3-01、CC-M3-02：均已验收、关闭并推送 |
| 目标模块 | `office_engine_m3` 下游 addon；保留既有 M2 / 上游边界 |
| HVR 数据库 | 仅现有开发数据库 `odoo18e_llm`；不创建数据库、不访问生产环境 |
| 冻结 / 授权记录 | `CC-M3-03-001`；同一负责人决定冻结本 CC 并授权 §5 全部实施、开发库、Provider / Hosted CI、HVR 与 Git 范围 |

> 负责人于 2026-11-16 明确指示“冻结cc-03,进入实施”。该指示依据本 CC v0.2 完整范围，经办为一次合并冻结及实施授权：同一记录覆盖 §5 所列开发、现有开发数据库、真实 Provider / Hosted Code Interpreter、Odoo UI HVR 和 Git 工作，无须对范围内各步骤重复申请。TDD v0.4、Plan v0.3、M2 / M3 既有行为均未改动。

Freeze disposition: `FROZEN WITH OPEN ITEMS`; authorization register: `docs/implementation/AUTHORIZATION_RECORDS.md`; record: `CC-M3-03-001`.

## 0. 文档治理与范围决策

- 本文 v0.2 已冻结；实施授权与范围由 `CC-M3-03-001` 记录。只有该 CC 范围取得授权，不扩大任何上游设计或业务权限。
- 本轮 Silent Retrieval 的正式保证范围是项目当前可用的非流式 Office Agent 路径。既有临时扩展 / Mock tool call / ORM TV 只证明有限子路径，不代替本 CC 对实际运行路径的完整验收。
- 流式路径只验收安全可见边界：不隐藏 assistant tool-call、续接消息、错误或未执行状态；本 CC 不要求修复上游 generator 返回值续接，也不把流式路径纳入静默承诺。不得修改上游 `odoo-llm`。
- TDD v0.4 的消息可见性与审计约束保持原样：只有成功纯 Retriever 内部消息可静默；错误、澄清、最终回答、Office 操作、用户确认及含非 Retriever 工具的混合 assistant 消息必须可见；静默消息、参数、结果、上下文与诊断仍保留。
- Bus / SSE / Discuss 仅围绕本轮实际非流式 UI 对话路径及其实际订阅入口验证。保留 TDD 对实际默认和显式 Bus 订阅入口的要求，不扩展到当前运行路径未使用的订阅者组合。

## 1. 目标

在真实 Odoo UI 中验证：Agent 基于用户自然语言，自主发现现有业务模型、选择字段、确定关联关系并组织 Retriever 与 Office Tool Calling；完整的 148 条出库订单及其产品明细经现有 CC-M3-01/02 能力交给 Hosted Code Interpreter 生成 XLSX；成功 Retriever 探索不刷屏且审计完整；用户明确 Accept 后 Finalize；独立检查下载文件的身份、字段、父子关系及 SHA。

验收由当前可用的非流式路径完成完整 Silent Retrieval 和端到端 HVR；流式路径按本契约确认其消息仍安全可见，不要求其静默或修复已知续接问题。

## 2. 上游基线与追溯

| 来源 | 版本 / 状态 | 本 CC 追溯 |
|---|---|---|
| M3 TDD | v0.4 Frozen with Open Items / `TDD-M3-003` | §13、§14、§17；`T-M3-MSG-001/002/003`、`T-M3-PRIV-001`、`TEST-SILENT-001`–`005`、`TEST-HVR-001`、`TEST-REG-001` |
| M3 Implementation Plan | v0.3 Frozen with Open Items / `PLAN-M3-003` | §4 CC-M3-03、§5、§6–8；OPEN-06 按本 CC 声称静默的非流式路径验收 |
| CC-M3-01 | 已验收、关闭并推送 | 通用 Registry / Retriever 能力和旧调用兼容 |
| CC-M3-02 | 已验收、正式关闭并推送 | 自动分页、完整关系收集、Hosted CI handoff、XLSX 核验和 Candidate 生命周期 |
| M2 SRS / TDD | 已冻结 | Route B、消息、文件、安全、版本及用户确认语义保持不变 |
| M3 SRS / DDD | N/A | 遵循负责人已记录决定；本 CC 不增加新业务语义 |

## 3. 范围

### 3.1 本轮工作

1. **非流式静默验收：** 针对实际运行的非流式 Office Agent 路径，验证成功纯 Retriever assistant/tool 消息在首次 Bus 通知前完成分类；用户 SSE 与 Discuss 历史不显示成功内部探索 / 查询消息。消息仍保留在 `mail.message`、工具调用与结果记录、LLM 后续上下文、tool events、执行状态和诊断中。
2. **实际消息路径：** 按真实 UI 会话覆盖其实际 SSE `message_create/update`、Discuss 历史读取及 Bus 通知。对该路径实际使用的默认订阅及 TDD 要求的显式订阅入口分别验证首次 notify 前的可见性；不构造与本轮运行无关的订阅者矩阵。
3. **可见性与审计：** 成功零结果仍保持成功语义；ACL / 查询错误、必要澄清、最终回答、Office 操作、Candidate、Accept / Reject / Finalize 和用户确认必须可见。混合 assistant 消息只要包含 Retriever 以外工具，整条 assistant 消息必须可见。不得删除或截断原消息及审计信息。
4. **流式安全边界：** 验证流式消息不会被静默过滤；tool-call、续接、错误或未执行状态保持可见。既有 generator return-value 问题作为已知限制记录，本 CC 不修复上游、不要求流式完成静默验收，也不将其报告为已通过。
5. **真实 Agent HVR：** 使用现有 `world.depot.outbound.order` 及 `world.depot.outbound.order.product` 业务模型，在 `odoo18e_llm` 准备 148 条合成出库订单和关联明细。用户以业务语言提出任务；Agent 自主发现模型、字段与关系，决定查询范围，并自行编排现有 Retriever / Office Tool Calling。测试程序只准备 fixture 和独立预期数据，**不得向 Agent 或工具调用预置技术模型名、字段名、Domain、查询计划、Collector 参数、列映射或工具调用序列**。
6. **文件独立核验：** 对 Candidate 和 Finalize 后下载的实际 XLSX 分别独立读取：核对 148 个源订单身份无遗漏、无重复；订单号、Reference、日期等用户要求字段及其值正确；产品明细与产品、数量等预期字段正确；每条明细准确归属其父订单；Candidate、receipt 和最终交付 XLSX 原始字节 SHA 相符，且文件可重新打开。
7. **回归与交付：** 执行本 CC 自动化、实际路径消息测试、M2 生命周期 / 文件 / 安全以及 CC-M3-01 Retriever 定向回归；记录 IHR、ATR、HVR 和 Final Report。

### 3.2 范围外

- 修改冻结 TDD v0.4、Plan v0.3、M2 或 M3 既有行为；修改上游 `odoo-llm` 或修复流式 generator 续接。
- 在本轮非流式路径以外承诺 Silent Retrieval；扩展当前真实 UI 路径未使用的 Bus / SSE / Discuss 组合。
- 新增公开工具、本地 XLSX Writer、报表 / 计算引擎或 Partial Candidate；变更 CC-M3-02 的完整收集、handoff 或 Candidate 实现。
- 用 Mock Agent / 预设 tool calls、预建 Query Plan、固定技术参数或预选列布局代替真实 Agent 自主决策及 HVR。
- 新建数据库、访问生产环境、直接 SQL/RPC 读取或修改业务数据、使用非合成客户数据。
- 合并、部署或发布。

## 4. 变更与保留契约

| ID | 要求 | 验收依据 |
|---|---|---|
| `CC-CHANGE-001` | 实际非流式 Office 路径下，成功纯 Retriever 消息在首次通知前标记；不进入用户 SSE / Discuss / Bus 可见消息 | `TEST-SILENT-001/004`、实际 UI 运行证据 |
| `CC-CHANGE-002` | 在真实会话中验证错误、零结果、澄清、final、Office / Candidate / 确认以及 mixed tool-call 的 TDD 可见边界 | `TEST-SILENT-002/003`、HVR |
| `CC-CHANGE-003` | 流式路径保持工具续接与失败状态安全可见；记录已知 generator 限制，不要求修复 | `TEST-SILENT-005`、路径记录 |
| `CC-CHANGE-004` | Agent 自主完成真实业务模型发现、字段选择、关系确定及 Retriever / Office 工具编排 | `TEST-HVR-001` 的真实 Agent tool trace 和自然语言 UI 记录 |
| `CC-CHANGE-005` | 148 条出库单及明细完整生成 Candidate；Accept / Finalize 后，独立核验实际下载 XLSX 的身份、字段、父子关系和 SHA | `TEST-HVR-001` 的独立 XLSX 核验记录 |
| `CC-CHANGE-006` | 完成定向自动化 / 集成回归并保存可追溯的本 CC 证据与结项记录 | 单一测试矩阵、ATR / HVR / IHR / FR |
| `CC-PRESERVE-001` | 隐藏仅影响用户可见面；原始消息、参数、结果、上下文、执行状态、tool events 与诊断完整保留 | `TEST-SILENT-001/002` |
| `CC-PRESERVE-002` | M2 Candidate、Current、Accept / Reject / Finalize、版本、文件安全和用户确认门禁不变 | `TEST-HVR-001`、`TEST-REG-001` |
| `CC-PRESERVE-003` | 业务数据访问遵守当前用户 ORM / ACL / Record Rules；不使用 `sudo()`；实现不得硬编码 WMS 模型或字段 | 定向回归与变更审查 |
| `CC-PRESERVE-004` | 保留单一 Retriever、单一 Office Tool、M2 Route B 和 LLM + Hosted CI 文件内容生成 | 变更审查、`TEST-REG-001` |

## 5. 一次性实施与验证授权边界

负责人在同一授权决定中批准冻结本 CC，并于冻结生效后一次性授权以下范围；无需对其中每个步骤、Provider 调用或 HVR 操作逐项再次申请：

- 在 `office_engine_m3` 下游范围编码、修复、运行自动化 / 集成测试并记录结果；
- 只使用现有开发数据库 `odoo18e_llm`，通过获准的 Odoo ORM / 测试准备及清理 148 条合成出库订单和关联明细；不得新建数据库或访问生产；
- 在遵守既有 M2 数据外发政策的前提下，将本契约限定的合成数据发送到指定真实 Provider / Hosted Code Interpreter，以完成非流式 Agent / XLSX 验收；该授权不改变或豁免 M2 外发政策；
- 在已登录 Odoo 开发 UI 中完成自然语言任务、查看 Candidate、明确 Accept、Finalize、下载及文件独立核验；
- 运行本 CC 定向回归，维护 IHR / ATR / HVR / FR，并按项目 Git 流程提交和推送 CC-M3-03 范围成果。

单一授权记录至少标明负责人、日期、CC 版本、开发数据库 `odoo18e_llm`、真实 Provider / Hosted CI 外发范围仅限本 CC 合成数据、内置浏览器 Odoo UI HVR，以及上述开发 / 测试 / 清理 / 证据 / Git 范围。授权后，在此边界内按正常失败修复与重测推进，不逐次请求同一授权。若发现必须改变冻结 TDD/Plan、访问其他数据库 / 生产数据或超出上述 Provider 数据范围，暂停受影响工作并按变更治理处理。

## 6. 测试与证据矩阵

本矩阵是本 CC 唯一的测试清单；HVR 的数据、执行和结果细节统一记录于 `HVR-M3-03-001`，不在多个测试表重复抄写。下列本 CC 项均尚未执行：原生状态 `NOT RUN`、Workflow Evidence Status `Missing`。此前局部 TV 不作为本 CC 的完整通过证据。

| 测试 ID | 范围与判定 | 状态 |
|---|---|---|
| `TEST-SILENT-001` | 实际非流式会话内多次成功纯 Retriever 调用：用户 SSE / Discuss 隐藏；原始 `mail.message`、工具参数 / 结果 / 状态、context、tool events 与诊断保留 | NOT RUN / Missing |
| `TEST-SILENT-002` | 同实际会话中的 ACL / 查询错误、成功零结果、必要澄清和 final：错误 / 澄清 / final 可见；零结果保持成功语义；失败不被先前静默标记吞掉 | NOT RUN / Missing |
| `TEST-SILENT-003` | 实际 mixed assistant message 含 Retriever 与 Office / 其他工具：整条 assistant 消息可见，工具链不被静默逻辑截断 | NOT RUN / Missing |
| `TEST-SILENT-004` | 实际 UI 路径的 SSE / Discuss 历史与 Bus：首次 notify 前生效；验证 TDD 指定的默认及显式订阅入口，不扩展到无关 subscriber 组合 | NOT RUN / Missing |
| `TEST-SILENT-005` | 流式边界：工具调用、续接和失败仍安全可见；不要求修复 generator 或证明流式静默 | NOT RUN / Missing；既有 TV 记录 generator return-value 限制 |
| `TEST-HVR-001` | 按 §7 的真实非流式 Agent UI → Retriever → Office / Hosted CI → Candidate → Accept → Finalize → 下载文件核验；Agent 参数必须自主形成 | NOT RUN / Missing |
| `TEST-REG-001` | M2 Route B、Candidate 生命周期、版本 / 文件 / 确认安全和 CC-M3-01 旧 Retriever 定向回归 | NOT RUN / Missing |

测试通过必须绑定本 CC 实际代码提交和原始日志 / HVR 记录。Mock、单独 ORM 测试、工具参数预设、Provider 独立生成文件或主页截图均不能替代 `TEST-HVR-001`。

## 7. 最终真实 Agent HVR — `HVR-M3-03-001`

### 7.1 Fixture 和 Agent 自主性

- 在现有真实业务模型 `world.depot.outbound.order` 中准备 **148 条合成出库订单**，并通过真实关联模型 `world.depot.outbound.order.product` 准备带父订单关系的产品明细。使用可识别的合成批次 / 项目标记；fixture 只能设定数据和独立预期集，不得预置给 Agent 的技术查询参数。
- 通过现有 ORM / 项目授权测试准备方式建数，保存 source order identity 集合、字段期望值、逐订单 product/quantity 明细及父子映射，供任务后独立比对。不得通过 SQL/RPC 操作业务数据。实施 / HVR 后按授权范围用 ORM 清理合成 fixture。
- 用户只用自然语言表达业务范围和所需业务内容，例如“请导出验收项目下的全部出库单，包含订单号、Reference、日期及每单的产品和数量”。提示不得出现模型技术名、字段技术名、Domain、分页值、集合计划、工具名、工具参数或预先组织的 Retriever / Office 调用顺序。
- HVR 不得使用 mock LLM、mock tool call、录制参数回放或测试 hook 注入 query plan。Agent 必须在实际会话中自行发现模型、选择相应字段、确定订单与产品明细的关联关系，并自主组织现有 `odoo_record_retriever` 和 Office Tool Calling。测试程序只在执行后读取调用记录作证，不得预先提供其参数。
- 环境可以选择本轮实际可用的非流式 Provider / 路由；该环境选择不等于向 Agent 预置业务模型、字段或查询计划。记录实际 Provider、路由形态、工具调用与响应关联 ID。

### 7.2 用户可见与消息证据

在登录后的真实 Odoo UI 观察本轮实际会话：成功纯 Retriever 探索及分页不产生冗余用户可见消息；错误、必要澄清、最终答复、Office/Candidate 操作及 Accept 确认正常显示。SSE、Discuss 历史和实际 Bus 通知按 §6 对同一真实运行路径核对；内部消息和审计数据仍可从授权的应用 / 测试记录中追踪。记录流式边界的实际可见性，但不要求流式任务成功运行，也不宣称该路径静默。

### 7.3 Candidate 与最终 XLSX 独立核验

1. Agent 输出 Candidate 后，保存 Candidate 标识、版本 / receipt、文件名及 XLSX 原始字节 SHA；在 UI 中展示必要的确认信息。
2. 人工在 Odoo 页面明确 Accept，再依 M2 既有流程 Finalize 并下载交付文件。Acceptance 前不得推进 Current；Finalize 文件必须是已接受 Candidate。
3. 使用独立 XLSX 读取方式核验 Candidate 与最终下载文件：文件可打开；148 个源订单 identity 全部恰好出现一次且无额外订单；用户要求的订单号、Reference、日期等字段值匹配；每笔订单的产品明细和值均正确，并准确映射到对应父订单；无遗漏、重复、跨父订单串线或错误值。
4. 计算并记录 Candidate XLSX、receipt 绑定文件及 Finalize 下载文件的 SHA-256；Candidate 与最终交付文件字节 SHA 必须一致。source identities、预期字段和值、关系 pair 集合、输出核验及各 SHA 分开记录，不以一个 digest 替代全部检查。
5. 保存对话输入、实际 Provider / 路由、Retriever 与 Office 调用 trace、必要的 SSE/Discuss/Bus 观察、Candidate / Accept / Finalize 页面结果及独立文件检查记录；避免在报告中写入密钥或无关敏感信息。

### 7.4 HVR 判定

`PASS` 要求 7.1–7.3 全部满足，包含真实自然语言自主规划、148 条及全部请求关系完整、消息可见性和审计正确、明确 Accept / Finalize、文件 SHA 一致。任何一项失败或缺证均为 HVR 未通过；不得以人工摘要、Candidate 存在、文件行数、模拟调用或用户授权代替验证结果。

## 8. 完成条件

- §6 所列适用自动化 / 集成回归通过；§7 `HVR-M3-03-001` 为 PASS。
- `CC-CHANGE`、`CC-PRESERVE` 与适用 TDD Guardrail 均逐项绑定本次实现基线和证据；静默保证严格限于实际验收通过的非流式路径。
- IHR、ATR、HVR、Final Report 完整记录环境、Provider / Hosted CI、数据处理、UI、文件 SHA 和所有失败 / 重试结果；不把流式边界误记为通过。
- 由负责人完成关闭评审后，按授权精确提交并推送本 CC 文件；本 CC 冻结 / 实施授权均不等同于合并、部署或发布批准。

## 9. 冻结与实施授权

负责人于 2026-11-16 明确批准冻结 CC-M3-03 v0.2 并进入实施。详细授权人、依据、开发库、数据外发和 Git 边界见 `CC-M3-03-001`。TDD / Plan 既有 OPEN 项及本 CC 尚未执行的测试仍保持原状态，必须按本 CC 完成并留证；本冻结不宣称任何测试 Passed，不授权合并、部署或发布。

## 10. 文档历史

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| v0.1 | 2026-11-16 | Superseded Draft | 首版评审稿，保留原文件，不作为当前待审版本 |
| v0.2 | 2026-11-16 | FROZEN WITH OPEN ITEMS | 聚焦已可用非流式路径；流式仅验证安全可见；以 148 条真实模型合成订单和关联明细完成 Agent 自主 HVR；同一条授权记录覆盖开发、开发库、Provider、Hosted CI、HVR 与 Git；负责人批准后冻结并进入实施 |
