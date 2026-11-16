# CC-M3-02 — 实施历史记录（IHR）

## 0. 文档治理

本 IHR 记录 CC-M3-02 的实施事实；§4 历史条目仅追加。TDD v0.4、Implementation Plan v0.3 和 CC-M3-02 v0.2 为冻结基线。自动化测试事实记入对应 ATR，不以本 IHR 代替验收。

## 1. 执行元数据

| 项目 | 记录 |
|---|---|
| IHR 文档 | `IHR-CC-M3-02-Complete-Data-Office.md` |
| CC | [`CC-M3-02_完整数据至Office_v0.2.md`](../../CC-M3-02_完整数据至Office_v0.2.md)，v0.2，Frozen with open gates |
| 授权记录 | `CC-M3-02-002`；兼容性与真实 Provider 测试范围扩展：`CC-M3-02-003` |
| TDD / Plan | TDD v0.4 / Implementation Plan v0.3 |
| 模块 | `office_engine_m3` |
| 工作类型 | 下游 addon 功能实现 |
| 实施负责人 | Codex；负责人 Li Jianqiang |
| 开始日期 | 2026-11-15 |
| Git 分支 / 基线 | 当前分支 `codex/cc-m3-01-provider-acceptance`；基线 `1b64e64` |
| 当前实施状态 | 实施与范围内测试已完成；提交负责人进行 CC 关闭评审，尚未自行关闭 |

## 2. Coding Contract 基线

| 项目 | 引用 |
|---|---|
| 实施范围 | CC §3–8 |
| 测试契约 | CC §10；`TEST-DATA-001`–`006`、`TEST-XLSX-001`、`TEST-LIFE-001`、`TEST-REG-001` |
| 完成定义 | CC §13 |
| 数据与 Provider 边界 | CC §9；授权记录 `CC-M3-02-002` / `CC-M3-02-003` |

## 3. 当前实施状态摘要

| 项目 | 状态 |
|---|---|
| CC §4.1 / §5 行为落实 | M3 主流程及新建 / current-source Candidate 路径已实现；见 ATR 中逐项状态 |
| Preservation Impact | 有界 M2 兼容性扩展；不改变 M2 接受、拒绝、Finalize 的用户决策或现有 `create` direct-V1 行为 |
| 代码偏离 | M2 文件面超出 CC v0.2 原许可；负责人授权 `CC-M3-02-003`，设计边界记于 `TDD_office_engine_m3_v0.4_Implementation_Compatibility_Addendum_20261116.md` |
| Stop Condition | IHR-002 是 2026-11-15 的历史停止记录；其问题由负责人授权后以最小兼容扩展解决，不删除该历史记录 |
| Open Issues | 本 CC 规定的真实 Provider 数据完整性、资源 / freshness、故障注入及 Candidate 生命周期证据已补齐；UI HVR 仍属于 CC-M3-03 |
| 当前状态 | **Ready for CC-M3-02 closure review — 等待负责人评审，不代表已关闭** |

## 4. 实施历史条目

### IHR-001

| 字段 | 记录 |
|---|---|
| 时间 | 2026-11-15 |
| 阶段 | Implementation |
| Action | 记录负责人对 CC-M3-02 的独立 Coding Authorization；建立 CC 专属 IHR / ATR 跟踪基线。 |
| Reason | 四项 OPEN 前置最小可行性 Spike 已通过，满足 CC-M3-02 实施入口条件。 |
| Files / Components | `AUTHORIZATION_RECORDS.md`；本 IHR；CC-M3-02 ATR |
| Contract Reference | CC §13.1；授权记录 `CC-M3-02-002` |
| Upstream Reference | M3 TDD v0.4 / Implementation Plan v0.3 |
| Result | Completed；代码实现尚未开始 |
| Deviation | None |
| Follow-up | 按 CC 范围实现；Provider 调用仍逐次等待专项授权。 |

### IHR-002

