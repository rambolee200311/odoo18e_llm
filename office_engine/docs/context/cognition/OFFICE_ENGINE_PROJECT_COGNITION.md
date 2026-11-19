# Office Engine 项目认知

**状态：** 项目认知记录；按用户提供的 Office Agent Standard 整理，未声明为冻结技术设计。
**记录日期：** 2026-11-17

## 1. 项目目标

Office Engine 基于 `odoo-llm` 开发。当前核心目标是：用户用自然语言表达业务需求，Agent 从 Odoo 业务记录中发现并取得数据，再使用 Excel 能力生成或修改工作簿，向用户交付可验证的正确结果。

此项目认知记录描述项目目标、能力标准和责任边界；具体业务范围与技术实现仍以相应冻结的需求、TDD 和实施契约为准。

## 2. Office Agent Standard

以下标准由项目负责人提供，是 Office Engine 的项目级能力目标。

### STD-01｜M3：可靠的数据发现与交付

M3 必须提供通用、可靠的数据发现、字段理解、关系查询、完整性验证和数据交付能力。

### STD-02｜M4：自主 Agent 能力

M4 必须建立通用的意图理解、任务规划、工具协同、执行验证与失败恢复能力。

### STD-03｜最终用户验收标准

一个普通业务员，只需用自然语言提出任务，无需了解 Odoo 模型、字段、Domain 或 Excel 技术细节，Agent 就能自主完成任务，并交付可验证的正确结果。

## 3. 能力与责任边界

- Agent 理解业务意图，发现模型、字段和关系，规划检索范围与输出，并协同现有 Retriever 和 Office 工具。
- Retriever / Collector 按已确定的通用查询计划读取当前用户有权访问的数据，执行分页、关系收集和客观完整性核对；它不替 Agent 解释业务需求或设计报表。
- Excel 内容继续由 LLM 与 Hosted Code Interpreter 通过现有 Office Route B 生成或修改；不以本地 Writer 或本地业务报表引擎替代。
- Odoo 权限、记录规则、文件完整性、Candidate、Current、版本、SHA 及用户确认由现有服务端机制执行。元数据发现不读取业务记录，也不授予业务数据访问权。
- 工具调用、Collector 成功或文件存在仅是执行证据，不单独证明业务任务已完成。

## 4. 最终结果与验收原则

最终 E2E 是否通过，以用户业务任务是否完成、结果是否正确为准。至少核对用户条件、记录身份与数量、字段值、关联关系、所需公式/聚合、文件可读性以及交付状态。即使工具均成功返回或 XLSX 能打开，只要业务结果缺失、错误、不完整或不符合请求，任务仍为失败。

“普通业务员无需了解技术细节”意味着 Agent 不应要求用户提供模型名、技术字段名、Domain 或 Excel 坐标来替代自身规划；业务含义确有歧义时，Agent 应提出必要澄清。

人工 Accept 是最终真实用户验收的一部分：用户在 Odoo UI 审阅实际 Candidate 后明确接受，系统再按既有生命周期 Finalize。组件 TV、隔离测试和候选 Spike 不要求人工 Accept；这些验证应核对 Candidate/Current 状态，并复用已通过的自动化生命周期证据。

Agent 任务规划、结果自检和失败诊断/恢复是彼此独立的验收能力。最终文件正确不能替代规划与自检证据；错误恢复安全也不能替代业务结果正确性。

## 5. 权威文档与证据边界

- M3 技术基线：[Office Engine M3 TDD v0.4](../../design/TDD_office_engine_m3_v0.4.md) 及其实施兼容性 Addendum。
- 现有 M4 问题证据：[M4 前置 TV 执行报告](../../verification/M4_TV_Execution_Report.md)、[缺陷登记](../../verification/M4_TV_Defect_Register.md) 和 [RCA 汇总](../../verification/m4_rca/M4_RCA_Summary.md)。
- Agent 操作决策边界：[Office AI Agent 架构与决策边界](../../AGENTS.md)；项目级一般操作原则：[Agent 操作原则](../principle/AGENT_OPERATION_PRINCIPLES.md)。
- 本认知文件不改变已关闭 RCA 的状态、不改写 TV-01～20 的 FAIL，也不冻结新的架构、接口或实施方案。验证结论必须引用真实执行证据；未执行的 TV 不得标为 PASS。

## 6. 变更记录

| 日期 | 变更 |
|---|---|
| 2026-11-17 | 首次记录用户提供的 STD-01～03 及 Office Engine 的项目目标、能力边界和最终验收原则。 |
