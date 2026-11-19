<!--
模板来源：office_engine/docs/skill/odoo-project-workflow/references/templates/Coding/ATR模板.md
模板版本/状态：v1.0.0 Frozen；同步检查 PASS（2026-11-19）
本文件状态：ATR-RUN-005～007 完成；项目负责人于 2026-11-19 批准关闭 CC-M4-01。旧 FAIL 与 P04 首次超时记录保留。
-->

# ATR — CC-M4-01 通用业务对象发现

## 0. 文档治理

本 ATR 记录自动化与真实 Provider / Agent 集成事实。Mock / ORM 通过不替代真实检索结果；失败、阻断、清理及未执行状态均保留。CC-M4-01 不要求 UI HVR。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | CC-M4-01 |
| IHR | `IHR-CC-M4-01.md` |
| CC Version | v0.2 FROZEN |
| Module | `office_engine_m3` |
| Environment | 本地开发环境；数据库 `odoo18e_llm` |
| Framework | Odoo Test Runner / TransactionCase |
| Code Baseline | HEAD `8f7ebd259cda414baae46fa91b1d55948ba481a0` + working tree；变更文件哈希见 `evidence/CC-M4-01/manifest.txt` |
| Execution Date | 2026-11-19（Asia/Shanghai） |
| Executed By | Codex |

## 2. Test Contract Baseline

| 来源 | ID | 验证范围 |
|---|---|---|
| CC | CC-TEST-001～009 | 仅按冻结 CC §11 的测试契约评估 |
| CC Preservation | CC-PRESERVE-001～006 | 公开工具、响应、稳定分页、元数据/业务数据权限与 legacy 兼容 |
| TDD | v0.2 §5.1、§12、§14 | 由 CC 裁剪纳入；此处不新增义务 |

## 3. 当前自动化状态

| 指标 | 数量 / 状态 |
|---|---|
| CC 自动化义务 | 9 项（其中 CC-TEST-007 条件性适用） |
| CC 层 PASS | 8 |
| FAIL | 0 |
| SKIPPED | 1（CC-TEST-007：未采用 Alias，按条件不适用） |
| BLOCKED | 0 |
| Latest Valid Run | ATR-RUN-005（最终真实 Provider / Agent 与双遍历）；ATR-RUN-007（审计隔离调整后的 office_engine_m3 全模块回归） |
| Evidence Baseline Match | Yes；Provider 原始证据、Tool Call 对账、清理记录和 SHA 见 manifest |

## 4. Core Test Contract Coverage Matrix

