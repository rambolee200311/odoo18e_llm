<!--
模板来源：office_engine/docs/skill/odoo-project-workflow/references/templates/Coding/Coding_Contract模板.md
模板版本/状态：v1.0.0 Frozen
本文件状态：Draft — 等待项目负责人评审；未冻结、未授权实施。
-->

# CC-M4-04 — Excel 结果验证 v0.1

## 0. 文档治理

| 字段 | 内容 |
|---|---|
| Intent ID | CC-M4-04 |
| 模块 | `office_engine_m3` / M2 Route B 验证路径 |
| 工作类型 | 明细、公式、聚合及文件结果的任务适配验证 |
| 状态 | **Draft — 等待评审；未冻结、未授权实施** |
| 上游 TDD | `TDD_office_engine_m4_v0.2.md`，FROZEN WITH OPEN ITEMS |
| Implementation Plan | `IMPLEMENTATION_PLAN_office_engine_m4_v0.1.md`，FROZEN |
| 前置 CC | CC-M4-01、CC-M4-02、CC-M4-03；关闭状态按各自 FR 记录 |
| 依据 | TD-M4-004、TD-M4-007；`SPK-M4-AGGREGATION-01_Report.md`；E02 / E06 原始验证记录 |
| 数据库边界 | 只使用现有开发库 `odoo18e_llm`；不新建数据库、不访问生产环境 |
| 验收类型 | 自动化和组件集成测试；不做 UI HVR，不替代 CC-M4-05 最终用户验收 |
| Provider / Hosted CI | 若实施验证需要真实服务调用，须在 CC 实施授权中明确；只允许合成数据和隐藏 Oracle |

本文件仅定义 CC-M4-04 Draft。冻结前不运行测试、不修改代码、不调用 Provider、不创建数据库、不开始实施。

## 1. 目标与问题

E02 的失败表明：现有 `record_projection` 验证会逐行核对源记录身份和值，而 `grouped_aggregate` / `semantic_transform` 当前主要检查 XLSX 可读性；公式汇总工作簿因此无法获得与其任务相符的独立验证。公式缓存缺失时，仅读取公式文本不能证明计算值正确。

本 CC 的目标是为 M4 规定的三种输出形态建立任务适配验证，并证明验证器与 Agent 能正确处理验证差异：

1. 记录投影继续精确核对源身份、行数、字段值和父子关系。
2. 明细加汇总时，分别验证明细投影与汇总结果；汇总行不伪装成源记录。
3. 纯聚合时，由 Collector receipt / handoff 证明输入数据完整，以独立 Oracle 核对输出分组及计算值。
4. 对公式缓存缺失、过期、公式不受支持或重算失败，准确报告验证边界；不以“文件可读”代替“结果正确”。
5. 分别验证验证器检测差异、Agent 实际收到并理解回执、Agent 作出正确后续决定；Oracle 结果不进入 Agent 上下文。

最终验收依据是用户任务的业务结果及其独立证据。工具调用成功、文件存在或 Agent 自述都不单独构成 PASS。

## 2. 基线证据与边界

| 事实 | 当前证据 / 约束 |
|---|---|
| M3 已有精确记录投影验证 | `office_engine_m3/services/export_verification.py` 对计划列、唯一记录 ID、关系父 ID、行数和值执行核对；公式不作为源字段值。CC 只扩展任务适配分支，不得削弱这条边界。 |
| 聚合验证尚不完整 | 当前非 `record_projection` 路径仅能确认工作簿可读和存在工作表，返回身份验证未执行；须在实施前以当时源码再次确认。 |
| E02 公式缓存缺失 | Spike 检查的 3 个 Provider XLSX 共 12 个公式格均无缓存值；原始版本 468–470 均失败关闭，没有 Candidate Accept / Finalize。 |
| 临时副本重算已有有限证据 | 对 E02 原始附件副本使用 LibreOffice headless 重算，COUNTIF / SUM 测试值与 ORM 独立 Oracle 一致；原件及 SHA 未改变。此结果不证明任意 Excel 公式兼容。 |
| 纯聚合尚未完成真实 Provider 验证 | Spike 没有生成纯聚合 Provider 文件；源集 receipt + handoff + 独立 Oracle 是设计边界，不应描述成已通过的产品能力。 |
| Oracle 必须独立且隐藏 | 使用普通测试用户执行受测查询；测试人员单独读取 ORM / 文件计算期望值。不得将正确答案、技术字段答案或 Oracle 标签传给 Agent。 |

