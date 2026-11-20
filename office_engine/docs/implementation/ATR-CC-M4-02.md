<!--
模板来源：office_engine/docs/skill/odoo-project-workflow/references/templates/Coding/ATR模板.md
本文件状态：**CC-M4-02 已由负责人于 2026-11-20 批准按冻结验收范围关闭。** 本 ATR 的失败、NOT SCORABLE 和证据边界均保留原状态。
-->

# ATR — CC-M4-02 意图理解与任务规划

## 0. 文档治理

本 ATR 记录冻结 CC-M4-02 v0.2 的自动化、普通用户 ORM 和真实 Provider 证据。成功、失败、临时实验及清理记录均保留；临时实验不替代冻结基线结果。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | CC-M4-02 |
| IHR | `IHR-CC-M4-02.md` |
| CC | `CC-M4-02_意图理解与任务规划_v0.2.md`；FROZEN |
| 环境 | 本地开发；仅使用 `odoo.conf` 指定的 `odoo18e_llm` |
| Provider | OpenAI GPT-5.6 Luna / `gpt-5.6-luna` |
| 工具 | `odoo_record_retriever`、`office` |
| UI HVR | N/A — 冻结 CC 明确排除 |

## 2. CC 自动化验收矩阵

| CC-TEST | 状态 | 实际证据与边界 |
|---|---|---|
| 001 复合业务条件与真实查询 | **PASS（RUN-043、067）** | v1.1 两轮父子关联任务及 RUN-067 明确“直接关联”查询都由普通用户通过 Retriever 执行；日期、有效状态、关系 ID、对象类型及结果身份与独立 Oracle 一致。历史 RUN-029 FAIL 保留 |
| 002 最新用户指令优先 | **PASS** | 同一 Thread 第二轮将“个人联系人”改为“公司账户并补充联系人”，保留父公司、日期、国家及有效状态；独立 Oracle 核对最终消息中的对象集合和关系值。依据 `provider_constraints_v0.4_oracle_validation.json` |
| 003 局部修改条件保留 | **PASS** | RUN-013 的二轮用户消息只改变对象类型并增加联系人输出；最终答案保留其他有效条件。系统指引断言另由 `test_current_task_rules_preserve_latest_user_instruction_and_unmodified_constraints` 覆盖 |
| 004 动态规划、元数据与澄清 | **PASS（RUN-043、068）** | v1.1 的 `discover → describe → rec_name 搜 ID → 完整 Domain → 按父 ID 批量查子记录` 动态路径通过 Oracle；RUN-068 在两种层级口径会改变身份集合时，Agent 依据自关联元数据先向用户澄清，未擅自搜索或报数。v0.4～v0.7 失败保留，v0.1/v0.2“客户总数”仍 NOT SCORABLE |
| 005 operation 参数拒绝 | **PASS（Execute + Provider 负向调用）** | 自动化覆盖 search、describe、legacy 的 `query` 拒绝且模型解析/ORM 未发生。RUN-029 Provider 实际发出 `describe(query=...)`，工具返回既有 `INVALID_QUERY`；`discover.query` 及旧 search 兼容回归通过 |
| 006 Provider / Execute / ORM 契约 | **PASS（接口、执行与 ORM 边界）** | 非搜索字段的 `INVALID_QUERY` fail-closed 及零结果区分由自动化/Provider v0.2 覆盖；普通用户合法 Domain、关系 ID 与完整结果由 RUN-043 验证。Focused v0.2 的 9/9 宽候选结果全页完整并带回过滤值，结果后筛选与 Oracle 一致；不将它误记为 Domain 等价 |
| 007 当前权限与零结果 | **PASS（自动化/组件）** | `test_registry_discovery_and_description_ignore_business_acl` 保持元数据行为并验证受限业务读取 AccessError；结构化错误测试区分成功零结果与无效 Domain；合成记录查询使用普通测试用户，没有业务 `sudo()` |
| 008 兼容、调用量与回归 | **PASS（组件及兼容性）** | 最终 M3 60 项和 M2 Retriever 6 项均 0 failed / 0 error；legacy search、分页及 M2/M3 响应回归通过。Provider 调用与耗时见 §3；未设新的硬性性能门槛 |

### 2.1 总体评定