| CC / TEST | 自动化验证 | Run | 原生结果 | Workflow Evidence Status | 证据 / 说明 |
|---|---|---|---|---|---|
| CC-TEST-001 | 完整 Registry 上 40 条明确意图的真实 Provider Top-5 召回、分页和重复稳定性 | ATR-RUN-005 | PASS | Passed | 最终真实 Provider Retriever Top-5 40/40。对同一 Thread 完成两次完整遍历：每遍 757/757、唯一 757、count 恒为 757，8 页顺序逐页完全一致。旧 18/40 结果仍在 RUN-003/004 保留。 |
| CC-TEST-002 | 中英文、短长、同义、单复数的逐项召回 | ATR-RUN-005 | PASS | Passed | 冻结 40 条逐项命中；不按类别平均抵销失败。P04 的 Agent 初次请求超时不影响 Retriever 独立直接召回结果。 |
| CC-TEST-003 | Agent 最终选模及 4 技术歧义 / 4 业务歧义处理 | ATR-RUN-005 | PASS | Passed | Agent 40 个唯一明确意图最终均正确 describe 目标；初跑 39/40，P04 初次 Provider 超时且未进入 Discovery，保留原失败；独立重跑 P04 后 40/40。技术歧义 4/4 只读消解，业务歧义 4/4 在业务 search 前澄清。 |
| CC-TEST-004 | 6 条负向表达的无误报和准确说明 | ATR-RUN-005 | PASS | Passed | 6/6 未编造模型、未启动业务 search，Agent 准确说明或请求澄清。 |
| CC-TEST-005 | 元数据发现不受业务 ACL 过滤；业务 search 仍受 ORM 权限控制 | ATR-RUN-002 | PASS | Passed | `test_registry_discovery_and_description_ignore_business_acl`；本次测试方法用当前用户 ORM，未用 sudo / SQL。 |
| CC-TEST-006 | 工具绑定、Provider 请求 Schema、Tool Call 与 Odoo Execute 对应、legacy 兼容 | ATR-RUN-005 | PASS | Passed | 66 个基线及 1 个 P04 重跑 Thread 初始仅绑定 `odoo_record_retriever`、`office`；所有正常 Agent Provider 请求均传这两个现有 Tool Schema。基线 171/171、P04 重跑 3/3 Tool Call 与 Odoo 执行按 Thread、ID、名称、参数匹配。内部 GPT 重排请求无 tools。legacy/响应兼容见 RUN-002、006。 |
| CC-TEST-007 | Alias 消融比较（条件项） | — | SKIPPED | Skipped | 本实现未采用 Alias，故条件项不适用；现有 Spike 的语义候选方案 Top-3 为 12/12、别名原型为 10/12 且出现遗漏/误候选，未增加别名配置维护路径。该 Spike 不是本轮 CC 产品验收。 |
| CC-TEST-008 | 完整 Registry 规模、discover / Agent p50/p95、Provider 调用数与超时 | ATR-RUN-005 | PASS（采集义务） | Passed | Registry 757；直接 discover p50/p95 6.155/8.826s；embedding 3.963/5.496s；GPT 重排 1.813/3.526s。Agent 基线 66 Thread p50/p95 17.372/26.869s，含一条已记录超时；基线 254 请求/253 响应/1 超时，P04 重跑 4/4 响应。CC 不设硬性 p95 门槛。 |
| CC-TEST-009 | Retriever/Registry 及通用指令受影响定向回归 | ATR-RUN-006 | PASS | Passed | `office_engine_m3` 全模块测试统计 63 项，实际 55 项，0 failed、0 error；不代表 M2 全量回归。 |

## 5. Test Run History（仅追加）

### ATR-RUN-001

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19（Asia/Shanghai） |
| Code Baseline | HEAD `8f7ebd259cda414baae46fa91b1d55948ba481a0` + manifest 所列工作树文件哈希 |
| Environment | `odoo18e_llm`，本地 Odoo 18；未创建数据库 |
| Invocation | `venv/bin/python odoo-bin -c odoo.conf -d odoo18e_llm --test-enable --test-tags /office_engine_m3:TestRetriever,/office_engine_m3:TestSilentRetrieval --stop-after-init --http-port=0 --gevent-port=0 -u office_engine_m3 --log-level=info --log-handler=odoo.tests:INFO --logfile=/private/tmp/cc-m4-01-targeted-tests.log` |
| Scope | Retriever 与受影响 Agent discovery 指令定向 TransactionCase |
| Executed | 23 个测试方法（12 TestRetriever + 11 TestSilentRetrieval）；Odoo stats 行显示 27 tests / 4.24s / 3659 queries |
| Result | 0 failed，0 error(s) of 23 tests |
| Evidence | `evidence/CC-M4-01/ATR-RUN-001_odoo_tests.log`、`ATR-RUN-001_summary.txt` |
| Follow-up | 真实 Provider 与盲测证据仍 Blocked；参见 OI-001、OI-002。 |

Odoo 日志中出现了被测错误分支预期产生的 `ACCESS_DENIED`、`QUERY_FAILED` 记录；另出现现有 Registry 加载错误 `Model column.filter.field.info has no table.`。该启动日志未导致本 Run 测试失败。所有 TransactionCase fixtures 在测试事务中执行并回滚。

### ATR-RUN-002

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19（Asia/Shanghai） |
| Code Baseline | HEAD `8f7ebd259cda414baae46fa91b1d55948ba481a0` +当前源文件哈希（见 manifest 的 ATR-RUN-002 部分） |
| Environment | `odoo18e_llm`，本地 Odoo 18；未创建数据库 |
| Invocation | 同 ATR-RUN-001；再次执行用于绑定修订后的测试文件哈希 |
| Scope | 与 ATR-RUN-001 相同的 Retriever / Agent 指令定向 TransactionCase |
| Executed | 23 个测试方法（12 TestRetriever + 11 TestSilentRetrieval）；Odoo stats 行显示 27 tests / 4.14s / 3659 queries |
| Result | 0 failed，0 error(s) of 23 tests |
| Evidence | `evidence/CC-M4-01/ATR-RUN-002_odoo_tests.log`、`ATR-RUN-002_summary.txt` |
| Follow-up | 本 Run 与当前测试文件哈希匹配；真实 Provider 与盲测仍 Blocked。 |

