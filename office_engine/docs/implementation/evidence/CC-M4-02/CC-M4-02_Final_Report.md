# CC-M4-02 实施与验收报告

## 评审状态

**项目负责人已于 2026-11-20 批准按冻结验收范围关闭 CC-M4-02。** 本轮目标路径有真实 Provider、普通 Odoo 用户 ORM 和独立隐藏 Oracle 的 PASS 证据；v0.4～v0.7 中 Agent 未澄清、条件遗漏或无查询报零的失败继续保留，反映真实 Provider 行为波动。正式逐项 Closure Assessment 见 [`FR-CC-M4-02.md`](../../FR-CC-M4-02.md)。

只使用 `odoo.conf` 指定的现有开发库 `odoo18e_llm`。Provider 为 OpenAI GPT-5.6 Luna / `gpt-5.6-luna`。没有创建数据库、访问生产环境、执行 SQL/RPC、使用 Retriever sudo 或修改冻结 CC。

## 1. 最新失败样例 RCA

原始 FAIL 为 Thread 1688 / `provider_constraints_v0.7`，原始记录继续保留。

| 阶段 | 观察到的事实 | 原因归类 |
|---|---|---|
| 原始用户要求 | 指定创建日期、有效状态、直接上级公司、国家和个人联系人；第二轮只改成公司账户并补充其联系人，要求保留其余条件。 | 约束本身充分，没有需要用户澄清的业务歧义。 |
| `discover` | 返回 Registry 模型候选，不提供业务记录 ID。一次返回 757 个候选中的 100 个，`has_more=true`。 | Agent 将模型发现结果当成足以查询字段/记录的依据。 |
| `describe` | 初次 `limit=1` 只返回 `res.partner` 198 个字段中的 1 个，`has_more=true`；Agent 没有补齐关系所需字段。另一次把 `query` 传给 `describe`，被正确拒绝为 `INVALID_QUERY`。 | 元数据页没有读完，且模型候选发现与字段描述职责混淆。 |
| 关系值与 Domain | `parent_id` 直接使用名称片段 `0712d5fff7d2`，`country_id` 使用显示值 `Andorra`。这两个 Many2one Domain 都要求目标记录 ID，且失败请求前没有成功查询返回这些值。 | Agent 把用户可读标签当作外键 ID，错误值来自猜测而非有效工具回执。 |
| ORM 与 Oracle | ORM 按收到的 Domain 成功返回 0，`has_more=false`；独立隐藏 Oracle 有满足用户原条件的合成记录。 | 不是 Retriever 忽略 Domain、权限拒绝或分页截断；Agent 把合法零结果错误地当成完整业务答案。 |
| 子记录处理 | 先前失败版本曾复用此前的个人记录而没有证明它们属于公司账户。 | 子记录必须依据关系元数据，以已确认父 ID 查询，并保留每条子记录的返回父 ID。 |

完整调用与每阶段证据见 [RCA-009](../../../verification/m4_rca/RCA-009_CC-M4-02_Relation_Query_Planning.md)、`provider_constraints_v0.7_result.json`、`provider_constraints_v0.7_sdk_audit.jsonl` 和 `ATR-RUN-029_provider_constraints_final.log`。

## 2. `INVALID_QUERY` 后宽查询的性质

另一个 focused run `provider_domain_precision_v0.2` 收到不可搜索字段的 `INVALID_QUERY` 后，Agent 选择了较宽的候选查询。该查询实际返回全部 9 条候选，`has_more=false`，并包含后筛选所需字段；对完整集合确定性筛选后，最终 4 个身份与独立 Oracle 完全一致。

因此该样例是合法的“完整候选集 + 结果后筛选”，不是条件遗漏或分页不完整。它不等价于 Retriever Domain 精确，也没有替代 `INVALID_QUERY` fail-closed 自动化证据。Thread 1688 则是另一条轨迹：Agent 未解析关系 ID，ORM 得到零结果；两种情况没有混为一谈。

`provider_constraints_v1.0` 还暴露独立 Provider 续接问题：同一个 assistant 响应发出两个 Retriever 调用，但下一次 Provider 消息缺少其中一个 `tool_call_id` 的工具结果，OpenAI 返回 HTTP 400。CC 范围内的最小处理是在当前任务指引中要求每个 assistant 响应只调用一次 Retriever 并等待回执；没有改上游框架、公开工具契约或新增 CC-M4-03 恢复框架。

## 3. 最小修复

在 `office_engine/office_engine_m3/models/llm_thread.py::_prepare_chat_kwargs()` 补充现有 Retriever 的通用任务指引：

