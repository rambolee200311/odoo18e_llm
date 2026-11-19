<!--
模板来源：office_engine/docs/skill/odoo-project-workflow/references/templates/Coding/IHR模板.md
模板版本/状态：v1.0.0 Frozen；同步检查 PASS（2026-11-19）
本文件状态：实施记录完成；项目负责人已于 2026-11-19 批准关闭 CC-M4-01。
-->

# IHR — CC-M4-01 通用业务对象发现

## 0. 文档治理

本记录只记载 CC-M4-01 v0.2 的实施事实。历史条目仅追加；当前状态与变更清单可更新。IHR 不判定 CC 是否关闭。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| IHR 文档 | `IHR-CC-M4-01.md` |
| Intent ID | `CC-M4-01` |
| CC | `CC-M4-01_通用业务对象发现_v0.2.md`；FROZEN |
| TDD 基线 | `TDD_office_engine_m4_v0.2.md`；FROZEN WITH OPEN ITEMS |
| 计划基线 | `IMPLEMENTATION_PLAN_office_engine_m4_v0.1.md`；FROZEN |
| 模块 | `office_engine_m3` |
| 工作类型 | 通用 Registry Discovery 增强 |
| 执行日期 | 2026-11-19（Asia/Shanghai） |
| Branch / HEAD | `codex/cc-m4-01-registry-discovery` / `8f7ebd259cda414baae46fa91b1d55948ba481a0`（CC 关闭提交前基线） |
| 当前实施状态 | 实施与冻结验收已完成；项目负责人于 2026-11-19 批准关闭 |

工作区在本 CC 开始前已有其他未提交代码和文档；本轮没有清理、覆盖或纳入它们。`llm_thread.py` 中既有的 M4 TV Provider audit hook 保持原样，本轮只调整 Discovery system instruction 文本。

## 2. Coding Contract 基线

范围、变更边界、保护项、Guardrails、测试与完成条件均引用冻结 CC §3–13；本记录不重述其规范性内容。

## 3. 当前实施状态摘要

| 项 | 状态 |
|---|---|
| CC-CHANGE 落实 | 全 Registry 高召回、GPT 元数据重排、Agent describe 选模及可复核的 Thread 内分页顺序已实现；最终真实 Provider 与 Agent 验收满足冻结门槛 |
| Preservation Impact | 公开 Retriever 响应结构、工具 Schema、legacy search 与 ORM 权限保持；office_engine_m3 全模块定向自动化测试通过 |
| Deviation | 按本轮明确指令，对 `office_engine/**/*.py` 进行纯注释/Docstring 补齐；未改变其运行逻辑 |
| CC Stop Condition | Registry 元数据发送到 embedding 经授权后执行；候选元数据聊天重排在单独授权后仅作为隔离实验执行，未接入产品 |
| Open Issues | 无冻结验收阻断项；最初 P04 超时已保留并单例复测通过；旧版候选重排实验仍仅作历史证据 |
| Revert | No |
| 当前状态 | **Closed — 项目负责人于 2026-11-19 批准关闭** |

## 4. 实施历史条目（仅追加）

### IHR-001 — 语义候选发现实现

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19 |
| 阶段 | Implementation |
| Action | 在现有 `discover` 私有路径中增加 Thread Provider embedding 排序；对完整 Registry 模型名、描述和 `_rec_name` 生成候选向量，以余弦相似度降序排序，同分按技术模型名稳定打破，之后再分页；没有增加公开分数或响应字段。直接无 Thread 上下文的旧式 discover 保持原字面行为。 |
| Reason | 落实 CC-CHANGE-001、CC-PRESERVE-002/003。 |
| Files / Components | `office_engine/office_engine_m3/models/llm_tool.py` |
| Upstream Reference | TDD v0.2 §§5.1、14；CC §5、§6 |
| Result | Partial — 代码和 mock/ORM 覆盖已完成；阈值 0.30 尚未用完整 Registry Provider 盲测校准。 |
| Deviation | None |
| Follow-up | OI-001、OI-002 |

