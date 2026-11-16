# CC-M3-03 Final Report — 静默检索与最终 HVR

## 状态

**CC-M3-03 已关闭（SATISFIED）。** 非流式 Silent Retrieval、附件上下文回归和 148 单真实 Agent 导出均完成；实际浏览器下载文件 SHA 已补齐。确定性的 `TEST-SILENT-002`–`005` 可见边界由自动化及本轮实际运行路径证据验证。`TEST-REG-001` 为范围化 PASS：M2 定向 12 项、M3 42 项和真实 HVR 通过，本轮未发现回归。M2 全量原始运行仍有 13 failures / 69 errors，其中 67 个 worker EOF 原因未明；不声称全量回归通过，也不把原因不明错误归类为环境问题。第二家公司依赖测试为本 CC 不适用项。正式关闭评估见 [`CLOSE-CC-M3-03-20261116.md`](CLOSE-CC-M3-03-20261116.md)。

## 已完成工作

- 在支持的非流式 Office 路径实现下游 Silent Retrieval。成功纯 Retriever 消息在通知前标记，不显示在 Discuss 历史和 SSE 消息事件中；查询失败时恢复错误消息可见。原消息、参数、结果和上下文继续保存。
- 增加通用 Agent 模型发现、关系表规划和 `export_records` Candidate 流程指引。
- 更新 OpenAI Tool Calling 对现有 Office 工具的有效 Schema 格式化。
- 增加 Hosted CI 源单元格精确复制指引和按日期字段核验 XLSX 的实现。
- 增加自动化测试，覆盖静默分类、Discuss / SSE 边界、错误恢复、混合工具可见性及流式安全边界。
- 修复 M3 附件上下文缺口：完整扫描 Thread 附件关系，不受 25 条 LLM 历史上限影响；每次 Provider 参数准备加入纯文本附件引用，不传二进制；用户明确文件名时优先选择历史附件。增加“整理成 Excel”新建 Odoo 导出路由及无需上传源文件指引。

## 验证结果

- `office_engine_m3`：当前 42 项测试，0 failures，0 errors；包含 100+ 消息附件上下文、历史文件优先和静默消息保留回归。
- M2 定向回归：12 项，0 failures，0 errors；覆盖 `TestWorkbookVersionState` 全类及 fileless Route B 导出工具绑定。
- 真实 Odoo UI + OpenAI GPT-5.6 Luna：Agent 自主发现模型、字段和关联，生成 Candidate 395；在页面收到用户明确回复“接受”后执行 Accept 和 Finalize。最终附件已发布。
- 最终附件 ORM 回读独立核验：148 / 148 个订单、185 / 185 条明细、185 / 185 组父子关联；请求字段和值均匹配，没有重复或错配；浏览器实际下载文件、最终附件、Candidate / receipt 的 SHA 相同：`92d6c0ac972bf406eb220701a637d7b36668c3950821b6c61e2276f5b948a5ee`。下载验证见 `browser_download_verification_v395.json`。
- 合成数据清理：按唯一标记通过 ORM 清理，清理后计数均为 0。
- Odoo 平台校验状态仍为 `PARTIALLY_VERIFIED`；该状态在 Accept 前对用户可见，Finalize 后仍保留。独立的 CC 数据核验通过，但没有替换或修改平台状态。

## TEST-REG-001 范围化结论及全量运行记录

**范围化结论：PASS（本轮未发现回归），已提交负责人关闭评审。** M2 定向 12 项、M3 42 项和真实 Agent HVR 覆盖本 CC 的 Candidate 生命周期、Route B 工具绑定、导出、Accept / Finalize 与文件结果。变更范围只涉及 M3 下游，没有修改 M2 或 OfficeCore 源码。

