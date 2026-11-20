<!--
模板来源：office_engine/docs/skill/odoo-project-workflow/references/templates/Coding/IHR模板.md
本文件状态：实施历史记录；CC-M4-02 已由负责人于 2026-11-20 按冻结验收范围批准关闭。历史实施与失败记录保持原样。
-->

# IHR — CC-M4-02 意图理解与任务规划

## 0. 文档治理

本记录记录冻结 CC-M4-02 v0.2 的实施事实，不替代冻结 CC，不自行宣布关闭。工作区在本 CC 实施前已有其他未提交和未跟踪的代码、文档变更；本轮未清理、暂存、提交或推送这些内容。以下文件级说明只认领本 CC 对应的改动。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | CC-M4-02 |
| CC | `CC-M4-02_意图理解与任务规划_v0.2.md`；FROZEN |
| 上游 | M4 TDD v0.2 FROZEN WITH OPEN ITEMS；Implementation Plan v0.1 FROZEN |
| 模块 | `office_engine_m3` |
| 数据库 | 仅使用 `odoo.conf` 指定的现有 `odoo18e_llm`；未创建数据库 |
| Provider | OpenAI GPT-5.6 Luna / `gpt-5.6-luna` |
| 分支 / HEAD | `codex/cc-m4-02-intent-planning` / `46ff8e96fed2e7eee47494bcfb9d52e1f0c84512` |
| 执行日期 | 2026-11-20（Asia/Shanghai） |
| 当前状态 | 负责人于 2026-11-20 批准按冻结验收范围关闭；CC-TEST-001/004 有真实 Provider + 独立 Oracle 目标场景证据，v0.4～v0.7 失败保留。关闭评估见 `FR-CC-M4-02.md` |

## 2. 实施摘要

| CC 项 | 实施事实 | 证据位置 |
|---|---|---|
| CC-CHANGE-001/002：当前任务连续性 | 在 `llm.thread._prepare_chat_kwargs()` 中加入通用当前任务指引：当前用户最新明确要求只覆盖冲突条件；保留其余要求；允许依赖 `discover`、`describe` 和只读结果动态调整；完成声明前对照可观察结果；不采集或输出隐藏推理 | `office_engine_m3/models/llm_thread.py`；`tests/test_silent_retrieval.py::test_current_task_rules_preserve_latest_user_instruction_and_unmodified_constraints` |
| CC-CHANGE-003：`search(query=...)` | 对 operation 缺省的旧 search，以及 `search` / `describe` 中非空 `query`，在 ORM 查询前返回既有 `INVALID_QUERY`；`discover(query=...)` 仍有效；不改变公开工具名和响应形状 | `office_engine_m3/models/llm_tool.py`；`tests/test_retriever.py::test_discovery_query_is_rejected_for_describe_search_and_legacy_before_orm` |
| CC-CHANGE-004：错误与零结果 | 既有结构化错误及成功零结果语义保持；普通用户合成 ORM 查询覆盖父子关系、日期、国家、布尔状态、排序和分页 | `office_engine_m3/tests/test_retriever.py::test_ordinary_user_retrieves_synthetic_parent_country_date_and_child_data`；`ATR-RUN-018_m3_full_regression_final.log` |
| Domain 精确性修复 | Odoo 18 ORM 可搜索条件按 `field.store or field.search` 判断；Domain 逐段拒绝非存储且无 search 实现字段，使用既有 `INVALID_QUERY` 并指出字段路径；不影响字段读取/排序校验、合法计算字段、自定义 search、related search 或 legacy search | `office_engine_m3/models/llm_tool.py::_retriever_validate_field_path()`；`tests/test_retriever.py::test_domain_rejects_nonsearchable_computed_field_before_orm`；`test_domain_accepts_stored_custom_search_and_related_search_fields_for_ordinary_user`；ATR-RUN-031 |
| Agent 查询规划指引 | 通用指引要求先读取实际返回的元数据、按 `rec_name` 查出关系 ID、按父 ID 查询子记录；遇到自关联且未说明深度先澄清；`INVALID_QUERY` 后不得静默删除条件，失败/未执行查询不得作为零计数 | `office_engine_m3/models/llm_thread.py::_prepare_chat_kwargs()`；`tests/test_silent_retrieval.py::test_current_task_rules_preserve_latest_user_instruction_and_unmodified_constraints`；Provider RUN-067/068 |
| Provider 审计测试门禁 | 为使普通业务用户下的 Provider 集成可使用测试专用审计白名单，仅对白名单 `ir.config_parameter` 读取使用 `sudo()`；不改变 Retriever 的用户身份，不读取或查询业务记录 | `office_engine_m3/services/provider_request_audit.py`；`tests/test_m4_tv_test_hooks.py::test_provider_audit_requires_test_switch_database_absolute_path_and_allowlisted_thread` |
| 旧调用和 M2/M3 兼容 | 保留唯一 `odoo_record_retriever`、现有 Tool Schema、legacy search、ACL / Record Rules、分页和 Candidate 行为；完整 M3 与 M2 Retriever 定向回归执行通过 | ATR-018、ATR-019 |