实现人员须核对当前 `office` Schema、Collector receipt、验证器输入 / 输出以及现有版本状态后确定接口。上述现状是 Draft 起草依据，不预先宣称其为 CC 实施时的最终源码基线。

## 3. 范围

### 3.1 范围内

- 在现有 M3 输出验证路径中扩展记录投影、明细加汇总、纯聚合及可验证语义转换的结果核验。
- 明确输出意图到可观察验证输入的最小契约：优先复用当前 `office` 参数、Collector receipt 和版本回执；如其不足以描述分组键 / 指标，提出并实施向后兼容的最小扩展，但不得增加公开 Tool 或独立模型。
- 规定受支持的聚合操作、公式读取 / 重算策略及不支持行为，并用测试证据限定支持范围。
- 公式缓存校验；必要时在隔离临时副本中重算，并核对原始 Provider 输出、Candidate 附件和 SHA 未被改写。
- 对验证差异进行受控注入，测试验证器状态、Agent 可观察回执、后续决策及 Candidate / Current 状态。
- 保留现有 M2 Route B / Hosted Code Interpreter 内容生成路径及 Candidate 生命周期。
- 运行相关 M2 / M3 自动化与组件集成回归，交付 IHR、ATR、Final Report。

### 3.2 范围外

- 本地 Excel Writer、报表生成器、复杂业务计算引擎或用于替代 Hosted Code Interpreter 的公式生成 / 修补服务。
- 针对特定 Odoo 模型、字段、工作簿名称、列布局、单元格坐标、业务词或固定模板的规则。
- 新增公开 Tool、独立验证 Tool、数据库模型、独立 Candidate / Partial Candidate 生命周期或新的用户审批机制。
- 修改冻结 TDD、M2 / M3 用户确认语义、权限规则或版本/SHA 门禁。
- 真实 UI HVR；最终业务员验收由 CC-M4-05 完成。

## 4. 关键执行契约

### 4.1 明细投影

- 每个被要求输出的源记录必须唯一且完整；缺行、重复 ID、字段值错误、错联父子关系或 handoff 身份不符均验证失败。
- 计划外辅助列不得替代可见业务字段或源身份检查；对辅助列的处理不得重新引入依赖固定列布局的规则。
- 增加汇总表不得改变明细表的原有严格核验。

### 4.2 明细加汇总与纯聚合

- 输出角色与分组 / 指标含义必须来自 Agent 实际提交且可审计的任务计划或现有工具请求信息，不从固定工作表名、坐标或隐藏思维链猜测。
- 明细表执行 §4.1 的逐记录验证；汇总行按用户目标中可客观表达的分组键及聚合指标验证，不要求汇总行携带 Odoo 源 ID。
- 纯聚合工作簿可不含逐行 ID；输入完整性依赖当前用户 Collector receipt / handoff 的数量、身份或摘要和关系完整性证据，输出值再与独立 Oracle 比较。
- 如果当前工具契约不能明确表达被验证的分组键 / 指标，实施阶段须先记录最小通用契约及旧调用兼容证据；不得用固定模板、仅解析任意业务描述或 Agent 自评冒充 Oracle。
- 对无法独立计算或确认语义的部分，验证结果须明确为未充分验证或失败；不得报告完全验证成功。

### 4.3 公式、缓存与隔离重算

- 公式字符串本身不是计算正确的证据；缓存值须能与独立 Oracle 对照，且不得仅因存在缓存就假定其未过期。
- CC 实施验收至少复现 Spike 覆盖的 COUNTIF / SUM 类型，并确认计划支持的公式子集、缓存策略和计算器版本。不得由该小样本推断任意公式支持。
- 若缓存缺失或需重新计算，只能在受控临时副本上使用经测试的计算器；以重算副本的结果核对 Oracle，不修改替换 Provider 原件、Candidate 附件或 SHA。
- 宏、外部链接、易变函数、未知函数、超资源边界、计算器错误或语义差异均须 fail-closed / 标为未充分验证。不得访问外部链接，不执行宏。
- 资源上限、超时、临时文件清理和文件权限须有自动化证据；临时副本不得被当作新 Candidate。

### 4.4 验证回执与 Agent 自检

将以下三项分开判定，不得合并成一个“自检通过”：

1. **验证器发现差异：** 隐藏 Oracle 与输出存在预设差异时，验证器给出可复核且不泄漏 Oracle 答案的失败 / 不充分验证回执。
2. **Agent 收到并理解回执：** 记录工具结果 / Provider 后续请求，证明实际错误状态及差异类别进入 Agent 上下文。
3. **Agent 后续决策正确：** Agent 不声称结果完全正确，不请求 Accept / Finalize；仅在保留用户条件且重试安全时纠正，否则准确停止并向用户说明。