M2 全量运行仍保留为非通过原始结果：常规发现流程因缺少 `SETATTR_SOURCES` 中止；兼容 shim 运行 208 项有 13 failures / 69 errors，其中 67 个 OfficeCore worker pipe EOF 的具体原因未明，另有一次 failed-create 后的 `current` 读取错误。没有把这些错误归类为环境问题，也没有证据证明它们由本轮 M3 变更引入。依赖第二家公司的 1 项失败和 1 项 setup error 列为本 CC 不适用；不要求创建第二家公司。原始日志（包括 EOFError trace）已原样归档在本 CC evidence 目录。该全量运行未能证明 M2 整体 PASS，也未显示本轮 M3 范围内的明确回归。

确定性 Silent Retrieval 边界 `TEST-SILENT-002`–`005` 已依据自动化及本轮实际非流式路径证据验收 PASS。Provider 未在 HVR 中生成的随机场景明确记录为未实际观察，不作为额外待执行验收项。

## 附加 HVR 问题调查

失败线程 264 的原始用户消息 `461912` 没有附件，Thread 当时 `tool_ids=[]`；“整理成一个 Excel”未匹配 fileless 路由，因此 Provider 没有 Retriever / Office 工具。这不是 Silent Retrieval 丢失上下文，也不是 Office Schema 要求上传。另确认 M2 附件定位代码限制最近 25 条用户消息，M3 已下游修复并为 106 条后续消息及历史附件优先选择增加回归。原始 OpenAI HTTP 请求体未由当前系统持久化；证据依据为 ORM 消息、Thread 工具绑定状态和实际上下文构建逻辑。本次修复后没有再次调用真实 Provider，压力场景证据属于自动化回归。

## 治理状态

未修改冻结 TDD、Plan 或 CC；未修改上游 `odoo-llm`、M2 addon、OfficeCore 或本次合成数据之外的业务记录。实现及证据按 CC-M3-03 范围提交，关闭记录与推送状态见 [`CLOSE-CC-M3-03-20261116.md`](CLOSE-CC-M3-03-20261116.md)。本 CC 不批准合并、部署或发布。

详细记录见 `ATR-CC-M3-03-Silent-Retrieval.md`、`IHR-CC-M3-03-Silent-Retrieval.md`、`HVR-M3-03-001.md` 及本目录中的证据 JSON / 日志。

## 8. Coding Contract Closure Matrix

当前实现基线：`9d6918fd4357201b3b514fe6d3001aff43b2df32`。

### 8.1 必需变更

| CC 义务 | 证据 | 状态 | 评估 |
|---|---|---|---|
| `CC-CHANGE-001` 非流式路径在首次通知前标记成功纯 Retriever 消息，并过滤用户 SSE / Discuss / Bus 可见面 | ATR `TEST-SILENT-001/004`；真实线程 677 及 `silent_path_observations.md` | SATISFIED | 当前实际非流式 Office 路径和自动化覆盖通知时序、历史与事件过滤；原消息仍保留。保证范围不外推至未验证路径。 |
| `CC-CHANGE-002` 错误、零结果、澄清、final、Office / Candidate / 确认及 mixed tool-call 遵守可见边界 | ATR `TEST-SILENT-002/003`；`test_silent_retrieval.py`；HVR | SATISFIED | 确定性分支由自动化覆盖，最终回复和 Office / Candidate 生命周期由 HVR 覆盖；不声称 Provider 在 HVR 随机触发所有分支。 |
| `CC-CHANGE-003` 流式路径保持工具续接及失败状态可见，并记录 generator 限制 | ATR `TEST-SILENT-005`；路径和限制记录 | SATISFIED（安全可见边界） | 自动化确认流式消息不被静默标记或过滤；本轮未修复或声称验证上游 generator 续接。 |
| `CC-CHANGE-004` Agent 自主发现模型、选择字段、确定关系并编排 Retriever / Office | HVR §1；`hvr_actual_trace_thread_677.json`、`hvr_agent_plan_thread_677.json` | SATISFIED | 真实自然语言请求未注入模型名、字段、Domain 或工具参数；实际 Trace 显示 Agent 自主规划。 |
| `CC-CHANGE-005` 148 单和明细形成 Candidate；Accept / Finalize 后独立核验下载文件身份、字段、关联及 SHA | HVR §3–4；`workbook_verification_v395.json`、`browser_download_verification_v395.json` | SATISFIED | 148/148 订单、185/185 明细、185/185 父子关系均核对；浏览器下载 XLSX 与 Candidate / Finalize 附件一致，SHA-256 为 `92d6c0ac972bf406eb220701a637d7b36668c3950821b6c61e2276f5b948a5ee`。 |
| `CC-CHANGE-006` 定向自动化 / 集成回归及 IHR / ATR / HVR / FR 证据 | ATR §2–3；IHR；HVR；本 FR | SATISFIED | M3 42/42、适用 M2 定向 12/12，并完成最终真实 Agent UI HVR；原始失败日志与不确定项均保留。 |

