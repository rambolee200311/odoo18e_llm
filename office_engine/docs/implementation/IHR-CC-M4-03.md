# CC-M4-03 实施记录（IHR）

## 文档状态

| 项目 | 内容 |
|---|---|
| CC | CC-M4-03 — 最终消息与失败恢复 v0.2 |
| 状态 | **CLOSED — 项目负责人于 2026-11-21 批准关闭** |
| 数据库 | 仅使用现有开发库 `odoo18e_llm` |
| M3 模块版本 | `18.0.7.0.7`；独立 ORM 会话确认已安装版本与清单一致 |
| Provider | OpenAI GPT-5.6 Luna（`gpt-5.6-luna`） |
| 范围 | 最终消息生命周期、Silent Retrieval、有限失败恢复及相关 M2/M3 回归 |
| Git | 按本轮批准的 CC-M4-03 关闭范围提交并推送 |

## 1. 实施结果

1. 保持 Odoo 自有事务管理，不在产品业务代码中增加显式 `cr.commit()`。非流式 Office SSE 在源生成器及其事务结束后才释放缓存事件；发生异常时丢弃尚未提交的事件。消息提交后通知失败时，持久化消息仍可重新读取。
2. 成功的纯 Retriever 内部消息继续静默并保留在 `mail.message`、工具回执及 Agent 上下文。中间错误不单独刷屏；最终助手答复、澄清、Office 结果及最终失败保持可见。
3. 增强当前任务恢复指引：按同一失败操作限制只读纠正次数；不重复无新证据的相同错误；权限拒绝停止；Office 状态未知时不盲目重发。
4. 根据 Thread 2002 的真实 Provider 失败，修正 Office 导出表格参数说明：根记录表 `source` 使用工具契约值 `root`，关系明细表 `source` 使用声明的 collection key；收到明确拒绝且 `operation_executed=false` 后不得原样重发，只有在 Schema 与错误信息能唯一给出修正值时才作一次定向修正。
5. 测试故障开关继续限定在开发库、环境开关和精确 Thread 白名单内。Provider 测试结束后关闭开关，删除合成业务夹具；保留 Provider usage 审计，并停用测试用户及其联系人。

## 2. 实际变更位置

- `office_engine_m3/controllers/llm_thread.py`：Office 非流式 SSE 延迟释放。
- `office_engine_m3/models/mail_message.py`：保留静默 Retriever 中间错误的内部记录与上下文。
- `office_engine_m3/models/llm_thread.py`：失败恢复和导出参数指引；补充根表 `source="root"` 的契约说明。
- `office_engine_m3/services/m4_tv_test_hooks.py`：仅测试配置的受控读取、消费及故障记录。
- `office_engine_m3/tests/test_silent_retrieval.py`、`test_export.py`、`test_m4_tv_test_hooks.py`：消息、事务、导出故障及提示契约测试。
- `docs/implementation/evidence/CC-M4-03/run_handoff_provider_v0.2.py`：真实 Provider 隔离运行器；清理时同时停用合成用户和其联系人。

未修改上游 `odoo-llm` 公共接口、公开 Tool Schema、权限路径或 M2 Candidate / Accept / Finalize 契约；未改写冻结 TDD、Plan 或 CC。

## 3. 关键根因与结论

### Thread 866

历史证据仍不足以唯一定位最终答复消失的边界，结论保留 **UNKNOWN**。当前受控 handoff 故障已能通过 Provider 和持久层验证，但不能用新测试替代历史因果证明。

### Thread 2002 的 Office 参数拒绝

真实 Provider 先后两次将根表 `source` 设为 `res.partner`，Office 两次均以 `operation_executed=false` 拒绝，未创建 Candidate，最终失败答复可重新读取。根因是 Agent 指引说关系明细表使用 collection key，却没有明确根表使用 `root`。修订后的 Thread 2049 首次即传递 `source="root"`，完整数据收集后触发预期 handoff 注入；这是对修复后行为的真实 Provider 复测。

### Thread 1993 查询错误

一次性 `QUERY_FAILED` 后，Agent 重复了同一搜索并在不同业务对象上得到成功零结果，因模型选择不正确而没有完成用户任务。这是 M4-02 的意图/选模问题，不是 Retriever 权限或 ORM 查询错误。它保留为失败证据，不用来声称 CC-M4-03 的 Retriever `INVALID_QUERY` / `FIELD_NOT_FOUND` 纠正分支已通过。