若测试替身注入受控回执，须证明 Agent 实际接收该回执，并将结论限定为隔离组件能力；不得让测试程序替 Agent 判断，也不得把 Oracle 正确值注入 Agent。

## 5. 变更与保护契约

| ID | 要求 |
|---|---|
| CC-CHANGE-001 | 保持现有 `record_projection` 精确身份、值及关系验证；为不同输出角色提供独立任务适配校验。 |
| CC-CHANGE-002 | 建立公式缓存 / 隔离副本重算边界与明确的受支持范围；原始 Candidate 内容及 SHA 不变。 |
| CC-CHANGE-003 | 让验证器回执可由 Agent 实际读取并据此作安全决定；不新增独立 Tool 或数据库模型。 |
| CC-PRESERVE-001 | Collector、权限、分页、关系及 handoff 完整性契约不放宽；ACL / Record Rules 不绕过。 |
| CC-PRESERVE-002 | M2 Route B + Hosted Code Interpreter 继续负责 Excel 内容生成；普通 M2 空白工作簿创建保持可用。 |
| CC-PRESERVE-003 | Candidate、Accept、Reject、Finalize、Current、版本 lineage、附件和 SHA 使用既有 M2 / M3 生命周期；确认前 Current 不变。 |
| CC-PRESERVE-004 | 失败 / 未充分验证的输出不得被标记为完全验证或完整业务成功；不得创建新生命周期状态来绕开现有门禁。 |
| CC-PRESERVE-005 | `odoo_record_retriever`、`office` 保持为既有公开工具；若需要新增可选 Schema 属性，必须维持旧调用兼容并在本 CC 内证明 Provider Schema、Execute 和验证器一致。 |

## 6. 验收测试

所有自动测试数据均为合成数据并由独立 Oracle 预先定义。测试人员可使用 ORM 读取 Oracle；Agent 不接收模型答案、字段答案、预期身份和值。按 Implementation Plan，本 CC 不执行真实 UI HVR。

| ID | 验证目标 / 方法 | PASS 条件 | 失败边界 |
|---|---|---|---|
| CC-TEST-001 明细回归 | 记录投影测试集覆盖正常、多页、缺行、重复身份、错误字段值及父子错联。 | 完整源投影逐记录匹配；错误身份 / 值 / 关系全部失败关闭；历史 M3 投影行为无回归。 | 任何缺失、重复、错值、错联被放行即 FAIL。 |
| CC-TEST-002 明细 + 聚合 | 使用合成关系数据输出明细页和汇总页，至少覆盖 COUNTIF / SUM 公式与独立分组结果。 | 明细严格匹配；汇总键及值与 Oracle 一致；汇总行不因缺少源 ID 被误判，额外辅助列不掩盖数据错误。 | 仅工作簿可读、公式存在或 Agent 自述正确均不通过。 |
| CC-TEST-003 纯聚合 | 使用 Collector 完整收集回执和无明细行的汇总输出；独立核对输入身份摘要、分组键和值。 | 源数据完整性和任务所需的聚合值均有独立证据；输出格式不要求虚构逐行 ID。 | 缺失源 receipt / handoff 或 Oracle 不匹配时不得完全验证。 |
| CC-TEST-004 公式缓存 / 副本重算 | 覆盖缓存有效、缓存缺失、缓存与 Oracle 不符、可支持与不支持公式、重算失败及计算超限。 | 受支持公式得到 Oracle 一致结果；重算仅在临时副本执行，原 Candidate 字节和 SHA 不变；不支持情形明确 fail-closed / 未充分验证。 | 把缺缓存公式文本当正确值、改写 Candidate 或静默忽略重算失败即 FAIL。 |
| CC-TEST-005 独立验证与差异注入 | 分别注入明细身份、关联、字段值和聚合值错误；核对隐藏 Oracle 与验证回执。 | 每个差异均由验证器检测，类别及状态与实际差异一致；未注入错误时有效样例通过。 | 只测验证器自生成输入而不与独立 Oracle 比较不通过。 |
| CC-TEST-006 Agent 自检 | 向 Agent 暴露受控验证失败回执，记录实际上下文 / Provider 请求 / 后续动作；按需在实施授权中使用真实 Provider。 | 验证器检测、Agent 理解、Agent 决策分别有证据；Agent 不错误宣称成功、不请求确认错误候选；安全恢复时保留原条件，否则停止。 | 隐藏 Oracle 进入 Agent、测试程序代替 Agent 决策、只有模拟输出而无接收证据均不通过。 |
| CC-TEST-007 失败关闭与生命周期 | 文件损坏、公式不支持、Oracle 差异、SHA 变化、验证器异常及资源超限；检查 Candidate / Current。 | 不完整或未充分验证的结果不被冒充为已完全验证；Current 不在 Accept 前推进；状态按既有 M2 / M3 契约处理。 | 新建独立 Partial Candidate 生命周期、验证失败仍可完全交付或 SHA 不一致即 FAIL。 |
| CC-TEST-008 M2 / M3 兼容回归 | 运行直接受影响的 M2 Route B / blank create / 版本 SHA、M3 export / projection / Candidate 生命周期测试。 | 有精确测试命令与证据；无新增失败；未运行范围标为 NOT RUN，不扩大既有回归结论。 | 不得以 CC-M4-04 局部通过声称 M2/M3 全量通过。 |

