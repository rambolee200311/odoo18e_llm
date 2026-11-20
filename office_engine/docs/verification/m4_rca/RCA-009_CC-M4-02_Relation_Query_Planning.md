# RCA-009 — CC-M4-02 关系值解析与查询规划

**关联 CC：** CC-M4-02 v0.2  
**状态：** Thread 1688 关系值错误已由 v1.1 复测通过；RUN-067 条件恢复和 RUN-068 关系歧义澄清通过。v0.4～v0.7 失败保留，提交 CC 评审。  
**数据库：** 仅使用 `odoo18e_llm`。  
**Provider：** OpenAI GPT-5.6 Luna / `gpt-5.6-luna`。

## 1. 调查范围

调查 Thread 1688（`provider_constraints_v0.7`）中普通用户合成查询返回零条的原因，并核实两种相邻现象：收到 `INVALID_QUERY` 后进行宽候选查询是否遗漏条件；多工具调用的工具结果是否完整进入下一次 Provider 请求。

## 2. 失败链逐步核对

| 阶段 | 实际证据 | 判定 |
|---|---|---|
| 用户原始要求 | 要求指定日期、有效状态、直接隶属指定公司、指定国家的个人联系人；后续只把对象改为公司账户并要求附带各公司的联系人，保留其余条件。 | 业务谓词清楚；同一 Thread 的局部修改语义明确。 |
| `discover` | Thread 1688 的发现请求查询词为 `res.partner fields created date parent company country email name contact type`，返回 Registry 候选（总数 757，当前页 100，`has_more=true`）。 | Discovery 结果是模型候选，不是字段值或业务记录。该次调用未提供父公司/国家的记录 ID。 |
| `describe` | 第一次对 `res.partner` `limit=1` 只返回 198 个字段中的 1 个（`active`），`has_more=true`。之后一次请求列出多个期望字段但仍 `limit=1`；另一次把字段词放入 `describe.query`，收到既有参数错误。 | Agent 没有先从完整字段页取得全部所需关系元数据；`discover` 中出现技术字段词也不能代替 `describe`。 |
| 关系元数据与值来源 | `parent_id`、`country_id` 是 Many2one，Domain 需要目标记录 ID。失败调用使用父公司文本片段 `0712d5fff7d2` 与国家显示名 `Andorra`，没有成功的前置搜索返回这些值。 | 关系字段名存在并不意味着显示文本可直接作为外键值；两个 ID 均无合法来源。 |
| 实际 Domain | 两轮分别用 `parent_id = "0712d5fff7d2"`、`country_id = "Andorra"`，而日期、`active`、`is_company` 条件均在 Domain 中。 | 这是 Agent 传入的合法值类型/语义错误；不是 ORM 忽略 Domain、不是 ACL 隐藏目标记录，也不是分页截断。 |
| ORM 返回与 Oracle | 两次普通用户查询均成功返回 `count=0`、`has_more=false`；隐藏 Oracle 中存在符合原要求的合成记录。 | 成功零结果被 Agent 当成任务结果，导致最终回答缺少 Oracle 身份。 |
| 后续联系人关联 | 早期 v0.9 轨迹曾复用上一轮个人联系人，而没有用公司 ID 查询子联系人并保留其父关系。 | 先前结果只有在其实际关系值证明关联时才可复用；本场景必须查询所选公司 ID 对应的子联系人。 |

原始证据：`../../implementation/evidence/CC-M4-02/provider_constraints_v0.7_result.json`、`provider_constraints_v0.7_sdk_audit.jsonl`、`ATR-RUN-029_provider_constraints_final.log`。该结果继续保留为 FAIL，不被后续成功结果覆盖。

## 3. `INVALID_QUERY` 后宽查询的区分

`provider_domain_precision_v0.2` 与 Thread 1688 是两条不同轨迹：

1. focused run 的第一次 `search` 因不可搜索字段被 Retriever 以 `INVALID_QUERY` 拒绝。
2. 后续查询移除了该不可搜索谓词，但返回完整候选集合：`count=9`、`returned_count=9`、`has_more=false`；同时带回 deterministic filter 所需的字段值。
3. Agent 对完整结果作可复核的结果后筛选，最终集合与独立 Oracle 的 4 个身份一致。

按冻结 CC 的完整执行链标准，这次宽查询是**合法的完整候选集加确定性结果筛选**，不是遗漏条件或分页不完整；它不等价于 Retriever Domain 精确，也不作为 ORM Domain 校验的替代证据。