### 8.2 保留要求

| CC 义务 | 证据 | 状态 | 评估 |
|---|---|---|---|
| `CC-PRESERVE-001` 静默只改变可见性；消息、参数、结果、上下文、状态、tool events 和诊断保留 | `TEST-SILENT-001/002`；HVR trace | SATISFIED | 静默消息保留于 `mail.message` 和后续 LLM 上下文；可见过滤按 CC 范围执行。 |
| `CC-PRESERVE-002` Candidate / Current / Accept / Reject / Finalize、版本、文件安全及用户确认门禁不变 | HVR §3–4；M2 定向 12 项 | SATISFIED | 用户先在页面明确 Accept，随后 Agent 执行 Accept / Finalize；Candidate 与交付附件一致。 |
| `CC-PRESERVE-003` 业务读取遵守当前用户 ORM 权限，不用 `sudo()`，不硬编码业务模型 / 字段 | IHR 变更审查；M3 / M2 回归 | SATISFIED | 本轮实现限于通用 Thread、Provider、消息和文件服务扩展；HVR 业务数据通过授权 ORM 查询。 |
| `CC-PRESERVE-004` 单一 Retriever、单一 Office Tool、M2 Route B 与 LLM + Hosted CI 文件内容生成 | IHR 变更清单；ATR `TEST-REG-001` | SATISFIED | 未增加独立公开工具或本地 Excel 内容生成器，保留 M2 文件生成与 Candidate 流程。 |

### 8.3 适用 TDD Guardrails

| Guardrail | 证据 | 状态 |
|---|---|---|
| `T-M3-MSG-001` 成功纯 Retriever 才可静默；错误、澄清、final、Office、确认可见；持久记录与上下文保留 | M3 42 项；HVR；IHR | SATISFIED |
| `T-M3-MSG-002` Bus 通知前标记；未覆盖路径不作全链路静默声明 | `TEST-SILENT-001/004`；实际非流式 HVR | SATISFIED（CC 指定路径） |
| `T-M3-MSG-003` 流式路径不误隐藏工具续接；不把未修复 generator 说成通过 | `TEST-SILENT-005`；ATR 限制说明 | SATISFIED（安全可见边界） |
| `T-M3-PRIV-001` 按 M2 外发政策最小化交给 Hosted CI，不记录或持久缓存完整 handoff payload | HVR 仅用合成数据；IHR / 数据处理与代码审查 | SATISFIED |

## 9. Automated Verification Assessment

| 检查 | 结果 | 关闭判定 |
|---|---|---|
| `office_engine_m3` 全套定向测试 | 42 项，0 failures，0 errors | SATISFIED |
| M2 受影响关键路径定向测试 | 12 项，0 failures，0 errors | SATISFIED |
| M2 全量兼容运行 | 208 项中 13 failures / 69 errors；67 个 OfficeCore worker pipe EOF 原因不明，另有 failed-create 后 `current` 错误 | 非绿色结果保留；不记 PASS、不归因环境或 M3。经负责人要求，第二家公司依赖的 1 项 failure 与 1 项 setup error 为本 CC N/A。范围化 `TEST-REG-001` 不依赖该全量套件通过。 |

