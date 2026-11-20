# FR — CC-M4-02 意图理解与任务规划

## 0. 文档治理

本 FR 依据冻结 CC-M4-02 v0.2、对应 IHR / ATR、最终评审报告及项目负责人的明确关闭批准，逐项评估本 CC 的实施义务。FR 评估 Coding Contract Closure，不代表代码合并或发布批准。

## 1. 关闭元数据

| 字段 | 值 |
|---|---|
| Intent ID / FR ID | CC-M4-02 / FR-CC-M4-02 |
| FR 版本 / 日期 | v0.1 / 2026-11-20 |
| CC 基线 | `CC-M4-02_意图理解与任务规划_v0.2.md`（FROZEN） |
| IHR / ATR | `IHR-CC-M4-02.md` / `ATR-CC-M4-02.md` |
| HVR | N/A；来源：冻结 CC §8 和 Implementation Plan v0.1，中间 CC 不执行 UI HVR |
| 模块 | `office_engine_m3`；必要的项目内 Provider 审计测试支持 |
| 上游基线 | M4 TDD v0.2（FROZEN WITH OPEN ITEMS）；M4 Implementation Plan v0.1（FROZEN） |
| 数据库 / Provider | 仅 `odoo18e_llm` / OpenAI GPT-5.6 Luna (`gpt-5.6-luna`) |
| 当前代码基线 | 分支 `codex/cc-m4-02-intent-planning`，HEAD `46ff8e96fed2e7eee47494bcfb9d52e1f0c84512` 加本 CC 已测试工作树差异。关键提示实现 `llm_thread.py` SHA-256：`68589381a8bcea874d3c56ae627846388924a68066bedba2e73f721262af749f`；测试 `test_silent_retrieval.py` SHA-256：`5dd4d1f6974eab3333bda269a31d1fbe82d2619c6934c23e586abf7e6e6670c5`。代码尚未提交；测试日志在该实现状态下生成。 |
| 关闭批准 | 项目负责人于 2026-11-20 批准按冻结验收范围关闭 |

## 2. 冻结基线

| 来源 | 最终版本 | 相关性 |
|---|---|---|
| CC | CC-M4-02 v0.2 | 本 FR 的唯一验收义务来源 |
| SRS | v1.1.0 冻结历史基线 | 适用范围依冻结 M4 TDD §0.3 |
| DDD | N/A | M4 TDD 未增加业务聚合 |
| TDD | M4 v0.2 | 当前任务约束、Retriever 参数、错误结果边界和安全防护 |
| Implementation Plan | M4 v0.1 | 阶段 2 / CC-M4-02 范围和中间 CC 验收方式 |

## 3. 执行摘要

| 字段 | 值 |
|---|---|
| Closure Status | **SATISFIED — 已按负责人批准关闭** |
| CC-CHANGE | 4 / 4 SATISFIED |
| CC-PRESERVE | 7 / 7 SATISFIED |
| CC-TEST | 8 / 8 有冻结验收结论与证据 |
| 自动化验证 | SATISFIED：提示定向 12 项、M3 60 项、M2 Retriever 6 项均 0 failed / 0 error |
| 人工验证 | N/A（由 CC 明确排除） |
| 未批准偏离 | None |
| 未解决阻塞项 | 0 |
| Evidence Baseline Consistency | Valid：IHR / ATR 及 Provider 结果对应所列工作树基线；原始失败和不适用探索保留 |

## 4. Coding Contract Closure Matrix