### Thread 1995 的未知 Office 状态

只读 ORM 核对确认 Version 556 为 `verifying`、Session 566 为 `analyzing`，没有输入、输出或最终附件，Current 未推进，且不存在可核对的 Candidate SHA。Office 回执包含 handoff SHA 和 Provider input SHA，但 Hosted Code Interpreter 子结果为 `indeterminate`、`cleanup_state=unknown`，没有远端 response/tool-call/file ID，因此远端执行与清理状态保持 **UNKNOWN**。Thread 中只存在一次 Office Tool Call，没有重发；按契约保留 Thread、版本及 Session，不重发、不清理。

SDK 审计中有 Provider 最终失败说明，但 Odoo `mail.message` 中没有对应 assistant 最终消息。既有运行记录表明当时清理异常回滚了消息事务，因此不将这条 SDK 响应说成用户可见交付，也不作为本轮产品路径的消息丢失证据。完整回执与 SHA 边界见 `evidence/CC-M4-03/thread1995_execution_receipt_evaluation.json`。

## 4. 验收证据索引

- 自动化及 Provider 证据见 `ATR-CC-M4-03.md`。
- 当前 handoff Provider 运行：`evidence/CC-M4-03/handoff_20261121T043051Z_0facf053_{result,evaluation}.json`。
- Provider SDK 请求/响应：`evidence/CC-M4-03/handoff_20261121T043051Z_0facf053_provider_sdk_audit.jsonl`（权限模式 `0600`）。
- 一次性故障记录：`evidence/CC-M4-03/handoff_20261121T043051Z_0facf053_fault_audit.jsonl`（权限模式 `0600`）。
- ORM 清理复核：`evidence/CC-M4-03/handoff_20261121T043051Z_0facf053_cleanup_orm.json`。
- 最终 ORM / 开关 / 残留状态复核：`evidence/CC-M4-03/final_orm_recheck.json`。
- 历史真实 Provider 运行与重试前失败均保留在同目录，未覆盖。
- CC-TEST-006 / 007 补充记录：`evidence/CC-M4-03/CC-TEST-006_007_补充验收记录_20261121.md`；三条独立真实 Provider Retriever 错误恢复 Thread 的原始请求/响应及 Oracle 结果见 `retriever_20261121T074630Z_*`、`retriever_20261121T081335Z_*`，Thread 1995 ORM/SHA 核对见 `thread1995_readonly_audit.json` 与 `thread1995_execution_receipt_evaluation.json`。
- 最终只读状态复核：`evidence/CC-M4-03/final_orm_recheck_20261121.json` 确认测试 Thread 与合成联系人已清理、测试用户已停用、故障注入和 Provider 审计临时开关已关闭，且 Thread 1995 仍未重发或推进版本。
- 模块通过 Odoo CLI 在现有开发库升级并运行测试；独立 ORM 会话确认模块为 `installed`、版本 `18.0.7.0.7`，审计 allowlist 与故障参数关闭。没有启动持久化 8091 服务。

## 5. 最终验收状态

- CC-TEST-006：**PASS**。`INVALID_QUERY` 和 `FIELD_NOT_FOUND` 均由真实 Retriever 校验器返回；Agent 分别在一条纠正重试后按原业务约束完成查询并通过 Oracle。重复 `INVALID_QUERY` 场景在两次错误回执后停止，没有伪报零结果或成功，未超过两次纠正重试。
- CC-TEST-007：**PASS（安全停止行为）**。现有确定性回归证明同一未知 Provider 操作只发起一次；Thread 1995 也只有一次 Office 调用。远端 Hosted Code Interpreter 状态、产物和清理结果仍 **UNKNOWN**，并未通过重发或清理消除。
- CC-TEST-005：非流式生产路径已测；流式仅验证可观察边界，generator 续接和未覆盖流式分支保持未验证。
- Thread 866 历史根因保持 **UNKNOWN**；当前受控消息故障路径另有既有 PASS 证据，不替代历史因果结论。
- 本轮重新运行 `TestSilentRetrieval` 17 项与 `test_indeterminate_provider_attempt_is_not_silently_replayed` 1 项，均为 `0 failed, 0 error(s)`。

项目负责人已于 2026-11-21 批准关闭 CC-M4-03。IHR、ATR、FR 和证据按批准范围提交并推送；Thread 1995 远端执行状态与 Thread 866 历史根因仍保留 UNKNOWN。