## 3. 实施历史（仅追加）

### IHR-001 — 现有基线测试与合成数据权限修正

早期 TransactionCase 先后遇到合成用户缺少创建联系人分类或联系人所需的 Odoo 原生组、测试国家数据不可读等夹具问题。修正后以普通内部用户及 Odoo 原生联系人管理组创建隔离记录；查询仍以该普通用户执行 `odoo_record_retriever`。这些早期权限拒绝是测试夹具权限不足，不是 Retriever 绕过权限的依据。原始日志保留于 `evidence/CC-M4-02/ATR-RUN-001` 至 `ATR-RUN-008`。

### IHR-002 — 当前任务约束指引与 operation 参数拒绝

增加最新用户指令优先、局部变更保留和依据元数据/只读回执动态调整的通用系统指引。对已知只适用于 `discover` 的 `query`，在 operation 分发点拒绝其用于 `search`、`describe` 和 legacy search，错误沿现有 `RetrieverToolError` 转为 `INVALID_QUERY`；拒绝发生在模型解析或 ORM 查询之前。没有改变公共 Tool Schema，亦未增加全局严格参数白名单。

### IHR-003 — 普通用户 ORM 夹具与审计门禁

通过 ORM 建立短生命周期的联系人父记录、公司/联系人子记录和 decoy；独立 Oracle 只保存在测试脚本，不写入 Agent 消息或 Provider 请求。真实 Provider 运行时发现审计 allowlist 用当前业务用户读取 `ir.config_parameter` 会触发 `ACCESS_DENIED`，导致测试观测失败被误当作业务查询错误。修复仅在测试观测开关、绝对审计路径及 Thread 白名单都满足后，以 `sudo()` 读取服务器侧 allowlist；实际工具依然使用普通测试用户 ORM 权限。相应隔离回归通过。

### IHR-004 — 真实 Provider 两轮合成任务（有效基线 RUN-013）

Thread 1601 绑定 `odoo_record_retriever` 与 `office`，运行于 `odoo18e_llm`。GPT-5.6 Luna 完成两轮对话：第一轮列出合成父公司下、给定日期/国家/有效状态的个人联系人；第二轮把对象改为公司账户并补充各账户联系人，保留日期、国家、有效状态和父公司要求。实际 SDK 审计记录 11 个请求、11 个响应、0 个 SDK 错误：9 个请求包含冻结的两个 Tool Schema，另 2 个为不带工具的内部模型请求；Retriever 共调用 8 次，Office 0 次。独立 Oracle 对两轮最终业务答案逐项核对通过，未写入文件。运行耗时为 24.018 秒和 7.684 秒。

### IHR-005 — Domain 搜索性探索及范围撤回

RUN-013 中发现 Agent 使用 `res.partner.company_type` 作为类型 Domain。Odoo Registry 显示该字段 `store=False`、无 ORM `search` 方法；定义位于 `odoo/addons/base/models/res_partner.py:290-294`，源码注明它是界面字段。`office_engine_m3/models/llm_tool.py::_retriever_validate_domain()` 当前验证字段路径存在，不验证 ORM 可搜索性。实际 ORM 查询将该谓词忽略，两个类型查询都返回 4 行（Oracle 目标各为 2 行）。Agent 依据已返回的值在最终回答中正确筛选，因此 RUN-013 的两轮最终输出仍与 Oracle 相符，但不能证明 Domain 选择性正确。