Thread 1688 收到的是 `describe(query=...)` 的参数拒绝。该失败调用没有字段结果；其后 Agent 将未经查询解析的显示值直接作为 Many2one 值，故查询失败不是“宽查询”的成因。证据不支持把两种轨迹合并成一个问题。

## 4. 多工具调用导致的 Provider 续接错误

`provider_constraints_v1.0` 的 Provider 审计显示：一个 assistant 消息包含两个 Retriever tool calls，其中一个工具调用失败；随后提交给 Provider 的历史缺少同一 assistant 消息另一个 `tool_call_id` 对应的工具消息，OpenAI 返回 HTTP 400：`An assistant message with 'tool_calls' must be followed by tool messages responding to each 'tool_call_id'`。工具结果在 Odoo 消息中存在，但这组并行调用的历史未组成 Provider 可接受的完整配对。

本 CC 的最小处理是在 Retriever 当前任务指引中要求每个 assistant 响应只发一个 Retriever 调用，收到其结果后再规划下一次。未修改上游框架、公开 Tool Schema 或工具分发接口；此指引只针对本 CC 观察到的消息配对边界，不构建 M4-03 的通用恢复机制。

证据：`provider_constraints_v1.0_result.json`、`provider_constraints_v1.0_sdk_audit.jsonl`。

## 5. 最小修复及复测

在 `office_engine/office_engine_m3/models/llm_thread.py::_prepare_chat_kwargs()` 为已有 Retriever 对话补充通用指引：

- 区分 Registry `discover` 与字段 `describe`；描述分页须读到实际返回所需字段的页。
- 关系查询先按关系字段及其 `relation` / `rec_name` 解析用户业务名称，并只使用成功查询返回的 ID。
- 查询子记录时依据描述中的关系/反向字段，以已确认父记录 ID 批量查询并保留每条子记录的父 ID。
- 不得用任意 ID 或无关记录探测；每次查询要支持当前任务。
- 遇到 `INVALID_QUERY` 时不得使用失败调用的结果；宽候选查询仅在全页读取完、返回了全部后筛选值且完整约束可确定性应用时才可用于交付。
- 每个 assistant 响应仅调用一次 Retriever，避免未配对工具消息。

未改变 Provider Tool Schema、公开接口、权限、Domain fail-closed 校验、普通用户 ORM、M2/M3 文件和确认生命周期；没有硬编码模型、字段、业务词、状态或测试答案。

`provider_constraints_v1.1` 使用新合成数据和普通内部用户，真实 Provider 11 请求 / 11 响应 / 0 SDK 错误。独立 Oracle 验证：

- 父公司、国家均经 `rec_name` 查询取得唯一记录 ID；
- 第一轮 2 个个人联系人身份及全部用户条件准确；
- 第二轮只改变目标对象并增加子联系人要求，原日期、父公司、国家和有效状态继续生效；
- 2 个公司身份准确；使用 `parent_id in [公司 ID 列表]` 读取 2 个子联系人，父子 ID 映射逐项匹配；
- 所有结果页 `has_more=false`，decoy 未出现，未做任意 ID 探测，最终回答值符合 Oracle。

证据：`../../implementation/evidence/CC-M4-02/provider_constraints_v1.1_result.json`、`provider_constraints_v1.1_sdk_audit.jsonl`、`provider_constraints_v1.1_oracle_validation.json`、`ATR-RUN-043_provider_constraints_v1.1.log`。

## 6. 歧义探索的 Oracle 边界

额外运行 `provider_ambiguity_v0.1` 与 `provider_ambiguity_v0.2`，输入“统计客户总数”。Agent 根据 `res.partner` 的 `customer_rank` 元数据查询 `customer_rank > 0`，返回 0。测试脚本原先把所有符合关系和日期的合成 partner 直接定义为“客户”，预期 2/4 并要求澄清；但用户原话没有定义“客户”是否等于全部 partner，且 Odoo 的可见元数据提供了一个直接相关的 `Customer Rank` 字段。因此该 Oracle 没有充分依据判定 0 为错或判定必须澄清，这两次探索标为 **NOT SCORABLE**，不计入产品 FAIL 或 PASS，也不覆盖 v1.1 的业务任务验收。原始请求、Tool Call、Provider 审计及结果均保留。

这两次运行没有改变最终产品提示。v0.2 的短暂提示实验与自动化测试已在复核后撤销；最终代码维持 v1.1 已通过时的通用关系/任务指引。记录文件：`../../implementation/evidence/CC-M4-02/provider_ambiguity_v0.1_result.json`、`provider_ambiguity_v0.1_sdk_audit.jsonl`、`provider_ambiguity_v0.2_result.json`、`provider_ambiguity_v0.2_sdk_audit.jsonl`。