最新复杂关系规划场景 v1.1、条件错误恢复 RUN-067 和歧义澄清 RUN-068 均按各自隐藏 Oracle 判定。CC-TEST-001 与 CC-TEST-004 当前证据均 PASS；v0.4～v0.7 的新失败仍保留，说明真实 Provider 行为存在波动。负责人已按冻结验收范围批准关闭；历史失败不改写。

## 3. 真实 Provider 证据

| Run | 状态 | 摘要 | 证据 |
|---|---|---|---|
| ATR-RUN-009 | FAIL / Provider 未调用 | 测试用户缺少发件邮箱，Odoo 在写入用户消息前拒绝；Provider 请求为 0。已修正合成用户 email，原始错误保留 | `evidence/CC-M4-02/ATR-RUN-009_real_provider_two_turn.log` |
| ATR-RUN-010 | INVALID / 不作为验收 | Provider 调用已发生，但 `message_post` 延迟 Bus 事件在清理次序中导致 FK 错误，未生成完整结果 JSON；保留原日志和 v0.2 SDK 审计，未把它算作通过 | `ATR-RUN-010_real_provider_two_turn.log`、`provider_constraints_v0.2_sdk_audit.jsonl` |
| ATR-RUN-011 | INCONCLUSIVE | 测试日志级别未留下可核对断言结果，不作为通过证据 | `ATR-RUN-011_provider_audit_user_test.log` |
| ATR-RUN-012 | PASS | 普通 Odoo 用户可在测试开关、绝对日志路径、白名单 Thread 条件下通过审计门禁；限制未改变业务权限 | `ATR-RUN-012_provider_audit_user_test.log` |
| ATR-RUN-013 / v0.4 | PASS（业务结果）；Domain 子项不通过 | 11/11 Provider 请求响应；9 个请求含工具 Schema，2 个内部请求无工具；8 次 Retriever、Office 0；两轮答案与 fixture Oracle 一致；耗时 24.018s / 7.684s | `provider_constraints_v0.4_result.json`、`provider_constraints_v0.4_sdk_audit.jsonl`、`provider_constraints_v0.4_oracle_validation.json`、`ATR-RUN-013_real_provider_two_turn.log` |
| ATR-RUN-017 / v0.5 | **EXPLORATORY FAIL / PASS** | 临时拒绝非搜索字段的实验版：18/18 Provider 请求响应，工具执行 7 次 error。第一轮错误关系 ID 和截断名称查询后未完成；第二轮通过名称查询和关系读取完成更新任务。该行为已撤回，不能作为当前产品基线或整体验收通过 | `provider_constraints_v0.5_result.json`、`provider_constraints_v0.5_evaluation.json`、`provider_constraints_v0.5_sdk_audit.jsonl`、`ATR-RUN-017_real_provider_two_turn.log` |
| ATR-RUN-024 / v0.6 | **Provider 业务任务 FAIL；Domain error propagated** | 9/9 请求响应；`company_type` Domain 返回 `INVALID_QUERY`。Agent 改用 `is_company`，但仍带错父/国家 ID，两个任务无法匹配目标记录；清理通过 | `provider_constraints_v0.6_result.json`、`provider_constraints_v0.6_sdk_audit.jsonl`、`ATR-RUN-024_provider_domain_precision.log` |
| ATR-RUN-025 / Domain v0.1 | **不作为 Oracle 验收** | 7/7 请求响应；模型遇到 `company_type` 错误后做宽查询。初版 fixture 的测试用户联系人名也含唯一标记，独立 Oracle 漏计该合成记录；该夹具问题已在 v0.2 runner 修正，原结果保留 | `provider_domain_precision_v0.1_result.json`、`provider_domain_precision_v0.1_sdk_audit.jsonl` |
| ATR-RUN-026 / Domain v0.2 | **Domain fail-closed PASS；Agent fallback 未等价** | 6/6 请求响应；非搜索字段错误在 Odoo UI 工具消息路径返回；后续查询不含类型条件，ORM 返回 9 个记录，Agent 用字段值给出与 4 个隐藏 Oracle 身份一致的最终输出。该运行不证明宽查询 Domain 精确 | `provider_domain_precision_v0.2_result.json`、`provider_domain_precision_v0.2_sdk_audit.jsonl`、`provider_domain_precision_final_oracle_validation.json` |
| ATR-RUN-029 / v0.7 最终复杂样例 | **FAIL（业务任务）** | 11/11 SDK 请求响应，Provider SDK 一次自动重试；Agent 发出 `describe(query=...)` 后收到 `INVALID_QUERY`。随后把名称片段作为 Many2one parent 值、把国家名称作为 country ID，真实 ORM 返回零条；最终回复未含 Oracle 记录。所有夹具清理通过 | `provider_constraints_v0.7_result.json`、`provider_constraints_v0.7_sdk_audit.jsonl`、`ATR-RUN-029_provider_constraints_final.log`、`provider_domain_precision_final_oracle_validation.json` |
| ATR-RUN-043 / v1.1 关系规划复测 | **PASS（CC-TEST-001；CC-TEST-004 动态路径）** | 11 请求 / 11 响应 / 0 SDK 错误；使用普通内部用户和合成 partner；父公司及国家由成功 `rec_name` 查询解析；两轮结果、身份、查询条件、分页及子记录父子映射均与隐藏 Oracle 一致。耗时 40.768s / 13.565s | `provider_constraints_v1.1_result.json`、`provider_constraints_v1.1_sdk_audit.jsonl`、`provider_constraints_v1.1_oracle_validation.json`、`ATR-RUN-043_provider_constraints_v1.1.log` |
| ATR-RUN-047 / ambiguity v0.1 | **NOT SCORABLE（探索）** | Agent 使用 `customer_rank > 0` 并回答 0；用例原 Oracle 把全部关联 partner 定义为客户，但用户输入未指定该口径且 Odoo 元数据包含 `Customer Rank`，无法据此判定任务错误 | `provider_ambiguity_v0.1_result.json`、`provider_ambiguity_v0.1_sdk_audit.jsonl`、`ATR-RUN-047_provider_ambiguity.log` |
| ATR-RUN-049 / ambiguity v0.2 | **NOT SCORABLE（同一 Oracle 缺陷复核）** | 与 v0.1 同口径和同结果；短暂提示试验未成为产品改动，未作为通过或失败证据 | `provider_ambiguity_v0.2_result.json`、`provider_ambiguity_v0.2_sdk_audit.jsonl`、`ATR-RUN-049_provider_ambiguity_v0.2.log` |
| v0.3 原始审计 / ATR-RUN-058 重跑保护 | **原 Provider 轨迹 FAIL；重跑未执行 Provider** | 原始 SDK 审计含 Thread 1911 的 9/9 请求/响应、最终回答 `2`，不符合直接联系人 2 / 所有后代 6 的歧义 Oracle。随后同标签重跑因证据已存在而拒绝；脚本错误地将拒绝信息写入同名结果 JSON。原审计保留，重跑错误单独留档 | `provider_hierarchy_ambiguity_v0.3_sdk_audit.jsonl`、`provider_hierarchy_ambiguity_v0.3_retry_guard_result.json`、`ATR-RUN-058_hierarchy_ambiguity_v0.3.log` |
| ATR-RUN-063 / hierarchy v0.4 | **FAIL（歧义澄清）** | 父公司与国家名称查询均成功并返回 ID；含 `company_type=person` 的完整日期/有效/国家/父记录 Domain 收到 `INVALID_QUERY`。随后改用 `is_company=false`，返回 2/2 直接个人联系人并回答 2；Oracle 为直接 2、所有后代 6，Agent 未澄清范围 | `provider_hierarchy_ambiguity_v0.4_result.json`、`provider_hierarchy_ambiguity_v0.4_sdk_audit.jsonl` |
| ATR-RUN-064 / hierarchy v0.5 | **FAIL（歧义澄清）** | 更强自关联规则已进入实际 Provider 请求；关系 ID 来自成功名称查询，`company_type=person` 收到 `INVALID_QUERY` 后以 `is_company=false` 得到 2 条直接记录并回答 2。Oracle 直接 2 / 所有后代 6，仍未澄清 | `provider_hierarchy_ambiguity_v0.5_result.json`、`provider_hierarchy_ambiguity_v0.5_sdk_audit.jsonl` |
| ATR-RUN-065 / hierarchy v0.6 | **FAIL（条件完整性）** | `company_type=person` 收到 `INVALID_QUERY` 后，后续 Domain 保留父 ID、国家 ID、active 和日期，但遗漏个人类型及等价条件；ORM 完整返回 4 条（2 人、2 公司），Agent 报 4。Oracle 目标为直接个人 2 / 所有后代个人 6 | `provider_hierarchy_ambiguity_v0.6_result.json`、`provider_hierarchy_ambiguity_v0.6_sdk_audit.jsonl` |
| ATR-RUN-066 / query recovery v0.7 | **FAIL（无查询报零）** | Agent 依据元数据和成功名称查询取得父项/国家 ID，但没有执行目标记录 Domain search，没有 ORM 结果或分页回执仍回答 0；隐藏 Oracle 有 2 条直接个人联系人 | `provider_query_recovery_v0.7_result.json`、`provider_query_recovery_v0.7_sdk_audit.jsonl` |
| ATR-RUN-067 / query recovery v0.8 | **PASS（精确条件恢复，CC-TEST-001）** | Agent 首先因 `company_type` 收到 `INVALID_QUERY`，再使用元数据确认可搜索的 `is_company=false`；Domain 保留日期、国家、有效状态和直接父 ID，返回 2/2 Oracle 身份并回答 2 | `provider_query_recovery_v0.8_result.json`、`provider_query_recovery_v0.8_sdk_audit.jsonl` |
| ATR-RUN-068 / hierarchy v0.9 | **PASS（歧义澄清，CC-TEST-004）** | Agent 读取自关联元数据后先问“仅直接挂在公司下，还是包括所有下级公司”；未搜索目标记录或报数；8/8 Provider 请求响应、0 SDK 错误 | `provider_hierarchy_ambiguity_v0.9_result.json`、`provider_hierarchy_ambiguity_v0.9_sdk_audit.jsonl` |

