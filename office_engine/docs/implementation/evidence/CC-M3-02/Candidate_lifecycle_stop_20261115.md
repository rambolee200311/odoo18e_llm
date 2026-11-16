# CC-M3-02 停止记录：新建导出的 Candidate 生命周期

**状态：BLOCKED — 需要 TDD / CC 影响评审**

**日期：2026-11-15**
**基线：M3 TDD v0.4 / Implementation Plan v0.3 / CC-M3-02 v0.2**

## 冻结要求

新建工作簿导出必须成为待用户审阅的 Candidate，用户 Accept 后才能成为 Current；同时不得使用 M2 fileless-create 的 direct-V1 例外，也不得修改 `office_engine_m2` 的 Candidate / Accept / Reject 状态机。依据 CC §3.1 #5–8、§3.2、§4.2、CC-PRESERVE-003 与 `T-M3-VERSION-001`。

## 源码证据

1. [M2 `register_initial_candidate()`](../../../../office_engine_m2/services/workbook_version_service.py#L636) 在登记 initial Candidate 时读取 `session.source_attachment_id` 及其 SHA；没有源附件时不能用此 API 建 Candidate。
2. [M2 fileless create 注册](../../../../office_engine_m2/services/workbook_version_service.py#L1344) 创建的是 `state="verifying"`、无输入附件的 fileless initial version。[现有 `execute_fileless_creation()`](../../../../office_engine_m2/services/edit_orchestrator.py#L480) 验证后调用 `publish_fileless_initial_version()` 并立即推进 V1 / Current（同文件约第 596 行）。这与 M3 要求的 Candidate → 用户 Accept 冲突。
3. [M2 `_revalidate_stored_receipt()`](../../../../office_engine_m2/services/workbook_version_service.py#L1528) 对所有可接受 Candidate 无条件调用 `_read_attachment(candidate.input_attachment_id)`；而 [`_read_attachment()`](../../../../office_engine_m2/services/workbook_version_service.py#L324) 对空附件直接拒绝。因此 fileless Candidate 即使持有输出文件与验证回执，也无法通过现有 `accept_verified_candidate()` 的复核。
4. 下游绕过 `accept_verified_candidate()`、自行推进 Session / Current，或伪造 source attachment / parent version，都会改变或绕开 M2 用户决策与版本门禁，违反 CC §4.2 和 §6。

## 影响

- `workbook_source="current"` 有已接受 parent version 和真实输入附件，理论上可复用 `register_candidate()`；这不解决 `workbook_source="new"` 的契约。
- CC-M3-02 同时要求支持新建和修改工作簿。只实现 `current` 分支会留下强制范围缺口，不能关闭本 CC。
- 尚未修改产品代码；未访问数据库；未调用 Provider；CC-M3-02 ATR 的实施测试全部保持 NOT RUN。

## 决策选项

推荐负责人评审并版本化设计，确定允许哪一种方案：

1. 修订 M2 version service，添加受同一用户 / Thread / Session / SHA / Candidate Accept 约束的 source-less Candidate 支持；这超出当前 CC 禁改 M2 的边界，需更新 TDD、Plan 与 CC 后另行授权。
2. 保持 M2 不变，修订 M3 新建导出的业务生命周期要求；若采用 direct-V1 或其他生命周期，必须先重新审议 SRS / TDD，不能由实现自行决定。
3. 要求新建任务提供真实源工作簿 / 模板，使其走已有 initial Candidate 路径；这会改变冻结的工具契约和用户任务范围，也须先评审。

取得明确决策、更新并重新基线化受影响文档后，方可恢复受影响实现。当前 Coding Authorization 不包含改变冻结设计、改 M2 生命周期或绕过用户确认的授权。

## 状态更新 — 2026-11-16

以上内容记录 2026-11-15 当时的静态检查与停止决定，作为历史记录保留。负责人随后明确授权继续实施并允许必要的 M2 兼容性修改，授权记录为 `CC-M3-02-003`。实施采用 M2 fileless initial 的文件完整性校验，但不调用 direct-V1 发布路径；source-less M3 Candidate 仍须用户 Accept，Reject 不推进 Current，Finalize 沿用 M2 门禁。具体实现边界见 [`TDD_office_engine_m3_v0.4_Implementation_Compatibility_Addendum_20261116.md`](../../../design/TDD_office_engine_m3_v0.4_Implementation_Compatibility_Addendum_20261116.md)。

真实 Provider 最终输出尚未通过验收，因此此更新只关闭原先“技术接口无通路”的阻断，不表示 CC-M3-02 已完成。Provider / ATR 当前状态以 [`ATR-CC-M3-02-complete-data-office.md`](./ATR-CC-M3-02-complete-data-office.md) 为准。