| 字段 | 记录 |
|---|---|
| 时间 | 2026-11-15 |
| 阶段 | Stop Condition |
| Action | 静态核对 M2 initial / fileless Candidate 的登记、验证、接受路径；确认新建导出无法同时满足 Candidate → Accept 与“不得使用 fileless direct-V1 / 不得修改 M2 生命周期”的冻结约束。停止产品代码实施。 |
| Reason | CC §12 要求遇到 M2 Candidate / confirmation 行为需改变时停止并作 TDD 影响评审。 |
| Files / Components | `office_engine_m2/services/workbook_version_service.py`；`office_engine_m2/services/edit_orchestrator.py`；CC-M3-02 §3.2、§8、§12；详见同目录 `Candidate_lifecycle_stop_20261115.md` |
| Contract Reference | CC §4.2、§5 CC-CHANGE-005、§6 CC-PRESERVE-003、§12、§13 |
| Upstream Reference | M3 TDD v0.4 `T-M3-VERSION-001`、API-EXPORT-RECEIPT-001 |
| Result | Blocked；未修改产品代码，未访问数据库，未发起 Provider 请求 |
| Deviation | None；按冻结 Stop Condition 停止 |
| Follow-up | 负责人先决定是否修订 TDD / CC 以支持安全的 source-less Candidate Accept；取得更新基线和对应授权前不恢复受影响实施。 |

### IHR-003

| 字段 | 记录 |
|---|---|
| 时间 | 2026-11-16 |
| 阶段 | Authorized compatibility resolution |
| Action | 按 `CC-M3-02-003` 继续实施；以 M2 fileless initial 的登记和文件完整性检查承载 M3 source-less Candidate，但延迟 direct-V1 发布，保留用户 Accept / Reject 和 M2 Finalize；current-source 继续走 M2 edit Candidate。Route B 的最小空白 XLSX 仅作 Hosted CI 输入载体，不作为业务模板或 M2 输入附件。 |
| Reason | 负责人明确授权以最简单可靠方式解决新建工作簿 Candidate 生命周期兼容性，并允许必要 M2 兼容修改。 |
| Files / Components | `office_engine_m2/services/workbook_version_service.py`、`edit_orchestrator.py`、`candidate_validator.py`、`office_workbook_version.py`；新增 M3 exporter / collector / handoff / verifier；设计记录见 TDD compatibility addendum。 |
| Contract Reference | CC-M3-02-003；M3 TDD v0.4 §6 / §9 / `T-M3-VERSION-001`；兼容性 addendum §1–3 |
| Result | 实现完成并有定向自动化测试；未绕过用户确认门禁 |
| Deviation | M2 文件面不在 CC v0.2 原允许清单内；负责人授权的有界偏离，未修改上游 `odoo-llm` |
| Follow-up | 真实 Provider 148 条输出契约与 Candidate 生命周期未通过，按 ATR 保持 Blocked；不关闭 CC。 |

### IHR-004

| 字段 | 记录 |
|---|---|
| 时间 | 2026-11-16 |
| 阶段 | Module / automated verification |
| Action | 通过 ORM 升级并核验 `office_engine_m3` 为 `18.0.2.0.0`，确认 `data_integrity_receipt_json` 注册；运行 M3 `test_export.py` 和三个定向 M2 回归测试文件。 |
| Reason | 验证全量收集、Route B 合成交接、M2 Candidate 兼容以及 legacy M2 行为未被破坏。 |
| Files / Components | 新增 / 修改 `office_engine_m3/**`；受影响 M2 文件见 §5；运行证据位于 CC-M3-02 evidence 目录。 |
| Contract Reference | CC §10；ATR `ATR-RUN-001` |
| Result | **55 项定向 Odoo 测试通过**（M3 export 14 + M3 Retriever 8；M2 11 + 5 + 11 + Retriever integration 6）；覆盖 148 条 100+48、251 条三页 Collector、count drift / identity 拒绝、失败关闭 / root、relation、payload 资源限额、不自动重放、Candidate 生命周期及 receipt v3；`py_compile`、`git diff --check` 通过。 |
| Deviation | 全 addon 测试套件未作为本次通过证据；只报告明确执行的定向测试。 |
| Follow-up | 完成缺失的全量、资源、freshness 和失败注入测试；不把定向结果当作整个 CC 通过。 |