RUN-013 的独立 Oracle 评估从合成夹具生成规则和随机后缀独立派生期望名称/邮箱，不读取工具返回来构造期望集合，未传给 Agent 或 Provider。Provider 只处理合成任务、合成记录查询结果及 Registry 元数据，不含凭据。

## 4. 回归及运行证据

| Run | 范围 | 结果 |
|---|---|---|
| ATR-RUN-001～005 | 前置 Retriever / ORM 夹具尝试 | 早期试验遇到权限组、测试数据和断言设置问题；原日志保留，不计为最终验收 |
| ATR-RUN-006 | Retriever ORM / 权限测试 | 18 项，0 failed / 0 error；包含普通用户合成父子关系查询 |
| ATR-RUN-007 | `office_engine_m3` 全模块 | 58 项，0 failed / 0 error（历史日志当时统计 58 项） |
| ATR-RUN-008 | M2 `TestOfficeRetrieverIntegration` | 6 项，0 failed / 0 error |
| ATR-RUN-014 | 临时 Domain 搜索性测试初次运行 | 测试 Oracle 错误地预期 `display_name` 匹配单条，但测试生成的三条夹具同名；不是产品缺陷。保留原始失败摘录 |
| ATR-RUN-015 | 临时 Domain 搜索性测试复跑 | 1 项，0 failed / 0 error；实验代码随后撤回，不算产品实现验收 |
| ATR-RUN-016 | 清理历史合成残留 | ORM 精确识别无关联用户的孤立 reader 联系人 ID 22615，删除后确认剩余 0 |
| ATR-RUN-018 | 最终 `office_engine_m3` 全量回归 | 58 项，0 failed / 0 error；66 次测试统计包含 Odoo 运行器初始化统计 |
| ATR-RUN-019 | 最终 M2 Retriever 定向回归 | 6 项，0 failed / 0 error |
| ATR-RUN-020 | 数据库最终只读核对 | 两模块版本与清单一致；测试用户、夹具联系人、Thread 均为 0；审计 allowlist 恢复为 `1398` |
| ATR-RUN-022 | 首次定向运行 | 命令退出码 0，但日志缺少测试统计；不单独计入通过证据，后由 RUN-023 取得明确统计 |
| ATR-RUN-023 | Retriever 定向回归 | 20 项，0 failed / 0 error；覆盖 Domain 搜索性、存储字段、计算字段自定义 search、related search 和 legacy search |
| ATR-RUN-027 | M3 全模块回归 | 60 项，0 failed / 0 error |
| ATR-RUN-028 | M2 Retriever 集成回归 | 6 项，0 failed / 0 error |
| ATR-RUN-030 / 032 | Odoo ORM 只读复核 | 两模块 installed；M3 `18.0.7.0.5`、M2 `18.0.26.0.22`；合成用户/联系人/Thread 均 0，audit allowlist 为 `1398` |
| ATR-RUN-031 | 最终 M3 全模块回归 | 60 项，0 failed / 0 error；覆盖最终新增的原始 ORM 忽略对照断言 |
| ATR-RUN-050 | 多轮 Provider 合成夹具清理复核 | v0.8～v1.1 与两次歧义探索共 6 轮；用户、Thread、合成伙伴均无残留；既有国家仍在；审计 allowlist 为 `1398`；PASS |
| ATR-RUN-051 | 最终 `office_engine_m3` 回归 | 60 项，0 failed / 0 error |
| ATR-RUN-052 | 最终 M2 `TestOfficeRetrieverIntegration` 回归 | 6 项，0 failed / 0 error |
| ATR-RUN-053 | 最终当前任务提示定向回归 | 12 项，0 failed / 0 error |
| ATR-RUN-069 | 提示回归初次运行 | 11/12 通过；唯一失败为断言仍使用旧提示文本，未涉及产品逻辑或 Provider；修正断言后由 RUN-070 复跑 |
| ATR-RUN-070 | 最终提示回归 | 12 项，0 failed / 0 error |
| ATR-RUN-071 | 最终 `office_engine_m3` 全量回归 | 60 项，0 failed / 0 error |
| ATR-RUN-072 | 最终 M2 `TestOfficeRetrieverIntegration` | 6 项，0 failed / 0 error |
| ATR-RUN-073 | Provider 合成数据清理复核 | 14 个可解析 Provider 运行及 v0.3 审计 Thread 均经 ORM 核对；无测试用户、Thread、合成 partner 残留，国家记录仍存在，审计 allowlist 恢复 `1398`；PASS |