全量运行缺少变更前基线；OfficeCore worker EOF 的具体原因仍未确定。因此本 FR 只作 CC-M3-03 范围结论：“本轮未发现明确回归”，不判断这些错误是否由其他因素引起。

## 10. Non-Blocking Known Items

| 项目 | 关闭影响 | 处置 |
|---|---|---|
| M2 全量兼容套件非绿色，worker EOF 原因未明 | Non-Blocking for this CC | 原始输出和 SHA 留存；不虚报 M2 全量 PASS。当前 M3 无 M2 / OfficeCore 源码变更，且适用 M2 定向路径通过。 |
| 第二家公司 fixture 测试 | N/A for this CC | 按负责人裁定，本轮不配置第二家公司。 |
| 流式 generator 续接能力 | Non-Blocking by frozen CC scope | 只验收安全可见边界；不修复上游，不宣称续接通过。 |
| 平台验收状态仍为 `PARTIALLY_VERIFIED` | Non-Blocking | HVR 向用户显示并保留此状态；独立核验只证明本 CC 要求的数据、关联与文件 SHA。 |
| Provider 未随机产生的 ACL / mixed-call / 澄清场景 | Non-Blocking | 确定性可见性由自动化验证；HVR 未观察的分支明确记录为未实际观察。 |

## 11. Final Closure Determination

**Final Closure Status: SATISFIED**

负责人于 2026-11-16 回复“同意 M3 收尾并准备关闭”，批准按已提交的范围化验收结论完成 CC-M3-03 收尾。所有必需 CC-CHANGE、CC-PRESERVE、适用 TDD Guardrail、自动化测试与真实 HVR 均有当前实现基线的证据；没有未解决的 CC 阻塞项或未授权偏离。

本结论关闭 CC-M3-03，不构成合并、部署或发布批准。M2 全量回归仍不通过，且其 worker 异常原因仍未确定。

## 12. Human Review Handoff

```text
Closure Assessment Complete: Yes
Human Review Required: 已由负责人于 2026-11-16 批准本 CC 关闭
CC-M3-03: SATISFIED / CLOSED
Implementation Code Commit: 9d6918fd4357201b3b514fe6d3001aff43b2df32
Automated Verification: M3 42/42; applicable M2 targeted 12/12
Human Verification: HVR-M3-03-001 PASS
TEST-REG-001: PASS (scope-limited; no CC-M3-03 regression identified)
Blocking Items: None
Non-Blocking Known Item: M2 full compatibility run remains 13 failures / 69 errors; 67 worker EOF causes unknown
Merge / Deploy / Release: Not approved by this FR
```

## 附录 A — 证据索引

| 类型 | 引用 | 用途 |
|---|---|---|
| Frozen CC | [`CC-M3-03 v0.2`](../../CC-M3-03_静默检索与最终HVR_v0.2.md) | 本次唯一 Coding Contract 关闭依据 |
| IHR | [`IHR-CC-M3-03-Silent-Retrieval.md`](IHR-CC-M3-03-Silent-Retrieval.md) | 变更与实施追溯 |
| ATR | [`ATR-CC-M3-03-Silent-Retrieval.md`](ATR-CC-M3-03-Silent-Retrieval.md) | 自动化与范围化回归证据 |
| HVR | [`HVR-M3-03-001.md`](HVR-M3-03-001.md) | 真实 Agent UI 与文件验收 |
| M2 全量分流 | [`test-run-005-m2-regression-status.md`](test-run-005-m2-regression-status.md) | 未解决错误的事实记录与范围判定 |
| Close record | [`CLOSE-CC-M3-03-20261116.md`](CLOSE-CC-M3-03-20261116.md) | 负责人审批及 Git 提交 / 推送结果 |
