# Office Engine M4 — 根因调查汇总

**状态：** RCA-001～008 汇总评审于 2026-11-17 关闭（截至该日未实施修复）；RCA-004、006、007、008 保持原未验证状态。CC-M4-02 后续证据见文末追加节。  
**调查计划：** [M4_RCA_Plan_v0.1.md](M4_RCA_Plan_v0.1.md)，用户批准冻结 2026-11-17  
**基线代码：** `8f7ebd259cda414baae46fa91b1d55948ba481a0`（`docs(office-engine): close CC-M3-03`）  
**设计基线：** M3 TDD v0.4 / `TDD-M3-003`；M3 Implementation Plan v0.3 / `PLAN-M3-003`；CC-M3-01/02/03 v0.2。冻结文档及 CC-M3-02 兼容性 Addendum 均未改写。

## 执行与复现配置

历史 TV Thread 的 Provider 原始 HTTP 请求体未持久化。本轮使用 Odoo UI 建立诊断 Thread 826，在发送前确认 Provider `OpenAI GPT-5.6 Luna`、model `gpt-5.6-luna`，并勾选 `odoo_record_retriever` 和 `office`；ORM 发送后核对 Thread 配置。该复现仅提交原始 TV-13 类型需求，没有提供模型名、字段、Domain 或查询答案。

诊断结果：两次搜索路径之前的 Registry discovery 返回空；Agent 仍尝试 project 模糊 `search` 和标准 `stock.picking`，后两次查询结果分别为 25 个项目记录和 0 张 stock picking。Agent 最终称当前用户可见的出库订单中无该项目记录，没有调用 Office、创建 Candidate 或生成文件。使用当前 UI 用户的只读 ORM 复核显示项目 ID 29 实际有 137 张自定义出库订单和 340 条明细。因此该回答是假阴性，不能算 E2E 通过。

**数据库边界：** 只使用现有开发库 `odoo18e_llm`；业务数据通过当前用户 ORM 查询（`env.su=False`）；没有 SQL、RPC、生产环境访问、代码 / Prompt / TV 标准修改。

## 八项 RCA 状态

| RCA | 关联缺陷 | 结论 | 核心证据 |
|---|---|---|---|
| 001 工具调用 | DEF-M4-002 | 部分确认 | 多个失败 Thread `tool_ids=[]` / 零调用，不能证明 Agent 在工具可用时拒绝；TV-02 Thread797 实际有 7 次 Retriever 调用；Thread826 正确选工具后也实际调用 Retriever。 |
| 002 模型发现 | DEF-M4-001 | 部分确认 | Registry discovery 是 `_name` / `_description` 的字面子串匹配；中文、长英文查询均为空，Agent 未遵循短语重试 / describe 指引，猜测 `sale.order` / `stock.picking`。 |
| 003 查询条件 | DEF-M4-003 | 已确认 | Thread796 的 395 条查询漏掉项目 Domain；Thread826 把 `query` 用在 `search` 而未带 Domain，Schema 接受但实现忽略 `query`。 |
| 004 歧义澄清 | DEF-M4-008 | 未确认 / 前置阻断 | TV-05 / 15 先遇到模型选择错误；TV-10 工具未绑定，未建立能独立测试“客户”含义的有效业务上下文。 |
| 005 Office / 确认 | DEF-M4-004 | 路由根因已确认；Accept 子流程未触达 | Thread794 用 M2 `create` 直发 fileless V1；实物只有表头和“未检索成功”说明，没有业务行；不是 `export_records`，没有 Candidate / Accept。 |
| 006 文件上下文 | DEF-M4-005 | 未确认 / 前置依赖 | 三个 TV-18 在没有有效 Current 时执行 edit；Thread811 是 TV-19 之后才创建版本。错误为 `A current Office workbook upload is unavailable.` |
| 007 聚合 | DEF-M4-006 | 未触达 | Thread811 是空明细表 + 公式模板；824 查询 0；825 查询错误 / discovery 空；没有有效数据 handoff 或 export_records。 |
| 008 重新查询 / 版本 | DEF-M4-007 | 未触达 | TV-20 查询未找到正确数据，没有任何 Office 写版本调用；M2/M3 版本机制没有被实际验证。 |

细节见各独立记录：`RCA-001_Tool_Invocation.md` 至 `RCA-008_Requery_Versioning.md`。

## TV-01～TV-20 覆盖归类

原始 TV 结果继续全部记为 FAIL；下表归类失败时最早可证实的环节，不把能力未触达的失败当成该能力的根因证据。