ATR-RUN-001/002 保留为历史 Odoo 自动化 Run。真实 Provider / Agent 验收见 ATR-RUN-003。

### ATR-RUN-003 — 真实 Provider 与 Agent 盲测（追加）

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19（Asia/Shanghai） |
| Code Baseline | ATR-RUN-002 产品源码基线；本次另加离线证据解析和测试清理修正，不改产品检索/路由代码 |
| Environment | 现有开发数据库 `odoo18e_llm`；Registry 757 模型；Provider OpenAI GPT-5.6 Luna；chat `gpt-5.6-luna`；embedding `text-embedding-3-large` |
| Scope | 完整 40 条 Retriever Top-5；66 个真实 Agent Thread（40 明确 + 4 技术歧义 + 4 业务歧义 + 6 负向 + 12 重复）；工具 Schema / Provider Tool Call / Odoo Execute 对账；同查询分页双遍历 |
| Provider evidence | 187 SDK request / 187 response；40 个直接盲测 embedding 请求；66 Thread；68 Agent embedding calls；无 Provider 错误或 timeout |
| Result | CC-TEST-001 FAIL（Top-5 18/40；分页集合 67 vs 66）；CC-TEST-002 FAIL；CC-TEST-003 PASS；CC-TEST-004 PASS；CC-TEST-006 PASS；CC-TEST-008 指标采集 PASS。Agent 40/40 最终选模正确、4/4 技术消歧、4/4 业务澄清、6/6 负向处理。 |
| Evidence | `provider_discovery_top5_v0.1.jsonl`、`provider_agent_threads_v0.1.jsonl`、`provider_agent_calls_v0.1.jsonl`、`provider_agent_evaluation_v0.1.json`、`provider_agent_tool_call_correlation_v0.1.json`、`provider_discovery_pagination_v0.1.json`、`ATR-RUN-003_summary.txt` |
| Fixture cleanup | `thread.generate()` 期间提交导致测试 Thread 持久化；其后仅用 ORM 清理 67 个 Thread 与 509 条消息，保留 188 条 Provider 使用审计记录，并核验无 attachment / Office 产物。见 `provider_agent_thread_cleanup_v0.1.json`。 |
| Follow-up | Retriever Top-5 和分页稳定性 FAIL；不得按 Provider 工具调用/Agent 选择通过而宣称整个 CC PASS。 |

### ATR-RUN-004 — 获授权的隔离 GPT 候选重排实验

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19（Asia/Shanghai） |
| Environment | 现有开发数据库 `odoo18e_llm`；Provider OpenAI GPT-5.6 Luna / `gpt-5.6-luna` |
| Authorization | 项目负责人在本会话中明确“授权仅限隔离测试”；授权内容限于将合成查询和现有 Retriever 返回的候选模型名、描述、`_rec_name` 发给 GPT 聊天接口重排。 |
| Scope | 原 40 条合成盲测查询；每条调用真实 Retriever `discover` 取最多 50 个候选，再使用无工具的单轮 GPT chat 对候选编号排序；不读取 Oracle、不执行业务记录 search、不调用 Office Tool。 |
| Provider evidence | 39 SDK request / 39 response、0 SDK 错误；SDK 审计与 Runner 请求内容、候选池和响应逐条核对；未见凭据字段。Chat 往返 p50 1.656 秒 / p95 3.830 秒（不含 embedding）。 |
| Result | 40 个案例：Retriever 前 50 候选覆盖目标 34/40（85%）；同轮 Retriever 原始前 5 命中 18/40；GPT 首选命中 30/40（75%，限目标已进入候选池为 30/34）；GPT 返回列表含目标 34/40，但完整 5 项输出只有 12/40（30%）。状态为 38 success、V03 空候选、PR03 无效空列表。该实验可作为候选方向证据，未达到 CC 冻结 40/40 Top-5 门槛，也不是 Agent E2E。 |
| Cleanup | ORM 按 Thread 1050 复核其记录不存在、关联消息 0、Provider usage 关联 0、审计 allowlist 参数不存在；未产生 Office 产物。 |
| Evidence | `provider_chat_metadata_rerank_authorization_and_result.md`、`provider_chat_rerank_blind_v0.1.jsonl`、`provider_chat_rerank_sdk_audit_v0.1.jsonl`、`provider_chat_rerank_evaluation_v0.1.json`、`provider_chat_rerank_cleanup_v0.1.json` |
| Follow-up | 不更改 CC-TEST-001/002 或已记录的产品失败；如后续采用候选重排，应另行设计产品集成与固定 Top-5 合同并达到冻结标准。 |

