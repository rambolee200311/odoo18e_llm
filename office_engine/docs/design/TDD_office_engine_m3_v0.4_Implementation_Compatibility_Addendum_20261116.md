# Office Engine M3 TDD v0.4 — Implementation Compatibility Addendum

**日期：** 2026-11-16  
**状态：** Owner-authorized implementation addendum；不替换或重新冻结 [TDD v0.4](./TDD_office_engine_m3_v0.4.md)、[Implementation Plan v0.3](../implementation/IMPLEMENTATION_PLAN_office_engine_m3_v0.3.md) 或 [CC-M3-02 v0.2](../implementation/CC-M3-02_完整数据至Office_v0.2.md)。  
**范围：** 记录新建工作簿的 Route B 输入载体与 M2 Candidate → Accept → Finalize 生命周期兼容性，以及后续经真实文件核验后对空白辅助列位置的有界实现补充；不替换冻结的 TDD、Plan 或 CC。

## 1. 决策

新建导出继续使用单一 M2 `office` Tool 的 Hosted Code Interpreter Route B 和现有 Candidate 生命周期。采用 M2 现有 fileless initial version 注册与验证服务，但**不调用**其 legacy direct-V1 发布路径。M3 先持久化输出并登记为可审阅 Candidate；只有用户明确 Accept 后才推进 Current；Finalize 仍交付同一已接受版本及同一 SHA。

Route B 要求有输入 XLSX 时，M3 随请求发送最小空白 XLSX carrier。它仅是 Hosted Code Interpreter 的技术输入附件，不是业务模板或业务内容；不附加到 Odoo Thread、不存为 M2 Candidate 输入附件、不用于业务字段或内容生成。LLM + Hosted Code Interpreter 仍负责生成最终 XLSX。M3 receipt 记录实际 Provider 输入 SHA，以便追溯。

`workbook_source="current"` 继续使用现有 Accepted Current 的附件和 SHA，创建 M2 edit Candidate；Accept 前 Current 不变。

## 2. 最小兼容性扩展

实现只在下游 `office_engine_m2` 生命周期服务增加 M3 所需的兼容点；不修改上游 `odoo-llm`，不改变 Accept / Reject / Finalize 授权语义，也不新增 Candidate 状态或独立生命周期：

- 允许已验证输出从 `verifying` 进入既有 `candidate_received`，并由既有 fileless initial 文件完整性验证器处理。
- 允许现有验证回执在 Accept 时重新核验这个 source-less initial Candidate；继续核对 Thread、Session、用户决策、输出附件和 SHA。
- 将 M3 export tool result 纳入现有 Candidate review 查找；M2 原有 `action="create"` 继续执行原来的 fileless direct-V1 行为。
- 为 current-source M3 export 提供已有 Accepted Current 上的 edit attempt 注册、输入 SHA 绑定、幂等身份和输出附件存储；仍通过 M2 Candidate review 与版本服务处理 Accept / Reject / Finalize。
- M3 保存 TDD 定义的紧凑 receipt v3：query 与权限范围摘要、source / relation / handoff 计数及 digest、采集窗口和同一事务 read-view 语义、freshness 标志、文件投影核验及 Candidate 输出 SHA。完整数据集和原始 domain 不写入版本记录。

此兼容性扩展偏离 CC-M3-02 v0.2 §4.1 原定的 M2 文件面限制。负责人于 2026-11-16 明确授权解决该兼容性问题；记录见 [`AUTHORIZATION_RECORDS.md`](../implementation/AUTHORIZATION_RECORDS.md) 的 `CC-M3-02-003`。冻结文件保留为历史基线，此 addendum 只覆盖上述窄范围。

Implementation Plan v0.3 和 CC-M3-02 v0.2 的冻结文本继续作为历史基线；本 owner-authorized addendum 对“禁止 M2 文件面修改”作单一、窄范围实施例外，不改变其他 CC 范围或验收门槛。ATR / IHR 记录实际偏差及未通过项；CC 不因本例外自动关闭。

## 3. 保留的边界