曾试做一个通用 fail-closed 校验并运行隔离 Provider 实验 RUN-017。该行为不在冻结 CC 对 Retriever 的 operation 参数修复范围内，会改变既有查询行为；且复验第一轮 Agent 因无效关系值和零结果报告未完成，第二轮才成功。该实验代码已撤回，未保留在最终产品代码；RUN-017 的请求、失败和恢复记录完整保留。该观察作为待评审技术发现，不以实验失败或结果修改历史基线。

### IHR-006 — 回归、清理与环境复核

最终 `office_engine_m3` 全量测试 58 项、0 failed、0 error；M2 `TestOfficeRetrieverIntegration` 6 项、0 failed、0 error。随后通过 Odoo ORM 只读核对 `office_engine_m2` 和 `office_engine_m3` 均 installed 且版本与清单一致，合成用户/联系人/Thread 为 0，审计白名单恢复为原值 `1398`。历史一次失败运行留下的孤立合成 reader 联系人 ID 22615 已确认无关联用户后，通过 ORM 定向删除，并复核剩余为 0。Provider usage 审计保留。

### IHR-007 — Domain fail-closed 修复及最终复测

对照 Odoo 18 `odoo/osv/expression.py` 的 Domain 解析：非存储字段没有 `field.search` 时，ORM 将 Domain 叶子转换为空条件；`odoo/fields.py` 的 `_description_searchable` 与 related-field setup 则按 `store or search` 暴露搜索能力。本次以相同运行时判定实现通用前置检查，不按 `store=False` 单独拒绝，不增加公开参数或错误码。Domain 每一段字段路径均检查，非法项在 Retriever 调用 `search_count/search_read` 前以 `INVALID_QUERY` 拒绝并带出问题字段路径。

普通用户合成记录测试直接用原始 Odoo ORM 证明 `company_type=person` 被静默忽略并返回 person/company 两条记录；同一组记录经 Retriever 则在 ORM 前拒绝。另验证 `is_company`、非存储且有自定义 search 的 `display_name`、由 related 目标字段生成 search 的 `country_code`，以及 dotted relation、`in/not in` 和 legacy search 仍工作。最终 `office_engine_m3` 全量 60 项、M2 Retriever 集成 6 项均为 0 failed / 0 error；M3 manifest 与已安装版本为 `18.0.7.0.5`。

最终真实 Provider 证据区分工具修复与 Agent 计划：focused run `provider_domain_precision_v0.2` 中，GPT-5.6 Luna 实际收到 `company_type` 的 `INVALID_QUERY`，该失败调用没有结果；Agent 随后执行不含类型条件的宽查询，检索 9 个记录，并根据返回的可读字段值给出与 4 个合成 Oracle 身份相符的最终结果。该 Provider 轨迹证明错误已传达、错误没有被当作成功查询，也证明模型没有采用等价 `is_company` Domain；其宽查询不作为 Domain 与 Oracle 相等的证据。

最后的复杂两轮 Provider run `provider_constraints_v0.7` 仍未完成任务：Agent 在 Search Domain 中把父公司名称片段当作 `parent_id` 值、把国家名称当作 `country_id` 值，ORM 按收到的合法但错误值返回零条；此外它一次 `describe` 携带 `query`，被既有校验正确拒绝。Agent 最后报告零结果，未包含 Oracle 记录。此项属于本次观测到的关系值规划失败，不是 ORM 静默忽略，也未在本次 Domain 修复范围内改写。Thread、测试用户和合成联系人均由脚本 ORM 清理；最终只读核对计数为 0，审计白名单恢复 `1398`。

### IHR-008 — 关系值解析 RCA 与真实 Provider 复测

按失败线程逐步核对：`discover` 返回的是 Registry 模型候选；Thread 1688 的 `describe(limit=1)` 仅返回 198 个字段中的 1 个且 `has_more=true`，Agent 没有继续拿齐字段；`describe(query=...)` 又被正确返回 `INVALID_QUERY`。随后 `parent_id` 使用父公司名称片段、`country_id` 使用国家显示名，而 Many2one Domain 需要目标 ID；这些值没有来自成功只读查询。ORM 两次合法执行并返回 0，Oracle 证明实际合成目标记录存在。因此根因是 Agent 没有用关系元数据和成功查询解析外键值，且把成功零结果当作业务答案，不是 Retriever 忽略 Domain、ACL 或分页问题。