### ATR-RUN-005 — 最终完整 Registry / Agent 验收与分页双遍历

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19（Asia/Shanghai） |
| Environment | 当前工作区，现有开发库 `odoo18e_llm`；OpenAI GPT-5.6 Luna / `gpt-5.6-luna` |
| Scope | 修复版完整 Registry 40 条直接 Top-5 盲测；66 个 Agent Thread（40 明确意图、4 技术歧义、4 业务歧义、6 负向、12 重复）；P04 单例重跑；同一 Thread 完整 Registry 两遍分页；SDK 实际请求、响应、工具 Schema 与 Odoo 工具执行对账。测试守卫禁止业务记录 search 和 Office 写操作。 |
| Provider audit | 直接盲测 40 个 GPT 重排请求/40 响应/0 错误；Agent 基线 254 请求/253 响应/1 超时，其中内部重排 69/69 均有真实 Provider 响应；P04 重跑 4 请求/4 响应/0 错误，其中 1 次内部重排成功。审计校验每个内部重排 SDK 请求的 `payload.messages` 恰为 `[system,user]`，无 `tools`；user JSON 恰含 `business_request,candidates`，候选 757 条且字段完整唯一。Thread ID 只存在 SDK audit event 顶层供本地关联，不在 Provider payload 中。 |
| Retriever result | 全 Registry 757；明确意图 Top-5 40/40。探索结果不硬编码目标/模型；目标字段只被离线 Oracle 读取。 |
| Pagination | Thread `1291`；page size 100；两遍各 8 页（7×100 + 57），count 每页恒 757，每遍 total/unique 均为 757；两个完整 page 列表逐项相同，无遗漏/重复。真实 GPT 重排请求仅 1 次。缺失快照的后续分页失败关闭有 Odoo 单测覆盖。 |
| Agent result | 初始 66 个 Thread 中明确意图 39/40 完成；P04 首请求 `APITimeoutError`，没有 embedding/discover，describe 为 NOT REACHED。保存原始失败后以相同用户话术、Provider、工具配置在独立 Thread 重跑 P04 并通过；40 个唯一明确目标最后均由 Agent describe 选中。技术歧义 4/4、业务歧义 4/4、负向 6/6 通过；6 组重复样本各 3 个独立 Thread 均通过。 |
| Tool correlation | Provider 返回 171 个基线 Tool Call，与 Thread assistant tool_call message 及 Odoo tool result 171/171 对应；P04 重跑 3/3 对应。工具名与 JSON 参数相同。基线 185 个正常 Agent 请求、重跑 3 个正常请求的 Tool Schema 只含 `odoo_record_retriever`、`office`。 |
| Performance | 直接完整 discover p50/p95 6.155/8.826s；embedding 3.963/5.496s；GPT chat rerank 1.813/3.526s。Agent 基线 66 Thread wall-time p50/p95 17.372/26.869s（含 P04 超时样本；最大 34.86s）；P04 重跑 17.488s。无冻结的硬性 p95 门槛。 |
| Cleanup | 通过 Odoo ORM 在 `odoo18e_llm` 复核 68 个合成 Thread 已不存在，关联消息与快照均为 0；保留 Provider 使用审计行。没有查询或修改业务记录，没有直接 SQL。 |
| Result | PASS（所有适用冻结验收）；P04 第一次 Provider 超时作为原始执行结果保留，重跑仅补齐案例覆盖，不改写初次结果。CC-TEST-007 因未采用 Alias 仍 SKIPPED / N/A。 |
| Evidence | `provider_discovery_rerank_final40_snapshot_v0.2.jsonl`、`provider_discovery_rerank_final40_snapshot_v0.2_evaluation.json`、`provider_discovery_pagination_snapshot_final2.json`、`provider_agent_final_acceptance_v0.2.json`、`provider_agent_calls_final_snapshot_v0.2.jsonl`、`provider_agent_calls_retry_P04_v0.2.jsonl`、`provider_request_audit_review_v0.2.json`、`provider_agent_tool_call_correlation_final_v0.2.json`、`provider_agent_cleanup_orm_recheck_v0.2.json`。 |