| TV | 样本与当前调查归类 |
|---|---|
| 01 | Thread796 首次搜索漏项目条件、返回 395；其重复 Thread812–814、823 没有绑定工具 / 调用记录。查询规划问题确认；其它重复项不能证明 Agent 工具能力。 |
| 02 | Thread797 实际有 Retriever / Office 且调用 Retriever 7 次，未调用 Office；报告称“无工具调用”不准确。M3 Office route 未激活，查询模型选择错误。 |
| 03 | Thread799 工具未绑定且无调用；只确认前置暴露不足，不能归因 Agent 查询能力。 |
| 04 | Thread800 工具未绑定且无调用；同上。 |
| 05 | Thread801 调用一次错误方向的销售订单查询，0 条；模型发现未成功，客户歧义未独立触达。 |
| 06 | Threads802、815、816 工具未绑定 / 无调用；产品明细聚合未触达。 |
| 07 | Threads803、817、818 工具未绑定 / 无调用；父子关联展开未触达。 |
| 08 | Thread804 工具未绑定 / 无调用；未形成可归因的查询轨迹。 |
| 09 | Thread805 工具未绑定 / 无调用；未触达订单 / 明细查询。 |
| 10 | Threads806、819、820 工具未绑定 / 无调用；歧义及统计未触达。 |
| 11 | Thread807 工具未绑定 / 无调用；月度统计未触达。 |
| 12 | Thread808 工具未绑定 / 无调用；排名 / 明细未触达。 |
| 13 | Thread794 两次 discovery 为空后误用 `office(create)`；生成说明性表头文件并直接 finalized，非数据导出。 |
| 14 | Thread809 工具未绑定 / 无调用；工作表创建未触达。 |
| 15 | Thread810 销售订单方向查询 0 条；正确模型未发现，公式 / Excel 生成未触达。 |
| 16 | Threads795、821、822 工具未绑定 / 无调用；完整查询未触达。 |
| 17 | Threads811、824、825 首轮未得到有效检索结果或工作簿。后续 Thread 有 Retriever / Office 调用；不能把“首轮不调用”归因成该线程从未绑定工具。 |
| 18 | Threads811、824、825 在没有有效 Current 的情况下调用 `edit`，均因当前工作簿不可用失败；这是 TV-17 的依赖失败。 |
| 19 | Thread811 生成无源数据模板；824 查到 0；825 `INVALID_QUERY` 后 discovery 为空。没有进入基于 Odoo 数据的聚合。 |
| 20 | 811 搜索标准 `stock.picking` 得 0；824 discovery 空；825 query 错误、discovery 空。没有 Office 版本写入，不证明版本服务故障。 |

## 已确认的共性根因与链式依赖

1. **TV 执行前置条件没有稳定记录。** 多个 Thread 没有工具绑定记录，原报告却统称 Retriever / Office 已配置；历史 outbound Provider payload 不可取，不能事后还原每个 Thread 的确切 UI 选择。
2. **业务词到 Registry 词面不匹配。** Registry 描述为英文 `Outbound Order`，discovery 只有子串查找；Agent 未按 M3 指令把查询缩短并重试 / describe，随后猜标准模型。
3. **筛选计划有漏项，工具接口会静默忽略 query。** Thread796 缺项目 Domain 是 Agent 计划错误；Thread826 的 `search(query=...)` 暴露 Retriever Schema / 分发器未按操作约束参数的问题。
4. **数据导出路由可被误选。** Thread794 使用 M2 fileless `create`，不经过 M3 export Candidate / Accept；M2 直接 V1 是既有空白工作簿路径，但 Agent 把数据导出请求路由到该路径。
5. **TV-17 的上游失败阻断后续独立验证。** TV-18 没有可编辑版本；TV-19 未获得源数据；TV-20 未进入 Office / 版本更新。三者不能被计成文件上下文、Hosted CI 聚合和版本服务的独立缺陷证据。

## 尚未确认的问题

- Provider 历史请求 schema、完整 system prompt 和本轮之外的 UI 预选记录没有持久化；不能证明每个无工具 Thread 的确切 outbound payload。
- 不能确认“客户”歧义处理、Hosted CI 在完整源数据上的聚合正确性、Candidate→Accept→Finalize、TV-20 新版本和旧版本保留。
- 当前用例不能区分 discovery 的语言覆盖缺口与模型不遵守重试指令各自的相对影响。

## 候选针对性 TV（不代表方案决策）

1. **工具暴露审计 TV：** 在 UI 发送前记录 Provider、model、工具勾选、Thread 持久化 `tool_ids` 及请求 schema，避免出现“配置了工具”的无证据结论。
2. **Discovery TV：** 用未给技术模型答案的中英业务词，分别检验短词重试、Registry 描述候选及跨语言模型发现；先验证失败边界再确定后续设计。
3. **Domain TV：** 对 `search(query=...)` 的静默忽略边界建立测试，验证 operation-specific Schema / 输入拒绝，并检验 Agent 对项目、日期、状态完整传递。
4. **导出门禁 TV：** 模拟 Agent 把有 Odoo 数据需求的任务误发 `create`；验证是否需要通用服务端拒绝、改道或澄清。空白 XLSX 继续走既有 M2 行为。
5. **能力隔离 TV：** 先完成一次有效的 Retriever → Export Candidate → 用户 Accept → Finalize，再分别测试歧义、关系完整性、附件长上下文和重新查询产生新版本。

## 修改 / 评审边界