另行核对了 INVALID_QUERY 后的宽查询。`provider_domain_precision_v0.2` 中，宽查询完整返回 9/9 条、`has_more=false`，并返回确定性筛选所需字段，结果后筛选到的身份与 Oracle 完全相同；按冻结 CC 这属于合法完整候选集处理，不是遗漏条件。它与 Thread 1688 的错误关系值查询是两条独立轨迹。

实现仅更新 `_prepare_chat_kwargs()` 的通用 Retriever 指引：先完成需要字段的 describe 分页；用目标模型的 `rec_name` 搜索业务标签，关系 Domain 只使用成功结果中的 ID；读取子记录时使用已确认父 ID 并保留父子映射；每个 assistant 响应只发一个 Retriever 调用，避免 v1.0 中 Provider 历史缺少兄弟 tool call 回执导致的 HTTP 400；宽候选集必须全页完整且确定性覆盖所有条件。不改 Tool Schema、权限、错误码、模型或 Retriever ORM 行为，不实现 M4-03 通用恢复机制。

真实 Provider v1.1 以普通内部用户完成两轮任务：首轮发现/描述 partner 与 country 字段，分别查询父公司和国家取得 ID，然后用日期、有效状态、父记录 ID、国家 ID 与个人类型条件查到 Oracle 的两位联系人；第二轮按用户最新指令查询两家公司，并用 `parent_id in [公司 ID]` 批量查到两位子联系人，返回的父子 ID 映射与 Oracle 一致。11/11 Provider 请求响应、0 SDK 错误；请求每次至多一个 Tool Call；所有查询页完整，decoy 不出现，Oracle 未注入 Provider。

补充的 `客户总数` 探索两次均得到 customer-rank 查询的 0，但该用例 Oracle 把所有关联 partner 定义为“客户”，而原始请求没有此定义且 Odoo 元数据包含 `Customer Rank`。因此两次结果记为 NOT SCORABLE，不当作 Agent FAIL 或 PASS。它们不修改产品代码。完整轨迹与 Oracle 边界见 `../verification/m4_rca/RCA-009_CC-M4-02_Relation_Query_Planning.md`。

最终提示定向回归 12 项、M3 全量 60 项、M2 Retriever 6 项全部 0 failed / 0 error；ORM 清理复核确认 6 次 Provider 场景的用户、Thread、合成联系人均无残留，审计 allowlist 恢复 `1398`。证据为 `ATR-RUN-043`、`047`、`049`～`053` 及相应 JSON / SDK audit 文件。

### IHR-009 — `INVALID_QUERY` 后精确恢复与自关联范围澄清

最新真实 Provider 复测发现两个相关但不同的问题。第一，Agent 能收到 `INVALID_QUERY`，但在一个测试中将被拒的 `company_type` 条件静默删除，返回含两家公司和两个人的候选集并回答 4；另一个测试中完成 metadata 和目标公司解析后，没有执行目标记录 `search` 就回答 0。第二，在父子模型自关联的“公司下面”查询中，Agent 曾按直接父关系给出单一数值，没有询问是否包括所有下级公司。

最小修复仍限于 `_prepare_chat_kwargs()` 的通用指引：

- 对数值计数，只有成功且完整的 search 或完整候选集确定性筛选才能报告；没有搜索、搜索失败或页未齐不等于零。
- 收到 `INVALID_QUERY` 后不得静默删除被拒谓词；必须用元数据确认的可搜索等价条件，或在完整候选集具备所有必要字段时先筛选全部约束再计数，否则说明无法确定。
- 若 `describe` 显示目标模型存在指回自身的关系，而用户说“under/下面/关联”等但未说明层级，不能从默认直接父关系推断业务范围；先询问直接关联还是所有后代。此规则根据实际 Registry 关系元数据触发，不指定特定模型或字段。

真实 Provider 结果：RUN-063～066 保留了规则未生效或计数不完整的 FAIL；RUN-067 在 `company_type` 被拒后用已描述的 `is_company=false`、保留日期/国家/active/直接父 ID，返回与隐藏 Oracle 一致的两条个人记录；RUN-068 在“直接 2 vs 所有后代 6”的 Oracle 下先询问范围，没有调用目标记录 search，也未报数。RUN-067 为 9/9 请求响应、0 SDK 错误；RUN-068 为 8/8、0 错误。二者皆使用普通内部用户和现有 `odoo18e_llm`，独立 Oracle 未传入 Provider。