### ATR-RUN-006 — Python 注释语法检查与 office_engine_m3 全模块回归

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19（Asia/Shanghai） |
| Command | `venv/bin/python odoo-bin -c odoo.conf -d odoo18e_llm --test-enable --stop-after-init --test-tags /office_engine_m3 -u office_engine_m3 --log-level=test --logfile=/private/tmp/cc-m4-01-final-module-tests.log` |
| Result | `office_engine_m3: 63 tests 7.82s 7471 queries`；`0 failed, 0 error(s) of 55 tests`。异常 Traceback / ERROR 日志来自负向用例注入的预期异常，不是测试失败。 |
| Python comment audit | 对仓库中排除 `venv` / `.git` 的全部 189 个 Python 文件完成 AST parse 与 py_compile；模块级说明/manifest 注释 189/189、类 120/120、公开函数/方法 929/929、`office_engine` 复杂私有函数 418/418，必需注释缺失 0。简单私有函数不强制逐行注释；新补注释为中文。 |
| Evidence | `ATR-RUN-006_m3_module_tests.log`、`python_comment_audit_v0.1.json`。 |

注释审计的上述数字只证明 Docstring 覆盖和 Python 语法检查，不代表所有新增说明均通过人工语义质量评审。后续复核在工作区发现 1,087 处模板式通用 Docstring；CC-M4-01 变更代码中的说明已逐项修正，而其他模块的批量注释质量清理不属于本 CC 提交范围，仍待单独完成。不得将此审计数字表述为仓库注释质量全部 PASS。

### ATR-RUN-007 — 审计隔离调整后的 office_engine_m3 全模块回归

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19（Asia/Shanghai） |
| Command | `venv/bin/python odoo-bin -c odoo.conf -d odoo18e_llm --test-enable --stop-after-init --test-tags /office_engine_m3 -u office_engine_m3 --log-level=test --logfile=/private/tmp/cc-m4-01-close-module-tests.log` |
| Purpose | 在 Provider 请求审计门禁与 CC-M4-01 Discovery 实现解除对 M4 TV fault-hook 模块的导入依赖后，复跑现有开发库的完整 M3 模块测试。 |
| Result | `office_engine_m3: 63 tests 7.28s 7471 queries`；`0 failed, 0 error(s) of 55 tests`。仅使用现有数据库 `odoo18e_llm`。 |
| Evidence | `ATR-RUN-007_m3_module_tests_post_audit_isolation.log`。 |

## 6. Regression Verification

| CC-PRESERVE | 回归项 | Run | Result | 证据 |
|---|---|---|---|---|
| CC-PRESERVE-001 | 唯一工具、discover / describe / search 分发及无 Thread 直接调用的 legacy discovery | ATR-RUN-002 | PASS（定向） | `test_registry_discovery_and_description_ignore_business_acl`、`test_semantic_discovery_uses_current_thread_provider_only_for_thread_calls` |
| CC-PRESERVE-002 | Tool Schema / discover 公共结果字段不增加评分字段 | ATR-RUN-002 | PASS（定向） | `test_tool_schema_exposes_array_valued_domain`、`test_discover_preserves_public_metadata_shape_and_stable_pagination` |
| CC-PRESERVE-003 | 同分稳定排序、排序后分页 | ATR-RUN-002 / 003 | FAIL（真实 Provider 边界） | mock/ORM 排序测试通过；真实 Provider 同查询分页候选计数/集合/顺序不稳定，见 `provider_discovery_pagination_v0.1.json` |
| CC-PRESERVE-004 | Registry metadata 不按业务 ACL 隐藏 | ATR-RUN-002 | PASS | `test_registry_discovery_and_description_ignore_business_acl` |
| CC-PRESERVE-005 | 业务记录 search 保持当前用户 ORM 权限 | ATR-RUN-002 | PASS | 同上；无 sudo/SQL |
| CC-PRESERVE-006 | legacy search、describe 和 Office 通用发现指引回归 | ATR-RUN-002 | PASS（定向） | `test_legacy_search_shape_and_explicit_pagination_with_in_domain`、`test_complete_export_route_requires_registry_discovery_before_search` |