- `discover` 返回模型候选，不代表字段定义或记录命中；`describe` 分页必须读到查询需要的实际字段。
- 使用关系字段元数据确认目标模型和 `rec_name`，通过成功查询把业务显示值解析成记录 ID；Many2one Domain 只使用用户或成功只读结果提供的 ID。
- 查询选定父项的子记录时依据关系/反向字段用 `in` 查询，并保留每个子项真实返回的父 ID。
- 不对任意 ID 或无关业务记录探测；每个工具调用都应支持当前用户目标。
- `INVALID_QUERY` 不可被静默删除；以元数据确认可搜索的替代条件，或仅在完整分页且全部谓词值可用时先确定性筛选再计数。失败或未执行的查询不能回答为零。
- 对自关联模型，若“under/下面”等表述未说明直接关联或所有后代，先向用户澄清；不得用当前最可能的直接关系代替用户选择。
- 每个 assistant 响应只发一个 Retriever 调用，等待对应结果后再规划下一步。

未新增工具、Schema、错误码、模型、业务字段或业务专用规划器；未改变 Domain fail-closed、ORM 权限、legacy search、M2/M3 文件生命周期或用户确认门禁。

## 4. 真实 Provider 与独立 Oracle 复测

`provider_constraints_v1.1` 使用新的 ORM 合成记录和普通内部用户（没有 Contacts Manager 权限），共 11 个 Provider 请求、11 个响应、0 个 SDK 错误。Oracle 保存在测试脚本/结果文件，不单独发给 Agent。

| 步骤 | Provider 实际行为 | 独立 Oracle |
|---|---|---|
| 模型与字段 | 发现 `res.partner` 候选；描述 `res.partner` 的所需字段及 `res.country`；实际读取 `parent_id`、`country_id`、`is_company` 等关系/条件字段。 | 字段和值来源与合成模型/关系一致。 |
| 关系值解析 | 先按父公司和国家 `rec_name` 搜索，各返回唯一一条并取得 ID。 | ID 与 Oracle 记录身份一致；没有使用猜测字符串。 |
| 第一轮复合条件 | 日期上下界、有效状态、父公司 ID、国家 ID、个人类型合并查询，返回 2 条且 `has_more=false`。 | 返回身份与期望的两个个人联系人完全一致；姓名和邮箱逐值匹配。 |
| 第二轮用户修改 | 用户只把对象改成公司账户并要求补上联系人。Agent 保留日期、状态、父公司、国家约束，先查到 2 个公司账户。 | 公司 ID 集合与 Oracle 一致。 |
| 子记录批量查询 | 以两个公司 ID 构造 `parent_id in [...]`，返回 2 个子联系人且 `has_more=false`。 | 每个子记录的 `parent_id` 与正确公司一一对应；姓名和邮箱正确，decoy 不出现。 |

每轮每个 assistant 响应最多一个 Retriever 调用；没有 Office 调用，因为用户明确要求只在聊天中回答且不创建文件。Oracle 验证结果为 PASS：`provider_constraints_v1.1_oracle_validation.json`。原始 Provider 请求和响应审计、完整工具参数/结果分别在 `provider_constraints_v1.1_sdk_audit.jsonl` 和 `provider_constraints_v1.1_result.json`。

## 4.1 后续错误恢复与关系歧义复测

为进一步检查“收到 `INVALID_QUERY` 后的宽查询”以及自关联关系规划，继续使用普通内部用户、全新合成父子数据和独立 Oracle 做真实 Provider 复测。Oracle 不进入用户消息或 Tool 参数。

| Run | 观察与 Oracle | 判定 |
|---|---|---|
| v0.4 / ATR-RUN-063 | 自关联元数据已发现；Agent 收到 `company_type` 的 `INVALID_QUERY` 后按直接父关系查询并报 2，未澄清直接范围还是全部后代范围。Oracle 为直接 2、全部后代 6 | FAIL，保留 |
| v0.5 / ATR-RUN-064 | 实际 Provider 请求已含加强后的自关联澄清规则，Agent 仍回答 2 | FAIL，证明前一版措辞不稳 |
| v0.6 / ATR-RUN-065 | 移除“只报总数”后，Agent 返回直接候选 4，包含 2 公司和 2 个人，遗漏“个人联系人”约束 | FAIL，排除输出格式是唯一原因 |
| v0.7 / ATR-RUN-066 | 对明确要求直接关联的任务，完成元数据及父名解析后未执行目标记录 search，却回答 0；Oracle 有 2 条 | FAIL，确认无查询报零 |
| v0.8 / ATR-RUN-067 | 遇到 `company_type` `INVALID_QUERY` 后改用 `describe` 已确认可搜索的 `is_company=false`，并保留日期、国家、active 和父 ID；返回 2 个准确身份 | PASS，CC-TEST-001 |
| v0.9 / ATR-RUN-068 | 在直接 2 / 所有后代 6 的差异 Oracle 下，Agent 先询问是否仅直接挂接或包括下级公司；未查询目标数据或报数，8/8 Provider 请求响应 | PASS，CC-TEST-004 澄清分支 |

v0.3 的原始 SDK 审计在运行时已存在（Thread 1911，9/9 请求和响应），并显示 Agent 回答 `2`。同标签重跑被保护逻辑拒绝，但 runner 外层异常处理错误地覆盖了同名结果 JSON。审计仍完整保留；重跑拒绝错误副本为 `provider_hierarchy_ambiguity_v0.3_retry_guard_result.json`，RUN-058 日志标识本次没有新的 Provider 调用。后续隔离 runner 增加最外层存在检查。RUN-073 通过 ORM 核验原审计 Thread 及唯一合成数据后缀已清理。