### IHR-005

| 字段 | 记录 |
|---|---|
| 时间 | 2026-11-16 |
| 阶段 | Real Provider integration |
| Action | 使用真实 `OpenAI GPT-5.6 Luna` / Hosted CI 和合成 148 条联系人测试。首次真实文件含 148 IDs 但 root 额外带有 `__office_parent_id`，被 projection 门禁拒绝；修正 Provider 指令后两次请求超时，没有可用 Candidate。 |
| Reason | 验证 Provider 对 handoff 数据的实际读取、XLSX 生成及本地客观完整性门禁。 |
| Files / Components | `real-provider-148-*.log`、对应 summary JSON、合成诊断 XLSX；详细结论见 ATR `ATR-RUN-002`。 |
| Contract Reference | CC `TEST-DATA-001`、`TEST-XLSX-001`；M3 TDD `API-HANDOFF-001` / `API-EXPORT-RECEIPT-001` |
| Result | Provider 请求真实发生，文件生成路径曾返回文件；**最终 Provider output contract、Candidate 接受及真实 Accept / Finalize 未通过**。两次后续请求 error 为 `provider_connection_or_timeout`，Adapter 标记 `not_automatic`，本轮未再试发。 |
| Deviation | 无；输出身份不符合契约即拒绝，未创建可接受完整 Candidate、未推进 Current。 |
| Follow-up | 需在有可用 Provider 连接时继续修正 / 验证；CC-M3-02 保持 In Progress。 |

### IHR-006

| 字段 | 记录 |
|---|---|
| 时间 | 2026-11-16 |
| 阶段 | Implementation completion / closure evidence |
| Action | 检查旧 148 行 Provider XLSX 并放宽通用核验器对空白辅助列的布局限制；通过故障注入修复关系字段类型核验缺陷和 Candidate 返回摘要取值缺陷；补齐 M2O / O2M / M2M、missing relation / inverse、handoff digest、Provider 无文件及资源边界测试；执行隔离事务 freshness、真实 148 行 Accept → Finalize 与 251 行三页真实 Provider 验证。 |
| Reason | 旧 XLSX 有 148 条唯一连续身份，`__office_parent_id` 148 行全空且没有关系集合；它是无业务意义的额外辅助列。必须以同一事务源记录证明最终数据，而不能仅以行数推断字段正确。 |
| Files / Components | `office_engine_m3/services/export_verification.py`、`export_orchestrator.py`、`tests/test_export.py`；CC-M3-02 ATR、证据目录、TDD v0.4 compatibility addendum。 |
| Contract Reference | CC `TEST-DATA-001`–`006`、`TEST-XLSX-001`、`TEST-LIFE-001`；TDD v0.4 `API-HANDOFF-001`、`API-EXPORT-RECEIPT-001`。 |
| Result | M3 export suite **20/20**；先前通过且本轮未改动的 M3 Retriever 8 项、M2 定向回归 33 项继续适用。真实 Provider 148 行 source→handoff→XLSX IDs/Name/Email 逐行完全一致，Candidate 创建前 Current 不变；Accept 后版本成为 Current，Finalize SHA 与 Candidate SHA 相同。真实 Provider 251 行输出 251/251 身份及字段精确匹配。并发 insert/update/delete 下单一 `REPEATABLE READ` 事务仍收集原 3 条及原值，3 条测试记录已通过 ORM 清理。 |
| Deviation | 实施核验契约允许 root 表中可选且全空的 `__office_parent_id` 及其他全空辅助列出现在任意列位置；任何非空未知列、root parent identity、缺失 / 重复 / 错值仍拒绝。记录于 TDD compatibility addendum §5；不改写冻结 TDD / CC。另修正关系表验证器从本地计划读取字段类型，以及 Candidate 输出的 source / Provider input SHA 嵌套路径。 |
| Follow-up | 向负责人提交 CC-M3-02 关闭评审；等待决定。CC-M3-03 UI HVR 尚未执行。 |