- Collector 使用当前用户 ORM；不使用 `sudo()`，不直连 SQL 查询业务记录。
- 本地程序不生成或修补 Excel 内容；`openpyxl` 只读检查 Hosted CI 输出。
- Accept 仍要求用户显式决策；Reject 不推进 Current / Last Valid；Finalize 只交付 Accepted Current 同一文件。
- 不完整、无法验证、Provider 超时或资源超限时失败关闭，不将其报告为完整导出。
- 仅使用现有开发数据库 `odoo18e_llm`；测试数据使用合成数据并在回滚事务中执行。

## 4. 初次验证记录（历史）

初次自动化 fixture 已验证 148 条记录按 100 + 48 收集、251 条记录跨三页收集、count drift / 重复 identity 拒绝、root / relation / handoff-byte 限额 fail-closed、不确定 Provider 结果不自动重放、输出投影核验、新建和 current-source Candidate 生命周期，以及新建 Candidate Reject。初次 freshness 并发 insert / update / delete 验收尚未完成；初次真实 Provider XLSX 因 root 表多出 `__office_parent_id` 被旧核验器拒绝，随后两次请求在无响应 ID 情况下超时。初次状态详见 IHR-005 和旧版 ATR-RUN-002；下节记录后续补验结果，不删除实施历史。

## 5. 输出核验契约补充与补验结论

### 5.1 通用 projection 核验规则

真实诊断 XLSX 中 `__office_parent_id` 在 148 行均为空，原任务没有关系集合。该辅助列不含业务数据；要求它必须缺席或紧邻 identity 列会造成无必要的布局拒绝。因此，实施核验器采用以下一般规则：

- 计划可见列必须各出现一次，并按已解析的输出计划顺序排列；可有任意位置的额外空白辅助列。
- 必需的 `__office_record_id` 必须唯一；关系表另须唯一的 `__office_parent_id`。root 表可选有一列 `__office_parent_id`，但每行必须为空。
- 未规划的额外列仅在所有数据行均为空时忽略；未知列只要出现非空值即拒绝。
- 数据行数量、每条 identity 恰好一次、逐行的计划字段值、关系 parent-child pair、父子身份映射继续精确核验。缺行、重复、缺失 / 错误字段或错误关联不因布局宽容而放行。
- 关系字段类型及 expected 值来自服务端已解析的 Collector plan，不从 Hosted CI 返回的 handoff 数据读取验证规则。

该实现补充经 owner 当前验收指令授权，记录于本次 CC-M3-02 ATR / IHR；它不更改 frozen TDD / CC 文本、不授权本地 Excel writer、不放宽数据完整性要求。

### 5.2 结果摘要

- 旧 148 行 XLSX 的结构检查：148/148 唯一连续 IDs（3272–3419），Name / Email 各 148 个非空且唯一，root parent helper 148 个全空，无公式，无关系集合。因旧合成事务已回滚，旧文件的全部中间字段不能再对回旧 source；单独证据 [`legacy-148-output-inspection.json`](../implementation/evidence/CC-M3-02/legacy-148-output-inspection.json) 明确此边界。
- 后续真实 Provider 148 行测试在新合成事务中逐项比较 IDs、Name、Email，全部相同；真实 Provider 251 行三页场景也逐项相同。148 行 Candidate 经显式用户 Accept 后推进 Current，Finalize 交付同 SHA，验证等级保持 `PARTIALLY_VERIFIED`。详见 [`ATR-CC-M3-02-complete-data-office.md`](../implementation/evidence/CC-M3-02/ATR-CC-M3-02-complete-data-office.md) 的 ATR-RUN-003。
- 故障注入发现并修复关系 verifier 中的字段类型来源 `KeyError`，以及 Candidate result 对 `source.kind` / `handoff.provider_input_sha256` 取错层级的问题。M3 export 当前 20/20 通过；M2 / Retriever 已通过的定向回归保持适用。
- Freshness 两 cursor ORM 验收在并发 insert / update / delete 发生后保留起始 3 条的同一 `REPEATABLE READ` read view，并已通过 ORM 清理测试数据。timeout 配置保持 120 秒：两次旧请求在 37.855s / 48.326s、无 response ID 时失败，不能归因为 120 秒上限；后续 Provider 响应在 24.660s / 28.000s 成功。Adapter 输入 / 输出上限和 timeout 失败关闭离线断言 3 项通过。

本 addendum 记录兼容设计及有界实现补充；它不代替 CC 关闭批准。CC-M3-02 关闭状态以负责人评审为准；真实 Agent UI HVR 仍归 CC-M3-03，未执行。