### IHR-002 — Agent 指引与隔离回归测试

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19 |
| 阶段 | Implementation |
| Action | 将通用 Agent 指引改为使用自然业务表达、检查多个候选、必要时只读 describe，并仅在剩余业务歧义会改变结果时于 search 前澄清；新增 Retriever 排序、同分稳定、低分过滤、分页、响应契约和 Provider 错误测试，并更新指引回归断言。 |
| Reason | 落实 CC-CHANGE-002、CC-CHANGE-003 及 CC-PRESERVE-001/006。 |
| Files / Components | `models/llm_thread.py`、`tests/test_retriever.py`、`tests/test_silent_retrieval.py` |
| Upstream Reference | TDD v0.2 §§5.1、12；CC §5、§6 |
| Result | Completed for code and deterministic tests; real Agent selection remains unverified. |
| Deviation | None |
| Follow-up | OI-001 |

### IHR-003 — 首次真实 embedding 校准（结果不可读）

| 字段 | 值 |
|---|---|
| 时间 | UNKNOWN（前序运行记录只保留在会话摘要中） |
| 阶段 | Implementation |
| Action | 启动真实 OpenAI embedding 校准，输入包括 12 条合成表达和运行时完整 Registry profile。工具只返回输出超长截断提示，排名/响应不可读。 |
| Reason | 早期语义排序方向校准。 |
| Files / Components | Provider 请求及工具输出；没有可保存的完整响应 artifact |
| Contract Reference | CC-TEST-001/002/008 |
| Result | Partial / Evidence unusable — Provider 请求方法已调用，完整 Registry 元数据可能已外发；不能确认 Provider 侧处理状态，不能判召回或性能结果。 |
| Deviation | None |
| Follow-up | 原始截断返回与后续自动审批拒绝另存于 `evidence/CC-M4-01/provider_request_block.md`；不重试。 |

### IHR-004 — 自动审批拒绝及停止重试

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19 |
| 阶段 | Implementation |
| Action | 后续重复校准命令在进程创建前被自动审批拒绝；未执行 Provider 调用。按拒绝内容停止该传输路径，未通过其他工具重试。 |
| Reason | 自动审批认为完整模型名、描述和 `_rec_name` 外发所涉及的具体 payload 尚未明确授权。 |
| Files / Components | `evidence/CC-M4-01/provider_request_block.md` |
| Contract Reference | CC-TEST-001/002/003/004/006/008；CC §8、§12 |
| Result | Blocked — 后续 Provider 验收无法进行。 |
| Deviation | None |
| Follow-up | 需负责人对该具体元数据外发作出明确决定；见 OI-001。 |

### IHR-005 — Registry Oracle 与自动化 Run

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19 |
| 阶段 | Implementation |
| Action | 以只读 ORM 核对 Registry 共 757 个模型及 10 个盲测目标模型，并读取关系字段声明；准备独立 blind inputs / evaluator Oracle；在 `odoo18e_llm` 执行 Retriever 与 Silent Retrieval 定向 TransactionCase。 |
| Reason | 建立独立测试 Oracle、验证 Registry 目标存在并覆盖确定性兼容边界。 |
| Files / Components | `evidence/CC-M4-01/`、`ATR-CC-M4-01.md` |
| Contract Reference | CC-TEST-001/005/009 |
| Result | Completed for local metadata and targeted automated tests; blind Provider tests not run. |
| Deviation | None |
| Follow-up | 见 ATR-RUN-002 与 OI-001/002。 |