## 5. 实际变更清单

| 文件 / 路径 | 动作 | 实际变更 | CC 来源 |
|---|---|---|---|
| `AUTHORIZATION_RECORDS.md` | Modified | 追加 Coding Authorization `CC-M3-02-002`；保留冻结期授权历史 | CC §2 |
| 本 IHR | Added | 记录授权和 Candidate lifecycle Stop Condition | CC §12 |
| `ATR-CC-M3-02-complete-data-office.md` | Added | 初始化测试矩阵；所有实施测试保持 NOT RUN | CC §10 |
| M2 lifecycle / version services | Modified | 按 `CC-M3-02-003` 增加受约束的 M3 source-less Candidate 接受兼容性和 current-source edit attempt 存取；原 `action="create"` direct-V1 行为保留 | M3 TDD compatibility addendum；CC `TEST-LIFE-001` |
| `office_engine_m3/**` | Added / Modified | 单一 Office Tool `export_records`；当前用户 ORM 分页与直接关系批量收集、Route B handoff、只读 XLSX identity verifier、Candidate receipt / 流程；本轮最终 M3 export 定向套件 20 项通过 | CC §5、§6、§10 |
| M3 TDD compatibility addendum | Added / Updated | 记录空白 carrier、受限 M2 兼容扩展、空白辅助列核验契约及后续验证结果；不替换冻结设计 | CC-M3-02-003；IHR-006 |
| `ATR-CC-M3-02-complete-data-office.md` | Modified | 记录最终自动化、边界、并发 freshness、真实 Provider 与生命周期证据；等待关闭评审 | CC §10；IHR-006 |

## 6. 偏离与停止条件记录

- M2 兼容性扩展与 CC v0.2 原文件面不一致；有负责人明确授权并由 versioned TDD compatibility addendum 记录，不改写冻结基线历史。
- 未修改上游 `odoo-llm`。M2 修改保持在 Candidate / receipt / review 兼容点，未改变 M2 用户确认机制或原 `create` direct-V1 行为。
- 新建专用 Git 分支尝试因沙箱 `.git` 只读失败；继续使用当前已检出的 Codex 分支，未请求提升 Git 权限。
- 数据库仍限定为现有开发库 `odoo18e_llm`；不创建数据库，不触及既有业务数据。

## 7. 遗留问题与后续

| 项目 | 状态 | 责任阶段 |
|---|---|---|
| 新建工作簿 Candidate Accept 契约 | 已通过最小兼容扩展并由 synthetic fixture 验证；设计偏离见 addendum | CC-M3-02 |
| 148 条与 251 条真实 Provider 输出、资源 / freshness / 故障注入 | PASS；详见 ATR-RUN-003 | CC-M3-02 |
| 真实 Provider Candidate → Accept → Finalize | PASS；148 行合成数据已通过，最终文件保持 `PARTIALLY_VERIFIED` | CC-M3-02 |
| 真实 Agent UI HVR | Deferred | CC-M3-03 |

## 8. 移交摘要

```text
CC：CC-M3-02 v0.2
TDD / Plan：M3 TDD v0.4 / Plan v0.3
Coding Authorization：CC-M3-02-002
Compatibility Authorization：CC-M3-02-003
Implementation：代码和 CC-M3-02 范围验收证据完成；提交负责人关闭评审
Automated Tests：M3 export 20 项本轮通过；先前 M3 Retriever 8 项、M2 回归 33 项通过；三项上游 Adapter 离线资源检查通过
Real Provider：148 与 251 行 XLSX 均精确匹配 source；148 行已 Accept → Finalize 同 SHA；较早两次超时后续已恢复，配置 timeout 保持 120 秒
Open：等待负责人进行 CC-M3-02 关闭评审；CC-M3-03 UI HVR 另行执行
```
