# CC-M4-03 最终实施报告（FR）

## 结论

CC-M4-03 v0.2 的消息可靠性与静默边界实现、CC-TEST-006/007 强制验收及受影响 M2/M3 回归均已有实际结果和证据。真实 Provider 在受控 Retriever `INVALID_QUERY` 与 `FIELD_NOT_FOUND` 后分别完成纠正并通过独立 Oracle；重复错误时安全停止。未知 Hosted Code Interpreter 状态下，现有执行层阻止同一操作被再次提交。

**状态：CLOSED — 项目负责人于 2026-11-21 批准关闭。** Thread 1995 远端 Hosted Code Interpreter 的执行/清理状态仍为 UNKNOWN；Thread 866 的历史消息丢失根因也仍 UNKNOWN。前者没有重发或清理，后者没有用新测试冒充历史根因证明。

逐项状态、测试证据及精确限制见 [ATR-CC-M4-03.md](ATR-CC-M4-03.md)，实施细节见 [IHR-CC-M4-03.md](IHR-CC-M4-03.md)。

## 本轮变更

- 强化非流式 Office SSE 的事务后释放及失败缓冲行为。
- 保留内部 Retriever 错误及 Agent 上下文，同时避免中间错误刷屏。
- 补足按工具实际错误、回执和状态进行有界恢复的 Agent 指引。
- 明确 Office 导出根表使用 `source="root"`；在操作被拒绝且未执行时禁止原样重发，并将修正规则限制为契约能唯一确定的情况。
- 补充事务、最终消息持久化/重读、Silent Retrieval、handoff 故障及提示契约回归。
- 补齐 CC-TEST-006 的真实 Provider 错误纠正/停止证据和 CC-TEST-007 的 Thread 1995 ORM 回执、附件及 SHA 核对；本轮未发现需改动产品代码的缺陷。

不修改 `odoo-llm` 公共接口、公开 Tool Schema、业务数据权限、M2 文件生命周期或冻结设计。没有新增工具、业务模型或通用幂等框架。

## 最终验证摘要

- 新增提示契约定向测试：1 项 PASS。初次仅有旧文本断言失败，更新断言后复跑通过。
- 最新 `office_engine_m3` 全模块回归：67 项，0 failed / 0 error。
- M2 Candidate/Finalize/Edit 关键路径：4 项，0 failed / 0 error；未运行 M2 全量套件。
- 最新真实 Provider：7 请求/7 响应；Oracle 验证两条合成联系人及其姓名、邮箱；handoff 故障注入后没有 Candidate，失败说明持久化并重新读取可见。
- CC-TEST-006：三条独立真实 Provider Thread（2119、2122、2123），共 21 / 21 请求/响应；两种 Retriever 错误纠正的最终身份、条件、人数和姓名/邮箱均匹配 Oracle；重复错误在初始错误加 1 次重试后停止，未误报零结果。首轮标签失真 FAIL、两次 Provider timeout/connection error 均保留，后续有效 Thread 补测通过。
- CC-TEST-007：`TestM3Export.test_indeterminate_provider_attempt_is_not_silently_replayed` 1/1 PASS，`TestSilentRetrieval` 17/17 PASS。Thread 1995 当前只存在一次 Office Tool Call；Version 556 为 `verifying`，Session 566 为 `analyzing`，无输出/最终附件及 Candidate SHA，Current 未推进。Provider 最终失败说明未持久化为 assistant 消息（先前清理时回滚），所以不宣称它对用户可见；Hosted CI 远端产物和清理仍为 UNKNOWN。
- Thread 2049 及其业务夹具已清理；合成测试用户和联系人停用；临时故障参数关闭。Provider usage 记录保留。Thread 1995/version 556/session 566 因执行状态不确定而保留。
- 未做真实 UI HVR（本 CC 中间阶段不要求）；未提交、未推送 Git。

## 评审建议

冻结 CC 要求的强制验收均已提供实际状态和证据，项目负责人已批准关闭。Thread 1995 的远端未知状态及缺失的 Thread assistant 最终消息如实保留，不作补发或清理；Thread 866 历史根因继续保持 UNKNOWN。逐项证据见 [ATR-CC-M4-03.md](ATR-CC-M4-03.md)、[IHR-CC-M4-03.md](IHR-CC-M4-03.md) 和 [`CC-TEST-006/007 补充验收记录`](evidence/CC-M4-03/CC-TEST-006_007_补充验收记录_20261121.md)。