范围限制：未运行完整 `office_engine_m3` 测试套件、M2 全量回归或真实 UI；不得据此声称这些范围通过。

## 7. Issues

| ID | TEST | 类型 | 原因 | 状态 | 后续 |
|---|---|---|---|---|---|
| OI-001 | CC-TEST-001/002/003/004/006/008 | RESOLVED | 用户已明确授权将 757 个模型名称、描述和 `_rec_name` 发送至 OpenAI embedding，真实验收已完成。首次截断调用的接收状态仍 UNKNOWN，不计入验收。 | Closed | 保留首次截断事实及后续有效结果。 |
| OI-002 | CC-TEST-001/002、CC-PRESERVE-003 | 历史 FAIL；ATR-RUN-005 已复测通过 | 初始 Retriever Top-5 为 18/40，分页集合与顺序不稳定。最终全量 Top-5 40/40；分页双遍历逐页一致。 | Closed — final retest PASS | 关闭历史失败状态但不删除首次证据；不调整冻结阈值。 |
| OI-003 | 候选 GPT 聊天重排实验 | Completed（非产品 PASS/FAIL） | 一次请求在单独授权前被自动审批拒绝；之后项目负责人明确授权并完成隔离实验。 | Closed for experiment | 见 ATR-RUN-004；实验结果不改变产品验收门槛，未实现或部署聊天重排。 |

## 8. Special Verification

| 类别 | 结果 |
|---|---|
| Security / 权限 | 定向 ORM 测试通过；无 sudo、SQL、替代用户或业务记录读取。 |
| Performance | 最终记录见 ATR-RUN-005：Registry 757；直接 discover p50/p95 6.155/8.826s，Agent 66 Thread p50/p95 17.372/26.869s，包含一次被保留的 Provider 超时；CC 不设置硬性 p95 门槛。 |
| Real Provider integration | 最终覆盖 40 条直接 Top-5、66 个真实 Agent Thread、P04 独立重试、分页双遍历。基线 171/171、重试 3/3 Tool Call→Odoo Execute 精确匹配。初次 P04 Provider timeout 保留；细节见 ATR-RUN-005。 |
| Mock transparency | 新增排序与全 Registry 分页行为使用 Fake embedding vectors；仅证明确定性逻辑，不证明真实 OpenAI 排序质量。 |
| HVR | N/A — CC §11.2 声明本 CC 不执行 UI HVR。 |

## 9. Evidence Inventory