## 7. 回归与数据清理

- 最终提示契约定向回归：12 项，0 failed / 0 error，`ATR-RUN-070_final_prompt_regression.log`。初次 RUN-069 的旧文本断言失败已修正，不是产品逻辑失败。
- `office_engine_m3` 全量回归：60 项，0 failed / 0 error，`ATR-RUN-071_m3_final_regression.log`。
- M2 Retriever 集成：6 项，0 failed / 0 error，`ATR-RUN-072_m2_retriever_final_regression.log`。
- ORM 清理复核：`ATR-RUN-073_postrun_orm_check.json` 核验 14 个有结果 Provider 运行，并由原始 v0.3 审计核验 Thread 1911/唯一后缀；测试用户、Thread、合成伙伴均无残留，国家记录保持，审计 allowlist 恢复 `1398`；PASS。

## 8. 后续失败根因与修复证据（2026-11-20）

### 8.1 可观察失败链

层级夹具由 ORM 合成：一个公司父项、2 个直接个人联系人、2 个直接子公司、各有 2 个个人联系人，另有一个无关 decoy。隐藏 Oracle 得到直接个人联系人 2 个、所有后代个人联系人 6 个，身份集合不同；直接 partner 子项 4 个、全后代记录 8 个。Oracle 记录不在 Agent 消息或 Provider Tool 参数中。

Provider 请求/工具回执证实：`discover` 返回候选 `res.partner`（描述 `Contact`、`rec_name=name`）；`describe` 返回 `parent_id`（Many2one，relation=`res.partner`）、`country_id`（Many2one，relation=`res.country`）、`company_type`（Selection，`person`/`company`）及 `is_company`（Boolean），并提供日期和有效字段。Agent 随后按父名称与国家名称分别执行成功只读搜索，得到本次 fixture 的父记录 ID 和国家 ID `1`；故本组复测不是把关系显示值直接当外键 ID。

- v0.4/v0.5：`company_type` Domain 被 `INVALID_QUERY` 拒绝；Agent 随后按直接父关系筛选并报告 2，没有澄清直接与所有后代范围。两次 Provider 请求均含自关联歧义指令。
- v0.6：去除“只报总数”后，Agent 返回 4 个直接 partner 子项，包含 2 个公司和 2 个人，遗漏“个人联系人”条件。
- v0.7：用户明确说“直接关联”，Agent 完成 metadata 和父项 ID 解析，却没有执行目标 partner 搜索，直接回答 0；Oracle 有两条合格记录。

因此失败位于 Agent 任务条件保留、对错误/回执的利用和完成声明：有时直接缩窄歧义，有时把 `returned_count` 当作业务计数，有时无查询仍报零。Retriever 对 `company_type` 的 fail-closed 行为正确；ACL、分页和外键 ID 来源不是这些新失败的原因。

下表核对了这组复测的**实际**查询参数与 ORM 回执；Domain 中的父记录 ID 是该次随机合成夹具经成功名称查询返回的 ID，不是固定配置：

| Run | 失败查询及 ORM 回执 | 后续查询及 ORM 回执 | Oracle 差异与根因 |
|---|---|---|---|
| v0.4 / RUN-063 | `res.partner` Domain：`create_date >= 2026-11-20 00:00:00`、`create_date < 2026-11-21 00:00:00`、`active = true`、`country_id = 1`、`parent_id = 25890`、`company_type = person`；工具明确返回 `INVALID_QUERY`，没有 ORM 结果。 | 删除不可搜索的 `company_type`，以 `is_company = false` 代替，其余条件不变；普通用户 ORM `count=2`、`returned_count=2`、`has_more=false`，两条均为直接子联系人。 | 直接口径为 2、所有后代为 6。外键 ID 和其它条件正确，但 Agent 在业务语义有实质歧义时直接选了直接关系，回答 2。 |
| v0.5 / RUN-064 | 相同条件，`parent_id = 25902`、`company_type = person`；收到 `INVALID_QUERY`。 | 改用 `is_company = false`，保留日期、active、country、parent；普通用户 ORM `2/2`，完整单页。 | Oracle 仍为直接 2、所有后代 6。实际 Provider 请求已有自关联澄清指引，但 Agent 仍自行选直接口径并回答 2。 |
| v0.6 / RUN-065 | `parent_id = 25914`、`country_id = 1`、`company_type = person`、`active = true`、日期下界及排他上界；收到 `INVALID_QUERY`。 | 后续 Domain 保留 `parent_id`、`country_id`、`active` 和日期范围，但**没有** `company_type` 或等价 `is_company` 谓词；ORM 返回 `4/4`，记录为 2 个个人联系人加 2 个公司账户，`has_more=false`。 | Oracle 目标为 2 个直接个人联系人、6 个所有后代个人联系人。Agent 报 4 并漏掉个人类型条件；返回页虽完整，却没有对全部条件作确定性筛选，故不是合法后筛选。 |
| v0.7 / RUN-066 | 用户明确说直接关联。Agent 通过 `parent_id` 的 `res.partner` 自关联元数据，并成功按父名称、国家名称分别查得本次父记录/国家 ID；未发现错误关系值。 | 没有对目标个人联系人执行 `res.partner search`，因此没有目标 Domain、ORM 结果或分页回执；Agent 仍回答 0。 | 隐藏 Oracle 有 2 个符合条件的直接个人联系人。没有查询结果不等于成功零结果；这是错误完成声明，不是 Domain、ACL 或分页缺陷。 |