## 5. 验收与回归状态

| CC 项 | 当前结果 | 证据边界 |
|---|---|---|
| CC-TEST-001 复合条件与真实查询 | **PASS（本轮目标）** | v1.1 每项业务约束、记录身份和父子关系一致；RUN-067 `INVALID_QUERY` 后改用可搜索等价条件，结果身份与隐藏 Oracle 一致。历史 v0.7 / v0.4～v0.7 失败仍保留。 |
| CC-TEST-002 最新用户指令优先 | **PASS** | v1.1 第二轮只修改对象范围并增加联系人，其他有效约束继续成立；另有历史 Oracle 证据。 |
| CC-TEST-003 局部修改条件继承 | **PASS** | 两轮查询与最终输出证明未修改条件保留。 |
| CC-TEST-004 动态元数据与关系规划 | **PASS（本轮目标）** | v1.1 动态发现、字段描述、关系 ID 解析及父子收集通过；RUN-068 在自关联深度影响结果时，按隐藏 Oracle 先澄清而未擅自查询或报数。v0.4～v0.7 的真实失败保留。 |
| CC-TEST-005 operation 参数拒绝 | **PASS** | `describe(query=...)` 的实际 Provider 错误调用收到既有 `INVALID_QUERY`；自动化验证 search/describe/legacy 边界及 discover 兼容。 |
| CC-TEST-006 Provider/Execute/ORM 契约 | **PASS（接口边界）** | 非搜索字段 fail-closed、错误与零结果区分由现有自动化和 focused Provider 证据覆盖；v1.1 合法 Domain 的实际普通用户 ORM 结果与 Oracle 一致。宽候选过滤按完整性而非 Domain 等价评估。 |
| CC-TEST-007 当前权限与零结果 | **PASS（自动化/组件）** | 普通用户执行 Retriever；ACL/Record Rules 与成功零结果语义不变，没有业务查询 sudo。 |
| CC-TEST-008 兼容与回归 | **PASS** | 最终 M3 60 项、M2 Retriever 6 项、提示定向 12 项均 0 failed / 0 error。 |

“统计客户总数”的补充探针 v0.1/v0.2 都由 Agent 按 Odoo `customer_rank > 0` 查询并回答 0。该探针的测试 Oracle 把所有关联 partner 当作“客户”，但原用户请求未定义客户口径，且元数据提供 `Customer Rank`，因此它 **NOT SCORABLE**，不记产品 FAIL 或 PASS。完整原始轨迹保存在 `provider_ambiguity_v0.1_*` 和 `provider_ambiguity_v0.2_*`。该结果不能替代 CC-TEST-004 的歧义验收。

回归证据：`ATR-RUN-070_final_prompt_regression.log` 为 12 项、0 failed/0 error；`ATR-RUN-071_m3_final_regression.log` 为 60 项、0 failed/0 error；`ATR-RUN-072_m2_retriever_final_regression.log` 为 6 项、0 failed/0 error。初次 RUN-069 唯一失败为断言未随提示文本更新，修正后由 RUN-070 通过。`ATR-RUN-073_postrun_orm_check.json` 对本批运行及 v0.3 原始审计 Thread 的清理复核为 PASS。

## 6. 安全、清理及实施边界

- 全部 Odoo 操作使用现有 `odoo18e_llm` 和 ORM；不访问生产环境，不直接 SQL/RPC，不创建数据库。
- Provider 只接收合成业务需求、合成记录查询结果、Registry 元数据和工具 Schema；独立 Oracle 标签未传给 Agent。
- Retriever 使用普通内部用户；没有通过 `sudo()` 放宽业务查询权限。
- `ATR-RUN-073_postrun_orm_check.json` 复核 14 个有可解析结果的 Provider 运行，并从 v0.3 SDK 审计读取 Thread 1911 与唯一后缀；测试用户、Thread、合成伙伴无残留；国家记录存在；审计 allowlist 恢复 `1398`；PASS。
- 没有执行 UI HVR、Office 写入或 Candidate 生命周期验收；没有提交 Git。

## 7. 结论

最初复杂查询失败的直接原因是 Agent 未读取完整关系元数据，也未先用 `rec_name` 查询 Many2one 目标记录，导致外键 Domain 使用显示字符串并返回零。v1.1 和 RUN-067 以真实 Provider、普通用户 ORM 和隐藏 Oracle 证明复合条件及错误条件恢复可正确执行；RUN-068 证明关系层级会改变结果时可先澄清，CC-TEST-001/004 本轮目标场景通过。

**CC-M4-02 已按负责人批准正式关闭。** 真实 Provider 在 v0.4～v0.7 曾违反澄清或条件完整性要求，之后 RUN-067/068 的目标路径通过；这些历史波动和测试 harness 的 v0.3 结果 JSON 覆盖事故均如实保留。未运行 UI HVR，符合中间 CC 范围；下一阶段 CC-M4-03 另行评审，未在本报告中启动。