### IHR-006 — 获授权的 Provider 盲测与 Agent 集成验收

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19 |
| 阶段 | Provider Acceptance |
| Action | 项目负责人明确授权将现有开发库 757 个 Registry 模型名称、描述及 `_rec_name` 发送至 OpenAI embedding。随后执行完整 40 条明确意图 Top-5 盲测、66 个真实 GPT-5.6 Luna Thread（含冻结的 6×3 重复集）、4 条技术歧义、4 条业务歧义、6 条负向表达，并记录真实 SDK 请求、Provider 响应和 Odoo 工具执行。受测 Thread 初始仅绑定 `odoo_record_retriever` 与 `office`；系统生成后的持久 Thread 工具列表还包含 4 个 Office action tool，但实际提交给 Provider 的请求 Schema 始终为冻结工具对。Agent 只可执行 discover / describe；search 与 Office 执行路径均有隔离保护。 |
| Reason | 关闭 CC-TEST-001～006、008 的真实 Provider 与 Agent 集成验收。 |
| Files / Components | `evidence/CC-M4-01/provider_discovery_top5_v0.1.jsonl`、`provider_agent_threads_v0.1.jsonl`、`provider_agent_calls_v0.1.jsonl`、`provider_agent_evaluation_v0.1.json`、`provider_agent_tool_call_correlation_v0.1.json` |
| Contract Reference | CC §8、§10、§11 |
| Result | Partial / Gates failed：Retriever Top-5 为 18/40（22 FAIL）；重复候选召回不稳定；40/40 明确意图的 Agent 最终模型选择/描述正确；4/4 技术歧义通过只读发现和描述；4/4 业务歧义在 search 前澄清；6/6 负向表达未强行匹配。Provider 187 请求/187 响应，187 请求提交相同工具对 Schema（canonical SHA-256 唯一）；185 个 Tool Call 与 185 个 Odoo 执行按 Thread、tool_call_id、工具名、JSON 参数逐项完全匹配。 |
| Deviation | None；未发送业务记录、隐藏 Oracle 标签或凭据。 |
| Follow-up | OI-002；详细分项见 ATR-RUN-003。 |

### IHR-007 — 候选排序探索与分页不稳定复测

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19 |
| 阶段 | Provider Experiment / Failure Analysis |
| Action | 在不改产品代码的独立测试脚本中比较本地化 profile（24/40）、中英多视角描述（23/40）、标识符归一化多视角（21/40）、单条 query rewrite（24/40）及三条等义检索表达（30/40）。另用相同查询、相同数据库和 20 条分页执行两次完整候选遍历。 |
| Reason | 了解已观察 Top-5 缺口是否由单一表达形式造成，并验证 CC-PRESERVE-003 的真实 Provider 分页边界。 |
| Files / Components | `evidence/CC-M4-01/provider_*_blind_v0.1.jsonl`、`provider_discovery_pagination_v0.1.json` |
| Contract Reference | CC-TEST-001/002/008、CC-PRESERVE-003 |
| Result | 所有 profile / phrase 方案均未达到冻结 40/40，且未并入产品代码。两次遍历候选数分别为 67 与 66；第二次各页 `count` 出现 66/67 不一致；合并唯一模型数 67 与 66，且分页顺序在第 41 项附近变化。确认本轮真实分页稳定性验收 FAIL；现有证据尚不能确认波动的底层 Provider 或运行时根因。 |
| Deviation | None。仅发送已授权 Registry 元数据至 embedding；query rewrite / variants 的聊天请求仅含合成 query，不含 Registry 元数据。 |
| Follow-up | OI-002；候选方法实验结果不是 CC-TEST-001 的 PASS。 |

### IHR-008 — GPT 聊天元数据重排请求被自动审批拒绝

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19 |
| 阶段 | Candidate Experiment Boundary |
| Action | 一项把真实 discover 候选模型名、描述和 `_rec_name` 发给 GPT-5.6 Luna 聊天接口进行重排的调用，在执行前被自动审批拒绝；没有 Provider 请求。 |
| Reason | 用户明确授权的元数据外发目标为 OpenAI embedding，不包含此次聊天接口及重排用途。 |
| Evidence | `evidence/CC-M4-01/provider_chat_metadata_rerank_block.md` |
| Result | Blocked before execution；未通过其他工具或间接路径重试。 |
| Follow-up | 该候选方向若需继续，须另行评审授权；不影响已完成的 embedding / Agent 验收结果。 |