命令日志、Provider 原始审计、测试结果 JSON 和 Oracle 评估保存在 `office_engine/docs/implementation/evidence/CC-M4-02/`。所有数据库命令均使用现有库 `odoo18e_llm`。

## 5. Domain 子项分析与范围边界

1. Odoo 18 的 `res.partner.company_type` 是 `store=False` 且无 `search` 方法的计算 Selection；原始 ORM 会把对应 Domain 叶子忽略。
2. Odoo 源码依据：`odoo/osv/expression.py` 的 Domain 解析对 `not field.store` 后检查 `field.search`；两者都没有时产生 dummy/empty Domain。`odoo/fields.py` 中 `_description_searchable` 定义为 `bool(store or search)`，related-field setup 也按 related 目标是否 searchable 决定是否提供 `_search_related`。
3. 生产代码现在只在 Domain 路径使用此 ORM 可搜索性检查；其它字段存在校验不变。对每段路径若 `not field.store and not field.search`，在 `search_count/search_read` 前返回既有 `INVALID_QUERY` 并指出完整路径。不会仅凭 `store=False` 拒绝合法计算字段。
4. TransactionCase 对照原始 ORM 查询证明 `company_type=person` 返回同一标记下的 person 与 company；同一 Domain 经 Retriever 被拒绝。`is_company`、自定义 computed `display_name`、related `country_code`、关系路径和 legacy search 均由普通用户合成数据核对。
5. Provider focused v0.2 实际收到错误，Agent 后续宽查后最终数据与 Oracle 相符，但宽查返回 9 个 ID（Oracle 目标 4 个），未使用等价 `is_company` Domain。因此 Provider 的错误边界通过，Agent 等价 Domain 重规划没有通过该观察；该最终输出不替代 ORM Domain Oracle 证据。
6. 复杂 Provider RUN-029 的 Domain 使用错误关系值后返回 0，是 Agent 记录值解析/规划失败，不是 ORM 忽略条件。该样例被如实标为 FAIL，留给负责人决定是否属于当前 CC 的后续整改范围；本轮没有把它修成针对性特例。