同标签保护调查还发现测试 Runner 异常：v0.3 SDK 审计已存在时，重跑保护虽拒绝新 Provider 调用，但外层异常处理仍覆盖了同名结果 JSON。我们将拒绝重跑的错误副本保存在 `provider_hierarchy_ambiguity_v0.3_retry_guard_result.json`，原 SDK 审计完整保留；RUN-073 通过 ORM 从审计中恢复校验 Thread 1911 与唯一后缀，确认无测试用户/Thread/partner 残留。后续隔离 Runner 增加最外层证据存在检查，避免发生同类覆盖。

验证结果：RUN-070 提示组装 12 项 0 failed/error；RUN-071 M3 全量 60 项 0 failed/error；RUN-072 M2 Retriever 6 项 0 failed/error；RUN-073 ORM 清理与审计 allowlist 复核 PASS。初次 RUN-069 唯一失败是测试断言仍匹配旧提示文本，修正断言后通过 RUN-070。

## 4. 保留的失败与未解决项

| 项目 | 当前判定 | 说明 |
|---|---|---|
| `search(query=...)` 实际 Provider 错误调用 | 组件边界通过；Provider 自主发出该无效组合未观测 | 真实 SDK Schema 和合法调用已审计；execute 的无效调用由确定性测试验证在 ORM 前返回 `INVALID_QUERY`。不把“模型未生成无效调用”虚报成 Provider 负向调用通过 |
| `company_type` Domain | **Retriever fail-closed 及本次 Provider 合法重规划 PASS；历史失败保留** | RUN-067 中 `company_type` 被拒后，Agent 使用元数据描述可搜索的 `is_company=false`，并保留日期、国家、active 和直接父 ID，Oracle 目标身份完整匹配。更早 focused run 的宽查询及 RUN-063～066 失败均保留 |
| CC-TEST-001 复合查询；CC-TEST-004 动态规划/澄清 | **目标用例 PASS；历史 RUN-029、RUN-063～066 FAIL 保留** | RUN-043 / RUN-067 核对条件、身份和关系；RUN-068 在直接与后代范围计数不同的自关联层级数据上先澄清，未搜目标记录或报数。完整证据见 ATR / RCA-009 |
| 歧义探索 `客户总数` | **NOT SCORABLE** | 两次都将“客户”理解为 `customer_rank > 0` 并返回零；测试 Oracle 未定义客户口径，无法用“所有关联 partner”这一假设判定对错 |
| 失败恢复 | 本 CC 证据有限 | RUN-017 中第一轮 Agent 未从错误/零结果恢复，第二轮在新用户要求下恢复；错误恢复策略与有界重试仍应按 CC-M4-03 验收 |
| 最终 UI / Office 写入 | N/A | 本 CC 明确不执行 UI HVR、Office 写入、Candidate 或文件验收；由 CC-M4-05 覆盖 |

## 5. 安全、兼容与交付边界

- 所有 Odoo 命令显式使用 `-c odoo.conf -d odoo18e_llm`；未创建数据库、未访问生产库、未执行直接 SQL 或 RPC。
- Provider 只收到自然语言合成任务、Registry 元数据及工具 Schema；未发送真实业务记录、独立 Oracle 标签或凭据。
- 真实工具调用使用普通 Odoo 用户；内部测试审计读取 `ir.config_parameter` 的局部 `sudo()` 不进入业务搜索。
- 未增加公开工具/参数/响应字段，未修改 M2/M3 冻结文件生命周期或用户确认门禁。
- 本轮未提交或推送 Git。工作区的其他修改保持原样。

## 6. 当前状态

Thread 1688 的错误关系值问题由 v1.1 复测通过；新增错误条件恢复和自关联澄清分别由 RUN-067、RUN-068 通过真实 Provider、普通用户 ORM 和独立 Oracle 验证。v0.4～v0.7 的失败仍保留为 Provider 行为不稳定证据，“客户总数”探索继续标为 NOT SCORABLE。项目负责人已于 2026-11-20 按冻结验收范围批准关闭 CC-M4-02；逐项关闭判断见 `FR-CC-M4-02.md`。