### IHR-009 — 测试 Thread 持久化发现、清理与脚本更正

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19 |
| 阶段 | Test Fixture Cleanup |
| Action | 因 `llm.thread.generate()` 会提交事务，`odoo-bin shell` 退出时的回滚没有清除测试 fixture。只通过 Odoo ORM 核实并清理了 ID 902–968 的 67 个本 CC 合成 Thread 与 509 条消息；检查关联附件和三个 Office 版本/请求模型均为 0。保留 188 条 `office.llm.usage` 审计行（`thread_id` 按现有 `ondelete=set null` 解除关联），清除仅由本轮测试设置且值为 968 的审计参数，并保存 Thread/消息/Provider 使用行关联快照及原始 evidence SHA-256。Thread 的标准 `mail.thread.unlink()` 框架实现会用其内置权限处理删除关联 `mail.message`；本脚本未执行直接 SQL 或显式 `.sudo()` 调用。 |
| Reason | 履行 CC §8 测试后清理/回滚要求，同时保留 Provider 审计记录和离线原始证据。 |
| Evidence | `evidence/CC-M4-01/provider_agent_thread_cleanup_v0.1.json` |
| Result | Cleanup PASS：Thread 0、消息 0、用量行仍为 188、关联 Thread 为空、Office 业务产物 0；只操作 `odoo18e_llm`，无直接 SQL、无业务数据读取。 |
| Follow-up | 修订 `run_agent_blind_tests_v0.1.py`，在 future run 的 `finally` 中只清理该脚本创建的 Thread、恢复原审计参数并保留用量行，避免 shell 回滚假设再次造成持久化测试数据。 |

### IHR-010 — 获授权的 GPT 聊天候选重排隔离实验

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19 |
| 阶段 | Isolated Candidate Feasibility Experiment |
| Action | 负责人在本会话中另行授权“仅限隔离测试”。使用现有 Retriever 对 40 条合成盲测意图各取最多 50 个实际候选，将查询和这些候选的模型名、描述、`_rec_name` 发给 OpenAI GPT-5.6 Luna 聊天接口；候选编号仅用于关联排序结果。Runner 不读取 Oracle、不执行业务记录 search、不调用 Office Tool。 |
| Reason | 评估在已召回候选内增加通用 GPT 重排是否值得进一步研究；不改变冻结 CC 的 40/40 Top-5 门槛。 |
| Evidence | `evidence/CC-M4-01/provider_chat_metadata_rerank_authorization_and_result.md`、`provider_chat_rerank_blind_v0.1.jsonl`、`provider_chat_rerank_sdk_audit_v0.1.jsonl`、`provider_chat_rerank_evaluation_v0.1.json`、`provider_chat_rerank_cleanup_v0.1.json` |
| Result | 40/40 场景执行；Retriever 前 50 候选覆盖目标 34/40，当前 Retriever 同轮前 5 命中 18/40；39 个 GPT 请求/39 响应、无 Provider 错误；GPT 首选命中 30/40，返回候选列表含目标 34/40，但完整 5 项排序仅 12/40；另有 1 个空候选及 1 个无效响应。此为方向性隔离证据，不是 Agent E2E 或 CC PASS。 |
| Deviation | None。只发送合成意图与 Retriever 实际返回的候选元数据；未向 Provider 提供 Oracle 标签、业务记录或凭据。 |
| Cleanup | Odoo ORM 按 Thread 1050 复核其记录不存在、消息 0、Provider usage 关联 0、审计 allowlist 参数不存在；见 `provider_chat_rerank_cleanup_v0.1.json`。 |
| Follow-up | OI-002 仍为唯一阻断项。实验显示候选池漏召回及输出长度不稳定；不据此直接加入产品重排逻辑。 |