| CC Obligation | 来源 | IHR / ATR 证据 | Workflow Evidence Status | Closure |
|---|---|---|---|---|
| CC-CHANGE-001：最新用户明确指令优先，局部修改保留其他有效条件 | CC §6 | IHR-002、IHR-004、IHR-009；ATR-001～004、RUN-043；提示回归 | Passed | SATISFIED |
| CC-CHANGE-002：依据 Registry / 只读回执动态调整计划 | CC §6 | IHR-008、IHR-009；RUN-043、RUN-067、RUN-068 | Passed | SATISFIED |
| CC-CHANGE-003：按 operation 拒绝不适用的 `query`，保持 legacy search | CC §6 | IHR-002；`test_discovery_query_is_rejected_for_describe_search_and_legacy_before_orm`；实际 Provider `describe(query=...)` 拒绝 | Passed | SATISFIED |
| CC-CHANGE-004：区分错误、权限拒绝和成功零结果 | CC §6 | IHR-007、IHR-009；普通用户 ORM、错误分类自动化及 RUN-067 | Passed | SATISFIED |
| CC-PRESERVE-001～002：单一公开 Retriever、legacy 调用和响应兼容 | CC §6 | IHR §2；ATR-RUN-071/072 定向回归 | Passed | SATISFIED |
| CC-PRESERVE-003～004：Registry / 业务数据权限、Domain、分页、排序和关联契约不回归 | CC §6 | IHR-007；普通用户 ORM / Oracle；ATR-RUN-071 | Passed | SATISFIED |
| CC-PRESERVE-005：M2/M3 文件、版本、Accept/Reject/Finalize、安全与确认语义不变 | CC §6 | IHR §2；ATR M2/M3 回归；本 CC 未纳入 Office 写操作 | Passed | SATISFIED |
| CC-PRESERVE-006～007：不采集隐藏推理 / Oracle，不建设 M5 全历史上下文系统 | CC §6 | IHR-009；Provider 请求与独立 Oracle 隔离核对；变更范围审查 | Passed | SATISFIED |
| CC-TEST-001：多条件与真实 ORM 查询 | CC §8 | ATR-RUN-043、RUN-067；隐藏 Oracle；RCA-009 | Passed | SATISFIED |
| CC-TEST-002～003：最新指令优先与局部条件保留 | CC §8 | ATR-RUN-043 两轮同 Thread 任务及 Oracle；提示回归 | Passed | SATISFIED |
| CC-TEST-004：动态规划、元数据依据与实质歧义澄清 | CC §8 | ATR-RUN-043、RUN-068；RCA-009 及层级身份 Oracle | Passed | SATISFIED |
| CC-TEST-005～006：operation 参数、Provider / Execute / ORM 契约 | CC §8 | 参数拒绝自动化覆盖确切 `search(query=...)` / describe / legacy 边界；Provider 实际负向调用及 Schema / Execute 审计；普通用户 ORM | Passed | SATISFIED |
| CC-TEST-007：当前权限与零结果 | CC §8 | 普通用户 ORM、ACL / Record Rule 与零结果错误分类测试；ATR-RUN-071 | Passed | SATISFIED |
| CC-TEST-008：兼容、调用量与受影响回归 | CC §8 | ATR-RUN-070（12）、RUN-071（60）、RUN-072（6）、RUN-073 清理复核 | Passed | SATISFIED |

## 5. Implementation Closure Assessment

| CC-CHANGE | 实际变更 | 证据 | 状态 |
|---|---|---|---|
| CC-CHANGE-001/002 | 在现有 Thread 指引中维护最新指令优先、未修改条件保留，并依据 Registry 与只读结果动态规划；增加关系 ID 来源、自关联深度、条件完整及不得无查询报零规则 | IHR-002、IHR-008、IHR-009；当前实现 hash 见 §1 | SATISFIED |
| CC-CHANGE-003 | 在现有 Retriever operation 分发边界拒绝不适用参数，复用 `INVALID_QUERY`；不改公开 Schema / 错误码 | IHR-002；参数拒绝自动化与 Provider 证据 | SATISFIED |
| CC-CHANGE-004 | 保持错误与合法零结果区分，通用提示要求依据成功完整回执再报告结果 | IHR-007、IHR-009 | SATISFIED |

## 6. Preservation 与防护评估

| CC-PRESERVE | 影响 / 回归证据 | 状态 |
|---|---|---|
| 001～002 | 工具名、Schema 和 legacy search 未变化；M2 Retriever 6 项回归通过 | SATISFIED |
| 003～004 | Registry 元数据边界、当前用户 ORM、ACL / Record Rules、Domain 搜索性、分页和关联结果由自动化及普通用户数据验证 | SATISFIED |
| 005 | 无 M2 Office 文件写入；M3 60 项与 M2 Retriever 6 项回归通过 | SATISFIED |
| 006～007 | 不采集隐藏 Chain-of-Thought；Oracle 未注入 Agent / Provider；未建设 M5 上下文机制 | SATISFIED |
| 适用的独立 TDD Guardrail | 本 CC 的执行防护均通过 CC-PRESERVE-001～007 表达；未增加 CC 外部 Guardrail 义务 | N/A（理由已列） |

## 7. 自动化验证评估

冻结 CC 的 CC-TEST-001～008 均在 §4 有状态及证据。最终提示组装测试 12 项、`office_engine_m3` 60 项、M2 Retriever 6 项均为 0 failed / 0 error；ORM 清理及测试审计 allowlist 复核 PASS。RUN-069 的旧提示文本断言失败经更新后由 RUN-070 通过，属于已解决的测试断言问题。真实 Provider 中间失败作为探索 / 迭代证据保留，不覆盖最终目标路径证据；最终 Provider 结果、工具执行参数、Oracle 差异分别见 ATR 和最终评审报告。

## 8. 人工验证评估

```text
Human Verification: N/A
Source: CC-M4-02 v0.2 / Implementation Plan v0.1
Reason: 中间 CC 以自动化与组件集成验收；真实 UI HVR 与人工 Accept/Finalize 属于 CC-M4-05。
```

N/A 不等于 PASS；此处为契约规定的不适用。

## 9. 偏离与停止条件评估

| 项目 | 结果 |
|---|---|
| 未批准偏离 | None |
| 冻结 TDD / Plan 变更 | None |
| 公共接口、权限或错误码变更 | None |
| 触发且未解决的 Stop Condition | None |
| 测试 Runner 证据事件 | v0.3 重跑错误覆盖同名结果 JSON；原始 SDK 审计保留，拒绝重跑结果另存，后续 Runner 保护及 ORM 清理复核通过。已解决，不伪称原结果 JSON 完整 |