## 6. 安全与数据清理

| 检查 | 结果 |
|---|---|
| 数据库 | 仅 `odoo18e_llm`；没有数据库创建操作 |
| Provider 数据 | 合成业务话术、测试用户创建的合成记录、Registry 元数据和工具 Schema；无真实业务记录、Oracle 答案或凭据 |
| 查询权限 | Retriever 用普通测试用户 ORM；没有 SQL、RPC 或业务查询 sudo |
| 内部审计 | 仅测试观测 allowlist 的读取使用 sudo；环境开关、绝对路径和 Thread 白名单均须匹配 |
| 清理 | Thread、测试用户、合成联系人及测试 Bus 事件均已复核为 0；Provider usage 审计保留 |
| Git | 未提交、未推送；没有将其他工作区变更纳入本 CC |

## 7. 证据清单

- IHR：`IHR-CC-M4-02.md`
- 实施报告：`evidence/CC-M4-02/CC-M4-02_Final_Report.md`
- 最终回归：`ATR-RUN-018_m3_full_regression_final.log`、`ATR-RUN-019_m2_retriever_regression_final.log`
- Provider v0.4：`provider_constraints_v0.4_result.json`、`provider_constraints_v0.4_sdk_audit.jsonl`、`provider_constraints_v0.4_oracle_validation.json`
- Provider v0.5 实验：`provider_constraints_v0.5_result.json`、`provider_constraints_v0.5_evaluation.json`、`provider_constraints_v0.5_sdk_audit.jsonl`
- 最终 ORM 核对：`ATR-RUN-020_postrun_orm_check.log`
- 其他初次失败、调试、清理和单测日志：同目录 `ATR-RUN-001` 至 `ATR-RUN-017`。