| Evidence | 位置 | 用途 |
|---|---|---|
| E-001 | `evidence/CC-M4-01/ATR-RUN-001_odoo_tests.log`、`ATR-RUN-002_odoo_tests.log` | 两次 Odoo test-runner 日志 |
| E-002 | `evidence/CC-M4-01/registry_snapshot.txt` | 757 模型数及盲测模型元数据快照（只读 ORM） |
| E-003 | `evidence/CC-M4-01/blind_queries_v0.1.json` | 40 条明确意图合成输入，已用于 Top-5 与 Agent 验收 |
| E-004 | `evidence/CC-M4-01/supplemental_queries_v0.1.json` | 4 技术歧义、4 业务歧义、6 负向输入，已用于 Agent 验收 |
| E-005 | `evidence/CC-M4-01/oracle_v0.1.json` | 独立测试 Oracle，不得发给 Agent / Provider |
| E-006 | `evidence/CC-M4-01/manifest.txt` | 输入、Oracle、各 Run 日志、代码 SHA-256 和隔离说明 |
| E-007 | `evidence/CC-M4-01/provider_request_block.md` | 首次输出截断、用户授权后的实际执行及不同接口审批边界 |
| E-008 | `evidence/CC-M4-01/ATR-RUN-003_summary.txt` | Provider / Agent 分项验收摘要与冻结门槛结果 |
| E-009 | `evidence/CC-M4-01/provider_agent_tool_call_correlation_v0.1.json` | 逐条 Thread/tool_call_id/工具名/JSON 参数匹配 |
| E-010 | `evidence/CC-M4-01/provider_discovery_pagination_v0.1.json` | 同查询两次完整分页遍历差异 |
| E-011 | `evidence/CC-M4-01/provider_agent_thread_cleanup_v0.1.json` | 测试 Thread/消息清理与 Provider usage 保留证明 |
| E-012 | `evidence/CC-M4-01/provider_chat_metadata_rerank_block.md` | 自动审批拒绝边界及未执行证明 |
| E-013 | `evidence/CC-M4-01/provider_chat_metadata_rerank_authorization_and_result.md` | 后续单独授权、隔离实验范围及结果摘要 |
| E-014 | `evidence/CC-M4-01/provider_chat_rerank_blind_v0.1.jsonl`、`provider_chat_rerank_sdk_audit_v0.1.jsonl` | 逐项 Retriever 候选、GPT 输出及 SDK 原始请求/响应 |
| E-015 | `evidence/CC-M4-01/evaluate_provider_chat_rerank_blind_v0.1.py`、`provider_chat_rerank_evaluation_v0.1.json` | Oracle 独立离线评估器与逐项结果；Oracle 未发送给 Provider |
| E-016 | `evidence/CC-M4-01/provider_chat_rerank_cleanup_v0.1.json` | ORM 清理复核 |
| E-017 | `evidence/CC-M4-01/provider_discovery_rerank_final40_snapshot_v0.2.jsonl`、`provider_discovery_rerank_final40_snapshot_v0.2_evaluation.json` | 最终 40 条 Retriever Top-5 真实 Provider 原始结果及独立 Oracle 离线评分 |
| E-018 | `evidence/CC-M4-01/provider_discovery_pagination_snapshot_final2.json`、`provider_discovery_pagination_sdk_audit_snapshot_final2.jsonl` | 同一 Thread 上 757 条全量结果分页双遍历及实际 SDK 请求/响应 |
| E-019 | `evidence/CC-M4-01/provider_agent_final_acceptance_v0.2.json`、`provider_agent_threads_final_snapshot_v0.2_evaluation.json`、`provider_agent_threads_retry_P04_v0.2_evaluation.json` | Agent 选模、describe、歧义、负向、重复集与 P04 初次超时/单例重跑结果 |
| E-020 | `evidence/CC-M4-01/provider_request_audit_review_v0.2.json` | 实际发往 Provider 的 Chat Completions `messages`、候选元数据数量、工具 Schema 与请求/响应对账；证明重排请求不含 Thread 历史 |
| E-021 | `evidence/CC-M4-01/provider_agent_tool_call_correlation_final_v0.2.json` | Provider Tool Call 与 Odoo assistant/tool 消息 171/171 及 3/3 对账 |
| E-022 | `evidence/CC-M4-01/provider_agent_cleanup_orm_recheck_v0.2.json` | 通过当前开发数据库 ORM 对 68 个合成测试 Thread/消息/快照的清理复核 |
| E-023 | `evidence/CC-M4-01/python_comment_audit_v0.1.json`、`ATR-RUN-006_m3_module_tests.log` | Python Docstring 覆盖计数与语法检查；质量限制见 ATR-RUN-006 注释 |
| E-024 | `evidence/CC-M4-01/ATR-RUN-007_m3_module_tests_post_audit_isolation.log` | 审计隔离调整后复跑的 office_engine_m3 全模块自动化回归 |

## 10. Handoff to FR

```
CC 自动化义务：9
PASS：8  FAIL：0  SKIPPED：1（CC-TEST-007：未采用 Alias） BLOCKED：0
最终 Provider / Agent / 全量分页验收：ATR-RUN-005
最后 M3 全模块定向回归：ATR-RUN-007；Docstring 覆盖/语法计数：ATR-RUN-006（不代表语义质量全面通过）
40/40 Retriever Top-5；分页两遍各 757/757 且顺序完全一致。
Agent 40 个唯一明确任务最终均 describe 选对；技术歧义 4/4、业务歧义 4/4、负向 6/6、6 组×3 Thread 重复均通过。
P04 首轮真实 Provider 超时保留，单例重跑补齐覆盖；未覆盖范围未被改判。
真实 Provider 重排 SDK payload 已核验不含 Thread 历史，Provider Tool Call 与 Odoo 执行 171/171 + 3/3 对应。
CC 证据达到关闭评审条件；最终关闭需负责人批准。
```

本 ATR 提交负责人进行关闭评审；在明确批准前不将 CC 标记为正式 CLOSED。