本次新增 RCA 与汇总文档以保留分析，不改业务代码、Prompt、冻结 TDD / Plan / CC 或原 TV 标准。只执行了上文记录的一次真实 GPT-5.6 Luna UI 诊断复现；其余调查为源码、日志和当前用户上下文 ORM 只读检查。原始 TV 均保持 FAIL；没有把 NOT REACHED 写为 PASS。后续若启动针对性 TV 或 M4 TDD，需另行依项目流程授权。

## 评审关闭记录

- **决定：** 用户批准 RCA 汇总进入评审关闭。
- **日期：** 2026-11-17。
- **关闭范围：** 关闭本轮 RCA 汇总评审及证据归档；不表示 M4 缺陷已修复，也不表示所有目标能力已验证。
- **未验证项保持原状态：** RCA-004 为 `INCONCLUSIVE / 前置阻断`；RCA-006 为 `INCONCLUSIVE / 前置依赖未满足`；RCA-007、RCA-008 为 `NOT REACHED`。它们仍是未验证项，不因本次汇总评审关闭而转为 PASS、根因已确认或缺陷关闭。
- **处置：** 保留现有八份 RCA、20 项覆盖归类与候选后续 TV；不修改代码、Prompt、冻结基线、原始 TV 结果或单项 RCA 结论。

## CC-M4-02 后续 RCA 补充（2026-11-20）

本节是 CC-M4-02 新增实施证据索引，不改写 2026-11-17 已评审关闭的 RCA-001～008 历史结论。

- 新增 [RCA-009 — 关系值解析与查询规划](RCA-009_CC-M4-02_Relation_Query_Planning.md)：确认 Thread 1688 的 Many2one 显示值被错误当作 ID，`describe(limit=1)` 页未读完；修复后 `provider_constraints_v1.1` 的目标复杂任务通过真实 Provider 与隐藏 Oracle。
- 明确 `provider_domain_precision_v0.2` 的 INVALID_QUERY 后宽查询返回 9/9 条、`has_more=false` 且带有确定性筛选字段，最终 Oracle 身份一致，属于完整候选集后筛选，不属于遗漏条件或不完整分页。
- 记录 `provider_constraints_v1.0` 的 HTTP 400 tool-call 配对错误，和本 CC 采用单 Retriever 调用/响应的提示约束；未把它归因成 Retriever Domain 问题。
- `provider_ambiguity_v0.1/v0.2` 的“客户数量”探索因业务口径与隐藏 Oracle 未被用户任务定义，记为 NOT SCORABLE，不转换为 PASS/FAIL。CC-M4-02 ATR 因 CC-TEST-004 独立业务歧义子场景仍无有效 Oracle，维持待评审状态。
- 最终自动化证据：提示定向 12 项、M3 60 项、M2 Retriever 6 项均通过；RUN-050 对六轮 Provider 的合成数据清理 ORM 复核通过。

### CC-M4-02 复测补充（2026-11-20，晚间）

此补充只更新 CC-M4-02 的新证据，不修改本报告的 RCA-001～008 历史结论，也不改写前一段当时的评审状态。

- RUN-063～066 的真实 Provider 复测确认：Agent 在 `INVALID_QUERY` 后有时遗漏“个人联系人”条件并报候选数，有时完成元数据及父记录解析后没有目标记录查询仍报 0；自关联层级请求收到澄清指令仍曾自行选直接父关系。上述 FAIL 均保留在 [RCA-009](RCA-009_CC-M4-02_Relation_Query_Planning.md) 与 CC-M4-02 ATR。
- 最小通用任务指引补充后，RUN-067 在 `company_type` 被拒后改用由 Registry 元数据确认可搜索的 `is_company=false`，日期、国家、有效状态和直接父 ID 均保留，返回身份与独立 Oracle 一致；RUN-068 对直接范围 2 与所有后代范围 6 的歧义先询问用户，没有查询目标记录或报数。两项分别覆盖 CC-TEST-001/004 目标路径，不抹除之前的失败波动。
- 提示定向测试 12/12、M3 全量 60/60、M2 Retriever 6/6 通过；RUN-073 ORM 核对测试账户、Thread、合成 partner 均无残留，allowlist 为 `1398`。
- v0.3 原始 SDK 审计仍保留 9/9 Provider 请求响应及 Thread 1911；重跑保护脚本曾拒绝覆盖后又在外层错误处理覆盖结果 JSON。该证据事故已明示于 RCA-009/IHR/ATR；RUN-058 是拒绝重跑记录，不是新 Provider 测试。
- CC-M4-02 已提交负责人关闭评审，但本报告不代替负责人关闭决定。

### CC-M4-02 关闭决定（2026-11-20）

- 项目负责人已批准按冻结 CC-M4-02 v0.2 的验收范围关闭该 CC。
- 关闭依据记录于 [`FR-CC-M4-02.md`](../../implementation/FR-CC-M4-02.md)；CC-TEST-001～008 的状态与证据边界在 ATR 中逐项保留。
- RUN-029、RUN-063～066 的历史失败、“客户总数” NOT SCORABLE 探索及 v0.3 结果 JSON 覆盖事故均不改写；本决定不表示 M4 整体关闭或 M4-03 已开始实施。