## 8. 最新关系失败 RCA 与修复证据

### 8.1 已确认根因

Thread 1688 的 `discover` 返回模型候选而不是记录值；`describe(limit=1)` 首页只返回 198 个字段中的 1 个且 `has_more=true`；Agent 将父公司名称片段直接作为 `parent_id`、将国家显示名直接作为 `country_id`，未用成功查询结果解析外键 ID。该 Domain 类型/语义错误由 ORM 正常执行并返回零条，目标合成记录由隐藏 Oracle 独立证明存在。字段/关系查找不完整、错误关系 ID 和零结果被当成任务结论，是 Agent 规划缺口；不是 Retriever 静默忽略条件。

`provider_constraints_v1.0` 另确认并行 Retriever 调用后 Provider 历史缺少某一兄弟 `tool_call_id` 的响应，OpenAI 返回 HTTP 400。CC 范围内通过单次响应只执行一个 Retriever 调用保持每次工具回执有序；不修改上游框架或创建恢复机制。

### 8.2 宽候选查询的准确判定

在 `provider_domain_precision_v0.2` 中，`INVALID_QUERY` 后的结果查询返回全部 9/9 候选、`has_more=false`，且结果字段覆盖所需后筛选值，独立 Oracle 核对最终 4 个身份相同。因此该执行是符合完整执行链要求的完整候选集加确定性后筛选，不是遗漏约束或分页不足；它不证明宽 Domain 等价。此现象与 Thread 1688 收到 `describe(query=...)` 后使用错误关系值并不相同。

### 8.3 最小修复

`office_engine_m3/models/llm_thread.py::_prepare_chat_kwargs()` 的现有通用 Retriever 指引补足：读完所需 describe 元数据页；依 `relation` / `rec_name` 先搜索业务显示值，Domain 只用成功结果的 ID；子记录依据已确认父 ID 批量查询并保留其返回父 ID；一个 assistant 响应只发一个 Retriever 调用；错误调用不提供有效记录，宽候选集必须完整分页且可确定性覆盖所有约束。没有新增工具、Schema、错误码、模型/字段规则或权限路径。

### 8.4 v1.1 独立 Oracle 结果