### IHR-011 — 全 Registry 重排、分页顺序持久化与最终验收

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19 |
| 阶段 | Implementation / Final Acceptance |
| Action | 移除固定相似度门槛，对当前完整 Registry 的全部 757 个模型元数据计算通用候选排序；将用户查询及全部 Registry 元数据交给 GPT-5.6 Luna 重排，再由 Agent 通过 `describe` 验证模型。针对分页，在首次 Thread 工具调用时把完整排序顺序及 query、Registry、Provider、model 摘要写入现有隐藏 `mail.message`；后续页、offset 0 重遍历均复用该顺序。缺少/失配快照时，后续页失败关闭并要求从 offset 0 重启。公开工具 Schema、响应字段及业务权限未变。 |
| Reason | 旧版 0.30 相似度阈值和 50 项候选上限导致目标模型漏召回；逐页重新执行 embedding / GPT 会令排序及 count 漂移，不能证明同一查询翻页一致。 |
| Files / Components | `office_engine/office_engine_m3/models/llm_tool.py`、`office_engine/office_engine_m3/tests/test_retriever.py`、`evidence/CC-M4-01/run_discovery_rerank_v0.2.py`、`run_discovery_pagination_v0.2.py` |
| Evidence | `provider_discovery_rerank_final40_snapshot_v0.2_evaluation.json`；`provider_discovery_pagination_snapshot_final2.json`；`provider_request_audit_review_v0.2.json`；`provider_agent_final_acceptance_v0.2.json`；`provider_agent_tool_call_correlation_final_v0.2.json` |
| Result | PASS（执行结果，待负责人关闭评审）：40/40 明确意图 Retriever Top-5；分页两次完整遍历各 757/757、无重复遗漏、顺序逐页完全一致；Agent 独立 Thread 初跑 39/40，唯一 P04 因 Provider 超时未进入 Discovery；保留该超时后对 P04 单独复测通过，40 个唯一明确用例最终均选模并 describe 正确；技术歧义 4/4、业务歧义 4/4、负向 6/6、6 组重复场景各 3 个 Thread 均通过。 |
| Provider Request Audit | 真实 OpenAI SDK 出站边界审计：40/40 直接重排请求、Agent 69/69 内部重排及 P04 复测 1/1 均只有 system + user 两条消息、无 Provider Tool Schema；user 内容仅含合成业务查询和 757 项 Registry 元数据。`thread_ids` 仅在审计事件顶层作本地关联，不进入请求 payload。Agent 普通请求携带的工具 Schema 始终只有 `odoo_record_retriever` 与 `office`。 |
| Pagination Proof | 同一 Thread `1291`、page size 100、8 页 × 两遍；每遍 757 项且 unique 757，count 恒 757，逐页内容完全相同；真实 GPT 重排只调用一次，第二遍复用已存顺序。 |
| Deviation | 无业务逻辑范围偏离。测试 Thread/隐藏快照按 ORM 复核均已清理；仅保留既有 Provider 用量审计记录和文件化 evidence。 |
| Follow-up | 供负责人进行 CC-M4-01 关闭评审。 |

### IHR-012 — Python 注释与 Docstring 覆盖

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19 |
| 阶段 | Documentation / Quality |
| Action | 按 `office_engine/AGENTS.md` 的注释规范，并依负责人“本项目所有代码 py”指令，对仓库中非 venv / .git 的 Python 文件补齐缺失模块说明、类 Docstring、公开函数/方法 Docstring 与复杂私有函数 Docstring；本轮新增说明使用中文。 |
| Scope | 共 189 个 Python 文件：`office_engine` 186 个、根目录 `setup.py` 1 个、项目文档检查脚本 2 个；包含 120 个类、929 个公开函数/方法及 418 个复杂私有函数。4 个 `__manifest__.py` 用中文注释说明清单用途。简单私有函数不添加逐行注释。 |
| Evidence | `evidence/CC-M4-01/python_comment_audit_v0.1.json`；仓库 Python 文件 AST/py_compile 检查通过。 |
| Result | PASS：189 个文件均有模块级说明或 manifest 注释；类/公开定义/复杂私有函数的必需 Docstring 缺失数为 0。未重写历史英文注释文本。 |
| Deviation | 该纯注释工作由负责人本轮明确要求；包括 Office Engine 以外的打包和文档检查 Python 脚本，不改变方法体、执行行为或业务契约。 |