## 7. 验证环境与证据

- 数据库：仅现有开发库 `odoo18e_llm`；不创建数据库或访问生产环境。
- 权限：普通测试用户执行真实 ORM 读取；Fixture 的准备与清理方式须符合项目测试约定，不以管理员结果替代被测用户结果。
- Provider：若实施授权包含 Provider 验证，使用明确批准的模型和现有 `office` / Retriever；只发送合成数据，不发送 Oracle 标签、真实业务记录、凭据或非必要 Thread 历史。
- Oracle：在 Agent 之外保存合成记录身份、关系、输入聚合期望值和预设差异；证据文件按项目要求限制访问权限。
- 每个测试保留命令、数据库 / 模块版本、代码基线、测试输出、Provider 请求与工具回执（若实际运行）、原始和临时副本 SHA、Candidate / Current 状态及清理结果。
- 临时重算完成后验证临时文件删除；不得改动 E02 历史附件或历史 TV / Spike 报告。

## 8. 交付物与关闭评审

实施阶段需交付：

1. 当前 verifier / Office 参数 / Collector receipt 的源码差异分析和实施记录。
2. 受支持输出类型、聚合项、公式 / 缓存 / 重算及不支持语义的明确契约；必要时的向后兼容接口调整记录。
3. CC-TEST-001～008 状态及逐项证据的 ATR。
4. IHR、ATR、FR；未验证事项、失败原始证据和适用的 M2/M3 回归范围。
5. 关闭评审建议；不由实施 Agent 自行宣布 CC CLOSED。

所有强制测试须有 PASS、FAIL 或有依据的 BLOCKED / NOT RUN 结论；强制项不能以不说明原因的 BLOCKED / NOT RUN 提交关闭。当前 CC 只需自动化和组件集成验收，HVR 由 CC-M4-05 完成。

## 9. 风险与待决事项

| 编号 | 问题 | Draft 处置建议 |
|---|---|---|
| OPEN-01 | 现有 Office Tool / Collector 数据能否表达分组键和指标的独立验证意图 | 实施前核查现有契约；缺少时在同一 Office Tool 中设计最小、向后兼容的可选字段，并提交接口差异供评审。 |
| OPEN-02 | 产品支持的公式 / 聚合范围及计算器 | 用 E02 中 COUNTIF / SUM 建立最低回归证据；追加任何公式族需有独立 oracle 对照和兼容证据。重算器候选以隔离 LibreOffice Spike 为依据，不视为已批准产品决策。 |
| OPEN-03 | 缓存值可信条件、外链 / 宏 / 易变公式策略 | 通过差异注入确认不可信或不可执行公式 fail-closed；保持原件 SHA。 |
| OPEN-04 | Agent 实际利用验证回执的方式 | 用真实可见工具回执与后续动作验证；测试替身只能证明隔离链路，不替代 CC-M4-05 真实 E2E。 |

这些事项是本 CC 的实施决策与测试问题，不修改或重新冻结 TDD。若证据显示必须改变冻结 TDD 的原则、增加独立公开工具、改变 Candidate 生命周期或突破本 CC 范围，应停止该项并提交负责人决策。

## 10. 版本记录

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| v0.1 | 2026-11-21 | Draft | 基于冻结 M4 TDD v0.2、Implementation Plan v0.1、聚合 Spike 和 M4-TEST-04/07 起草；待项目负责人评审。 |