## 10. 未关闭事项 / Findings / Evidence Gaps

| ID | 来源 | 说明 | Closure Impact | Human Judgment Required | 依据 |
|---|---|---|---|---|---|
| FIND-01 | ATR / RCA-009 | RUN-029、RUN-063～066 历史 Provider 失败；后续修复后对应 CC-TEST-001/004 目标场景通过 | Non-Blocking | No | 原失败完整保留；最终运行满足冻结验收，不把失败轨迹改写为通过 |
| FIND-02 | ATR | “客户总数”探索的业务口径及 Oracle 不充分，状态 NOT SCORABLE | Non-Blocking | No | 非冻结 CC 必测任务；不以此断言产品通过或失败 |
| FIND-03 | RCA-009 / ATR | v0.3 原结果 JSON 被错误重跑流程覆盖 | Non-Blocking | No | 原 SDK 审计保留，拒绝重跑错误另存；后续 RUN-073 核实数据清理 |

没有 Mandatory CC Obligation 的缺失证据或未解决失败；以上发现均有证据边界与处置，不需要永久豁免。

## 11. Evidence Baseline Consistency

| Evidence Source | 基线 | 对当前实现有效 | 依据 |
|---|---|---|---|
| IHR | HEAD `46ff8e96…` + CC 工作树差异 | Yes | 记录分支、文件范围与实施状态；关键提示和测试文件 SHA-256 见 §1 |
| ATR | 同上工作树执行结果 | Yes | RUN-070～073 在最终提示 / 测试状态下执行；Provider 运行记录及 ORM 清理按 Thread / fixture 对应 |
| HVR | N/A | N/A | CC 不要求 HVR |

Evidence Baseline Status：**Valid**。此 FR 记录 CC 关闭，不声称相关代码已提交或合并。

## 12. Done Criteria Assessment（CC §12）

| Done Criterion | 证据 | 状态 | Gap |
|---|---|---|---|
| §12-1：CC-CHANGE-001～004 有当前实现及证据 | IHR §2、§6；RCA-009；ATR | SATISFIED | — |
| §12-2：CC-PRESERVE-001～007 有回归且无未解释契约破坏 | IHR §2；ATR-RUN-070～073 | SATISFIED | — |
| §12-3：CC-TEST-001～008 状态和证据齐全，无未解决 BLOCKED / NOT RUN | ATR §2～4；§4 矩阵 | SATISFIED | — |
| §12-4：`search(query=...)` fail-closed 且 legacy search 通过 | Retriever 单测、Execute/ORM 边界、Provider Schema 与 legacy 回归 | SATISFIED | — |
| §12-5：Oracle 核验约束覆盖；不使用隐藏推理 | RUN-043、RUN-067、RUN-068；独立 Oracle | SATISFIED | — |
| §12-6：IHR、ATR、Final Report 对应已验证基线 | IHR、ATR、当前 FR 与文件 SHA | SATISFIED | — |
| §12-7：仅自动化 / 组件集成，无 UI HVR，提交负责人关闭评审 | 测试日志；项目负责人 2026-11-20 明确批准 | SATISFIED | — |

## 13. Final Closure Determination

```text
Final Closure Status: SATISFIED
Basis:
- 冻结 CC 的全部变更义务和保留义务均有实施 / 回归证据。
- CC-TEST-001～008 均有状态与有效证据；迭代失败、探索性 NOT SCORABLE 项和证据事故均原样保留并已分类。
- 中间 CC 的 Human Verification 按 CC 规定为 N/A。
- 未发现未解决的未经批准偏离或阻塞性 Evidence Gap。
- 项目负责人已批准按冻结验收范围关闭。

本结论仅关闭 CC-M4-02，不代表合并或发布批准，也不代表 M4 整体完成。
```

## 14. Handoff to Human Review

| 项目 | 结果 |
|---|---|
| Closure Assessment Complete | Yes |
| 负责人关闭决定 | 已记录：批准按冻结验收范围关闭 |
| Blocking Items | 0 |
| Non-Blocking Known Items | 历史 Provider 失败轨迹、“客户总数”NOT SCORABLE、v0.3 结果 JSON 覆盖事件；均保留证据及边界 |
| Merge / Release Decision | 未作出；不属于 FR 职责 |

## 附录 A — Evidence Reference Index

| 类型 | 路径 | 用途 |
|---|---|---|
| CC | `CC-M4-02_意图理解与任务规划_v0.2.md` | Closure Authority |
| IHR | `IHR-CC-M4-02.md` | 实施事实与边界 |
| ATR | `ATR-CC-M4-02.md` | Provider / 自动化 / ORM 证据索引 |
| Final Report | `evidence/CC-M4-02/CC-M4-02_Final_Report.md` | RCA、结果差异及完整评审摘要 |
| RCA | `../verification/m4_rca/RCA-009_CC-M4-02_Relation_Query_Planning.md` | 失败链及逐项根因 |

## 附录 B — 版本历史

| 版本 | 日期 | Closure Status | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-20 | SATISFIED | 根据冻结 CC、IHR / ATR 和负责人批准完成当前关闭评估 |