### IHR-013 — 最终 M3 模块回归与测试数据清理复核

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19 |
| 阶段 | Regression / Cleanup Verification |
| Action | 对 `office_engine_m3` 执行完整 Odoo TransactionCase，之后使用 Odoo ORM 只读核验 66 个基线 Thread、P04 重试 Thread 和分页 Thread。 |
| Result | M3 模块 63 项统计，55 项执行，0 failed、0 error；测试日志中的 Retriever/AccessError 记录属于验证器预期的故障注入路径。68/68 个测试 Thread 均不存在，关联 `mail.message` 为 0，隐藏排序快照为 0。未运行 M2 全量回归。 |
| Evidence | `evidence/CC-M4-01/ATR-RUN-006_m3_module_tests.log`；`provider_agent_cleanup_orm_recheck_v0.2.json` |
| Deviation | 仅使用现有开发库 `odoo18e_llm` 和 Odoo ORM；未创建数据库、未执行 SQL、未访问生产环境。 |

### IHR-014 — Provider 审计隔离解耦及回归复跑

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19 |
| 阶段 | Regression / Audit Isolation |
| Action | 将 Provider 请求审计的 Thread allowlist 校验移入 M3 下游私有 helper，避免 `llm_provider` 依赖 M4 TV fault-hook 模块；在此隔离调整后复跑完整 `office_engine_m3` Odoo 测试。 |
| Database | 仅使用已有开发数据库 `odoo18e_llm`。 |
| Result | 63 项统计、55 项实际执行，0 failed、0 error；测试后没有执行新的 Provider 调用或业务记录修改。 |
| Evidence | `evidence/CC-M4-01/ATR-RUN-007_m3_module_tests_post_audit_isolation.log`。 |
| Deviation | None。 |

### IHR-015 — 仓库级注释审计的质量范围更正

| 字段 | 值 |
|---|---|
| 时间 | 2026-11-19 |
| 阶段 | Documentation Quality Review |
| Action | 对上一条 IHR-012 的机械 Docstring 覆盖结果做语义复核，发现仓库工作区中存在 1,087 处模板式通用 Docstring。CC-M4-01 变更代码内的相关说明已修正；其他模块的批量注释没有纳入本 CC 选择性提交。 |
| Result | IHR-012 的 AST / py_compile 与覆盖数字仍是原始执行事实，但不能作为注释语义质量全面 PASS 的依据。负责人提出的仓库级注释质量清理仍未完成；该事项不属于冻结 CC-M4-01 的关闭门槛。 |
| Evidence | 工作区检索模式：`所表达的场景；具体通过条件`、`对应的功能、状态或数据结构`、`所标识的输入、状态或结果`。 |
| Follow-up | 单独清理非 CC-M4-01 代码中的模板式说明，并以实际行为为依据逐条复核。 |

## 5. 实际变更清单（当前快照）