复核表明，RUN-063～066 的父/国家关系值均来自成功只读名称查询，且实际关系条件使用 `parent_id` 的直接关系边。该组新失败没有复现“把显示名称当外键 ID”；这一问题只在上文 Thread 1688 中被直接证据确认。新失败分别是未澄清关系深度、`INVALID_QUERY` 后遗漏个人类型谓词，以及未查询便报零。对应原始参数、工具回执、最终答复和隐藏 Oracle 见 `provider_hierarchy_ambiguity_v0.4_result.json` 至 `v0.6_result.json`、`provider_query_recovery_v0.7_result.json` 及各自 SDK audit 文件。

### 8.2 修复及对照结果

在 `_prepare_chat_kwargs()` 中更新通用任务指引：

1. 数值计数必须有成功完整查询或完整候选集确定性筛选；未查询、失败查询或不完整页不能回答 0。
2. 收到 `INVALID_QUERY` 不得静默删除被拒谓词。应改用 Registry 已确认可搜索的等价字段，或在完整候选页带齐全部筛选值时先应用所有条件再计数；否则说明无法确定。
3. `describe` 发现目标模型存在自关联，且自然语言表达未说明深度时，必须先问用户是直接关联还是所有后代；不能用一个关系边或当前查询结果替用户选择。

RUN-067/v0.8 的用户明确指定“直接关联”。Agent 第一次以 `company_type=person` 查询收到 `INVALID_QUERY`，随后使用由 metadata 确认可搜索的 `is_company=false`，保留父 ID、国家 ID、active 和日期范围，普通用户 ORM 返回两条，身份与隐藏 Oracle 一致，最终回答 `2`；9/9 Provider 请求/响应、0 SDK 错误。此为 CC-TEST-001 目标分支 PASS。

RUN-068/v0.9 使用模糊的“公司下面”任务。Agent 先基于自关联元数据向用户询问“仅直接挂在公司下，还是包括所有下级公司”，没有发起目标记录 search，没有回答数字；Oracle 证实两个范围身份/数量分别为 2 和 6。8/8 请求/响应、0 SDK 错误。此为 CC-TEST-004 澄清分支 PASS。

### 8.3 v0.3 重跑保护及证据状态

v0.3 原始 SDK 审计文件在重跑时已存在，并包含 Thread 1911 的 9/9 请求和响应、模型最终回答 `2`。同名运行保护抛出异常后，runner 外层捕获逻辑仍将错误结果写入同名 JSON，造成原结果 JSON 被覆盖。原 SDK 审计完整保留；当前重跑拒绝 JSON 的副本为 `provider_hierarchy_ambiguity_v0.3_retry_guard_result.json`，`ATR-RUN-058_hierarchy_ambiguity_v0.3.log` 记录该次没有发起 Provider 调用。后续 runner 增加最外层证据存在检查；RUN-073 通过 ORM 对原审计 Thread 与随机后缀确认无夹具残留。该证据完整性事故已明确记录，不将修复后的副本冒充原始结果。

## 9. 结论边界

Thread 1688 的关系值规划根因已由真实失败证据确认；v1.1/RUN-067 的普通用户 + Provider + 隐藏 Oracle 证明复合查询和错误条件恢复目标通过，RUN-068 证明实际自关联歧义目标先澄清再执行。v0.4～v0.7 失败保留。CC-TEST-001/004 的本轮目标场景现有 PASS 证据；本 RCA 提交 CC 关闭评审，不自行宣布关闭。