普通内部用户没有 Contacts Manager 权限。第一轮用元数据确认 `res.partner.parent_id`、`country_id`、`is_company` 与 `res.country.name`；按父公司和国家显示名查询获得唯一 ID；最终 Domain 包含日期边界、active、父 ID、国家 ID 和个人类型，得到两个精确 Oracle 身份。第二轮当前用户只改目标对象为公司并加子联系人要求，Agent 保留其他条件，先得到两个父公司 ID，再用 `parent_id in [IDs]` 批量查询联系人。子项的 `parent_id` 映射与各自公司 ID 一一吻合。所有页 `has_more=false`，decoy 排除，用户答案名称/邮箱与 Oracle 一致。11/11 Provider 请求响应、0 SDK 错误，11 次内无一条请求出现多个 Retriever 调用。

### 8.5 业务歧义探索状态

“统计客户总数”两次探索都产生 `customer_rank > 0` 查询和 0 结果。该任务本身及其 Oracle 没有定义“客户”是所有 partner 还是按 Odoo Customer Rank 分类；因此该 0 不能作为业务错误证据。另设明确可判定的自关联层级夹具：直接个人联系人为 2、所有后代公司下个人联系人为 6，身份集合不同。v0.4～v0.7 Agent 曾自行选直接范围、遗漏对象条件或无查询报零，均按真实 FAIL 保留；v0.9 在最终提示下先向用户澄清，未查询目标记录，符合 Oracle。该结果仅证明本次歧义分支，不抹除前述失败或此前 NOT SCORABLE 的客户口径探索。

### 8.6 条件错误恢复与无查询报零

RUN-066 使用明确“直接关联”的合成任务。Agent 完成 discover/describe 和父记录名称解析后，未发出目标记录 `search` 即回复 `0`；隐藏 Oracle 中有 2 条合格记录，因此确认“无查询/无结果被解释为零”是直接失败事实。随后在任务指引中补充：不可静默删除 `INVALID_QUERY` 谓词；候选计数不是最终计数；数值答案（特别是零）必须由成功完整查询或完整确定性筛选支持。RUN-067 复测中 Agent 的 `company_type` Domain 再次收到 `INVALID_QUERY`，随后按 `describe` 提供的信息改用可搜索 `is_company=false`，其余日期、国家、有效状态和直接父 ID 仍在 Domain 中，ORM 返回 2 条，身份及最终数字均与隐藏 Oracle 一致。该改动是现有 Agent 指引，不是 CC-M4-03 通用恢复框架。

自关联歧义规则依据 `parent_id` 的实际自关联 `relation` 元数据，不硬编码特定模型或字段。最终 RUN-068 的 Provider 请求含该规则，Agent 询问“直接挂在公司下”或“包括所有下级公司”后代的范围选择；目标记录搜索调用数为 0。直接与后代计数的差异由独立 ORM Oracle 确认。历史 v0.3 原始 SDK 审计显示此前回答 `2`，但其同名结果 JSON 因重跑保护脚本异常写入被覆盖；原审计保留，重跑错误另存，不将受损 JSON 冒充原始测试结果。

## 9. 最终验收状态

- CC-TEST-001：**PASS**，v1.1 关系查询和 RUN-067 `INVALID_QUERY` 后合法替代条件均由普通用户、真实 Provider 和隐藏 Oracle 核对。
- CC-TEST-004：**PASS（目标路径）**，v1.1 验证动态元数据/父子关系规划，RUN-068 验证自关联歧义先澄清；v0.4～v0.7 的真实失败仍留作历史证据。
- CC-TEST-005/006：**PASS**，既有 operation-specific 拒绝、Domain fail-closed、普通用户 ORM 和完整候选后筛选边界均保留证据。
- CC-TEST-008：**PASS**，最终提示回归 12 项、M3 60 项、M2 Retriever 6 项及 ORM 清理核查通过。
- 失败与边界：RUN-029、v0.4～v0.7 FAIL 保留；RUN-047/049 的“客户”口径仍为 NOT SCORABLE；v0.3 原始审计的结果 JSON 覆盖事故和恢复边界已明示。

**关闭状态：** 项目负责人于 2026-11-20 批准按冻结验收范围关闭 CC-M4-02。关闭依据及契约逐项评估见 [FR-CC-M4-02](FR-CC-M4-02.md)；本 ATR 中 RUN-029、RUN-063～066 等原始失败、NOT SCORABLE 探索和 v0.3 结果 JSON 覆盖事故均继续保留。