| 文件 | 动作 | 实际变更 | CC 来源 |
|---|---|---|---|
| `office_engine/office_engine_m3/models/llm_tool.py` | Modified | 全 Registry embedding 排序、GPT 重排、Thread 隔离请求、分页顺序快照及失败关闭；不改工具 Schema、响应字段或 search 权限 | CC-CHANGE-001、CC-PRESERVE-001～006 |
| `office_engine/office_engine_m3/models/llm_provider.py`、`services/provider_request_audit.py` | Modified / Added | 增加仅在显式开发测试开关、`odoo18e_llm` 数据库和 Thread allowlist 全部满足时生效的 OpenAI SDK 出站请求审计；不改请求内容或公共 Provider Schema | CC-TEST-006、CC-TEST-008 |
| `office_engine/office_engine_m3/models/llm_thread.py` | Modified | 只更新通用 discovery / describe / 歧义指引；保留文件既有的 M4 TV audit-hook 差异 | CC-CHANGE-002 |
| `office_engine/office_engine_m3/tests/test_retriever.py` | Modified | 增加语义排序、低相关过滤、分页、响应结构和 Provider 故障测试 | CC-TEST-001、005、009 |
| `office_engine/office_engine_m3/tests/test_silent_retrieval.py` | Modified | 更新通用 discovery 指令断言 | CC-TEST-003、006、009 |
| `office_engine/docs/implementation/evidence/CC-M4-01/` | Added | 盲测输入、分离 Oracle、真实 Provider/Agent 轨迹、Top-5 与分页失败结果、Tool Call 对账、测试 Thread 清理和自动审批边界证据 | CC-TEST-001～009 |
| `evidence/CC-M4-01/run_agent_blind_tests_v0.1.py` | Modified | 在 `finally` 中清理本脚本创建的 Thread、恢复 audit 参数并保留 usage 行；不再依赖 `thread.generate()` 后 shell 回滚 | CC §8 |
| `office_engine/docs/implementation/IHR-CC-M4-01.md` | Added | 实施与变更记录 | CC §13 |
| `office_engine/docs/implementation/ATR-CC-M4-01.md` | Added | 自动化及 Provider 验收证据；真实 Provider 部分仍开放 | CC §13 |
| `office_engine/docs/implementation/FR-CC-M4-01.md` | Added | 关闭评审；当前为 BLOCKED | CC §13 |
| 仓库中排除 `venv` / `.git` 的 `*.py` | Comment-only | 覆盖 189 个 Python 文件，补齐缺失模块/类/API/复杂私有函数中文说明；不改变运行逻辑 | 负责人本轮明确指令 |
| `office_engine/docs/implementation/CC-M4-01_实施验收报告_v0.3.md` | Added | 最终实施与验收报告，提交负责人关闭评审 | CC §13 |

测试基线的代码 SHA-256 与文件哈希见 `evidence/CC-M4-01/manifest.txt`。

## 6. 偏离与停止条件

- Deviation：None。未修改公开工具 Schema、M2/M3 冻结实现或权限语义。
- CC §12 Stop Condition：未触发技术越界。完整 Registry embedding 元数据外发及后续候选元数据聊天重排均在各自明确授权后进行。原始历史 IHR-008 保留此前一次请求在授权前被自动审批拒绝且未执行的事实；负责人之后另行授权隔离测试，执行记录见 IHR-010。未通过其他工具或间接路径绕过原拒绝。

## 7. 遗留问题

| ID | 问题描述 | 类别 | 级别 | 状态 | 责任方 |
|---|---|---|---|---|---|
| OI-001 | 完整 Registry metadata embedding 外发权限此前未确认，导致 Provider 验收阻断。 | 外部数据传输授权 | Resolved | Closed | 2026-11-19 项目负责人明确授权发送 757 个模型名称、描述及 `_rec_name` 至 OpenAI embedding；真实测试已执行并保留结果。此前截断调用的接收状态仍 UNKNOWN，不用于本轮评分。 |
| OI-002 | 历史版本的完整 Registry Top-5 为 18/40，分页计数及结果集合不一致。 | 技术 / 验收 | Closed — final retest PASS | Closed | ATR-RUN-005 达到 Top-5 40/40；同一 Thread 两遍分页各返回 757/757，逐页排序完全一致；未硬编码模型或盲测答案。原失败记录仍保留。 |
| OI-003 | GPT 聊天候选重排此前在单独授权前被阻止；负责人后来明确授权隔离测试并已执行。 | 候选试验 | 非关闭门禁 | Completed | 见 IHR-010；实验未满足产品 Top-5 验收，未修改产品路由或接入聊天重排。 |

## 8. 移交摘要

Implemented in current working tree：CC-CHANGE-001～003 均有最终真实 Provider / Agent 证据；CC-PRESERVE-001～006 定向回归满足。本 CC 无冻结验收阻断项，待负责人评审并批准正式关闭。详细结论见 IHR-011～013 与 `CC-M4-01_实施验收报告_v0.3.md`。本报告不自行宣布关闭，不提交 Git。
