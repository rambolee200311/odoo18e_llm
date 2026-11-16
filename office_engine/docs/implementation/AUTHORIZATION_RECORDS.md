# Office Engine 项目授权登记册（M2 / M3）

本文件仅记录负责人明确批准的未通过项处置，不改变原始测试、HVR 或上游阶段 Gate 状态。

## EXEMPTION-CC-M2-004-001

| 字段 | 记录 |
|---|---|
| 豁免项 | Odoo `HttpCase.browser_js` 自动浏览器测试（ATR-ISSUE-001；CC-TEST-002/010 的自动化浏览器子项） |
| 状态 | `Skipped` |
| 原因 | 本机缺少 `websocket-client`，未安装额外依赖；负责人已通过内置浏览器确认卡片显示、合法字段选择、保存及确认，并明确批准关闭 CC-M2-004。 |
| 影响 | 人工核心路径有证据，但没有自动浏览器回归；普通消息隔离、控制台错误等仍依靠非浏览器自动化证据或未验证。原 ATR 状态保持 `SKIPPED/PARTIAL`。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人于 2026-10-23 明确指示“cc-004允许关闭，提交推送git”；并于 2026-10-23 确认“人工验证通过”。 |

## EXEMPTION-CC-M2-004-002

| 字段 | 记录 |
|---|---|
| 豁免项 | HVR-SCN-003 未由人类完整验证的取消/不完整映射子场景；HVR-SCN-004 普通聊天发送与浏览器 console 检查 |
| 状态 | `Missing` |
| 原因 | 负责人确认了卡片展示、字段选择、保存和确认；其余子场景未在内置浏览器中完整执行。负责人随后明确批准关闭 CC-M2-004。 |
| 影响 | 不声称取消、澄清补项及错误后普通聊天发送均通过；残余交互回归风险被接受。HVR 保持 PARTIAL，场景状态保持 NOT RUN。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人于 2026-10-23 明确指示“cc-004允许关闭，提交推送git”。 |

## EXEMPTION-CC-M2-004-003

| 字段 | 记录 |
|---|---|
| 豁免项 | Implementation Plan 阶段 3 XML-RPC 安装/升级 Gate 的证据缺口（CC-M2-004-OPEN-001） |
| 状态 | `Missing` |
| 原因 | CC-M2-003 ATR 有 CLI 升级与 TransactionCase 证据，但没有 Plan 明定的 XML-RPC 安装/升级记录；负责人已批准 CC-M2-004 带该缺口关闭。 |
| 影响 | 仅接受本次 CC 的行政关闭处置；阶段 3 Gate 仍为 OPEN，计划阶段不标记 PASS，M2 阶段与后续阶段 Gate 仍需独立评估。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人于 2026-10-23 明确指示“cc-004允许关闭，提交推送git”。 |

## EXEMPTION-CC-M2-005-001

| 字段 | 记录 |
|---|---|
| 豁免项 | 全 Addon 回归：`TestOfficeMappingSession.test_cc_test_003_attachment_must_be_attached_to_the_same_thread_message` 的共享数据库全表 Session 数断言 |
| 状态 | `Failed`（原始失败保持不变） |
| 原因 | 测试断言开发数据库中全表 Session 数必须为 0；既有历史记录导致断言失败。负责人认定这是测试基建缺陷，不作为 CC-M2-005 条件关闭的阻塞。 |
| 影响 | 不证明该测试通过，不证明全 Addon 全绿。只接受该失败不阻断 CC-M2-005 的条件关闭；脆弱断言的修复作为独立测试基建债务跟踪。其他需求缺口和 PARTIAL 证据继续按各自状态保留。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人明确裁定：“测试代码写了‘全表 Session 必须为 0’这种脆弱的断言，遭遇了开发库的历史残留数据。这属于测试基建缺陷，不作为阻塞本 CC 关闭的理由”，并批准将 CC-M2-005 状态更新为 `CONDITIONALLY CLOSED`。 |

## EXEMPTION-CC-M2-005-001

| 字段 | 记录 |
|---|---|
| 豁免项 | 全 Addon 回归：`TestOfficeMappingSession.test_cc_test_003_attachment_must_be_attached_to_the_same_thread_message` 的共享数据库全表 Session 数断言 |
| 状态 | `Failed`（原始失败保持不变） |
| 原因 | 该测试断言开发数据库中全表 Session 数必须为 0；既有历史记录导致断言失败。负责人认定这是测试基建缺陷，不作为 CC-M2-005 条件关闭的阻塞。 |
| 影响 | 不证明该测试通过，也不证明全 Addon 全绿。只接受该失败不阻断 CC-M2-005 条件关闭；脆弱断言修复作为独立测试基建债务跟踪。其他需求缺口和 PARTIAL 证据继续按各自状态保留。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人明确裁定：“测试代码写了‘全表 Session 必须为 0’这种脆弱的断言，遭遇了开发库的历史残留数据。这属于测试基建缺陷，不作为阻塞本 CC 关闭的理由”，并批准将 CC-M2-005 状态更新为 `CONDITIONALLY CLOSED`。 |

## 处置约束

- 上述授权只接受列明的未通过项；不把任何原生 `SKIPPED`、`NOT RUN`、`PARTIAL` 或 `OPEN` 改写为 PASS/RESOLVED。
- CC-M2-004 的处置为 `FROZEN WITH OPEN ITEMS`。对应 FR 的 Closure Status 仍按证据判断；豁免不自动使 Closure Status 成为 SATISFIED。
- CC-M2-005 的单项授权只接受列明的测试失败不阻塞其条件关闭；测试原生 FAIL 和 FR NOT SATISFIED 状态不变，其他未完成路径不在此授权范围内。
- CC-M2-005 的单项授权只接受列明的测试失败不阻塞其条件关闭；测试原生 FAIL 和 FR NOT SATISFIED 状态不变，其他未完成路径不在此授权范围内。
- 本登记不批准合并、发布、M2 阶段完成或变更 Implementation Plan 基线。

## M3 TDD v0.2 冻结授权与适用性裁定

### DECISION-M3-SRS-NA-001

| 字段 | 记录 |
|---|---|
| 决定 | M3 专属 SRS 不适用；M3 属于现有 Office Engine 的优化。M2 SRS 继续约束既有业务语义。 |
| 理由 | 负责人明确表示“这是优化，不需要 SRS”。 |
| 影响 | 本决定仅处理 M3 SRS 适用性；不豁免 TDD、Retriever、Hosted Code Interpreter、Silent Retrieval 或 HVR 的技术验证。若后续新增独立业务需求，须先修订 / 新建 SRS。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人于 2026-11-13 回答 SRS 门禁：“2，这是优化，不需要srs”。 |
| 经办人确认 | 已依据负责人明确授权记录；M3 SRS 状态为 N/A，不伪称存在已冻结 M3 SRS。 |

### EXEMPTION-TDD-M3-OPEN-01-001

| 字段 | 记录 |
|---|---|
| 豁免项 | TDD v0.2 `OPEN-01`：完整数据 handoff 的 Hosted CI 文件输入兼容性，以及 Provider Tool Schema / Tool Execute / ORM Domain JSON Schema 三层兼容性未验证。 |
| 状态 | `Missing` |
| 原因 | 当前 Responses Adapter 仅有单 XLSX 输入与 instruction；多页数据 handoff 尚无真实 Hosted CI 载体验证。负责人批准 TDD 带此未通过项冻结。 |
| 影响 | 不代表 handoff 或 Domain Schema 通过。CC-M3-03 / CC-M3-04 及依赖其结果的完整导出实现保持阻断，直至适用兼容验证通过或 TDD 经版本化修订。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人于 2026-11-13 指示“批准冻结tdd，起草implement plan”；此前已收到本 TDD 七项 OPEN 状态摘要。 |
| 经办人确认 | 已获负责人明确授权按 `FROZEN WITH OPEN ITEMS` 冻结 TDD；底层状态仍为 Missing。 |

### EXEMPTION-TDD-M3-OPEN-02-001

| 字段 | 记录 |
|---|---|
| 豁免项 | TDD v0.2 `OPEN-02`：root / relation rows、handoff bytes、Provider tokens 与 wall-clock 有界资源预算尚无基准测试结果。 |
| 状态 | `Missing` |
| 原因 | 本轮只处理设计冻结；未执行合成规模基准。负责人批准 TDD 带此未通过项冻结。 |
| 影响 | 不声称支持无限数据规模。相关容量 CC 在确定有限预算前不得进入实现或完整性验收。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人于 2026-11-13 指示“批准冻结tdd，起草implement plan”，此前已收到 OPEN-02 未决项摘要。 |
| 经办人确认 | 已获负责人明确授权按 `FROZEN WITH OPEN ITEMS` 冻结 TDD；底层状态仍为 Missing。 |

### EXEMPTION-TDD-M3-OPEN-03-001

| 字段 | 记录 |
|---|---|
| 豁免项 | TDD v0.2 `OPEN-03`：目标运行环境 / 调用链是否能保持单个 Odoo `REPEATABLE READ` transaction read view，以及 Accept 时 freshness 语义尚未验证 / 裁定。 |
| 状态 | `Missing` |
| 原因 | 源码确认 Odoo cursor 默认隔离级别，但目标运行链测试和 M3 freshness 决议未完成。负责人批准 TDD 带此未通过项冻结。 |
| 影响 | 不声称目标环境已提供单事务完整性。分页 / 关系收集实现前须完成隔离验证；不默认 Accept 前重复完整查询。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人于 2026-11-13 指示“批准冻结tdd，起草implement plan”，此前已收到 OPEN-03 未决项摘要。 |
| 经办人确认 | 已获负责人明确授权按 `FROZEN WITH OPEN ITEMS` 冻结 TDD；底层状态仍为 Missing。 |

### EXEMPTION-TDD-M3-OPEN-04-001

| 字段 | 记录 |
|---|---|
| 豁免项 | TDD v0.2 `OPEN-04`：record projection、aggregation、semantic transform 的任务级输出核验边界未完成 TV。 |
| 状态 | `Missing` |
| 原因 | 任务类型的完整性 / 语义验证证据尚未按通用 fixture 验证。负责人批准 TDD 带此未通过项冻结。 |
| 影响 | 不降低任何完整交付要求；用户要求完整而文件输出不能证明满足任务契约时，禁止标记完整或作为完整结果交付。CC-M3-04 前需关闭。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人于 2026-11-13 指示“批准冻结tdd，起草implement plan”，此前已收到 OPEN-04 未决项摘要。 |
| 经办人确认 | 已获负责人明确授权按 `FROZEN WITH OPEN ITEMS` 冻结 TDD；底层状态仍为 Missing。 |

### EXEMPTION-TDD-M3-OPEN-05-001

| 字段 | 记录 |
|---|---|
| 豁免项 | TDD v0.2 `OPEN-05`：Registry model / field metadata 面向哪些角色可见的安全决议未完成。 |
| 状态 | `Missing` |
| 原因 | 已有 TV 确认 Registry / `fields_get()` 的技术边界，但角色范围的正式安全决议未完成。负责人批准 TDD 带此未通过项冻结。 |
| 影响 | 不扩大业务记录权限；`fields_get()` 过滤、ACL、Record Rules 和字段访问仍不可绕过。Registry 扩展在 metadata 范围决议前阻断。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人于 2026-11-13 指示“批准冻结tdd，起草implement plan”，此前已收到 OPEN-05 未决项摘要。 |
| 经办人确认 | 已获负责人明确授权按 `FROZEN WITH OPEN ITEMS` 冻结 TDD；底层状态仍为 Missing。 |

### EXEMPTION-TDD-M3-OPEN-06-BUS-001

| 字段 | 记录 |
|---|---|
| 豁免项 | TDD v0.2 `OPEN-06`：Odoo Bus 默认 / 显式订阅路径首次通知时序与 UI 可见性未验证。 |
| 状态 | `Missing` |
| 原因 | Silent Retrieval TV 未验证 Bus fan-out 和真实 UI。负责人批准 TDD 带此未通过项冻结。 |
| 影响 | 不宣称全链路 Silent Retrieval 通过；依赖该路径的静默实现须先通过 Bus / Discuss / SSE 验证。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人于 2026-11-13 指示“批准冻结tdd，起草implement plan”，此前已收到 OPEN-06 未决项摘要。 |
| 经办人确认 | 已获负责人明确授权按 `FROZEN WITH OPEN ITEMS` 冻结 TDD；底层状态仍为 Missing。 |

### EXEMPTION-TDD-M3-OPEN-06-STREAM-001

| 字段 | 记录 |
|---|---|
| 豁免项 | TDD v0.2 `OPEN-06`：流式工具续接试验失败，generator return value 未继续到工具执行链。 |
| 状态 | `Failed`（原 TV 结论保持不变） |
| 原因 | Silent Retrieval TV 实际观察到 Provider 仅调用一次，未产生 Retriever 执行记录；下游不得宣称流式静默通过。负责人批准保留该失败并冻结 TDD。 |
| 影响 | 不覆盖或隐藏流式 assistant tool-call 消息；流式 Silent Retrieval 不作为当前可交付能力。是否修复须走下游方案并验证，不能修改上游 `odoo-llm`。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人于 2026-11-13 指示“批准冻结tdd，起草implement plan”，此前已收到 OPEN-06 的 NOT VERIFIED 状态与流式失败结果。 |
| 经办人确认 | 已获负责人明确授权按 `FROZEN WITH OPEN ITEMS` 冻结 TDD；原始 Failed 状态保持不变。 |

## M3 Implementation Plan v0.1 冻结与适用性裁定

### PLAN-M3-001

| 字段 | 记录 |
|---|---|
| 批准事项 | Office Engine M3 Implementation Plan v0.1（修订后的三 CC 版本） |
| 冻结结果 | `Frozen`; baseline validity `VALID`; baseline date `2026-11-13` |
| DDD 适用性 | N/A。M3 为现有 Office Engine 优化，不引入新业务 aggregate 或 domain state；M2 SRS 与 M3 TDD 继续作为对应权威基线。 |
| 批准范围 | 批准计划中的三 CC 划分、依赖次序、范围、验收和按 CC 划分的 OPEN 门禁；本记录不关闭任何 TDD OPEN，也不改变其原始 `Missing` / `Failed` 状态。 |
| 未授权事项 | 不授权创建/冻结正式 CC、编码、Provider 调用或外发、数据库操作、模块升级、部署或发布。各 CC 仍须满足自己的入口门禁并另行获得 Coding Authorization。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人明确指示：“冻结计划，起草cc-01契约”。该指令批准当前三 CC 计划基线；计划中列明的 OPEN-01 Domain Schema facet、OPEN-05 metadata scope、环境和角色门禁仍未解决。 |
| 经办人确认 | 计划状态已更新为 Frozen / VALID；CC-M3-01 仍因其专属技术及环境门禁处于 BLOCKED。 |

## M3 TDD v0.3 / Plan v0.2 / CC-M3-01 v0.2 — 批准与实施授权

### DECISION-M3-SEC-001

| 字段 | 记录 |
|---|---|
| 决定 | `discover` 和 `describe` 是通用 Registry Schema Discovery：对现有 Retriever 工具调用者开放模型与字段定义，不检查当前用户业务模型 ACL、Record Rules 或字段组；不读取业务记录、不使用 `sudo()`。`search` 严格遵守调用者当前 ORM 权限。 |
| 关闭项 | 关闭 TDD `OPEN-05` 的设计决策门禁。实施行为仍由 `TEST-RET-002` 验收；该测试尚未运行，不代表 Passed。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人明确决定：“discover 和 describe 是通用 Schema Discovery 能力，不受业务模型 ACL、Record Rules 限制……search 必须严格遵守当前用户的 ORM 权限，不允许 sudo 或权限绕过。” |

### TDD-M3-002

| 字段 | 记录 |
|---|---|
| 批准事项 | `docs/design/TDD_office_engine_m3_v0.3.md` |
| 冻结结果 | `FROZEN WITH OPEN ITEMS`；版本 v0.2 原样保留为历史基线 |
| 本轮设计调整 | Registry metadata 权限按 `DECISION-M3-SEC-001`；关闭 OPEN-05 设计门禁；原 OPEN-01 拆为 OPEN-01a（Domain Schema 三层兼容性，CC-M3-01 实施验收）及 OPEN-01b（Hosted CI handoff，CC-M3-02 前置 Spike）；对齐三 CC 边界与既有开发数据库限制。 |
| 未通过项 | OPEN-01b、OPEN-02、OPEN-03、OPEN-04、OPEN-06 仍按原状态保留并由 v0.2 对应授权记录追溯；不宣称 Passed。OPEN-01a 的三层测试必须在 CC-M3-01 关闭前通过；OPEN-05 不再作为未决项。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 负责人已审阅修订稿并指示：“批准冻结cc，进入实施”；该指令被执行为冻结 CC-M3-01 所需的 TDD / Plan 版本化前置基线，并授权后续进入 CC-M3-01 实施。 |
| 经办人确认 | TDD v0.3 已发布为独立冻结版本；v0.2 未覆盖。未运行测试仍为 NOT RUN / Missing。TDD 冻结本身不授权超出 CC 的操作。 |

### PLAN-M3-002

| 字段 | 记录 |
|---|---|
| 批准事项 | `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m3_v0.2.md` |
| 冻结结果 | `Frozen`; baseline validity `VALID`; baseline date `2026-11-13` |
| 基线 | M3 TDD v0.3（`TDD-M3-002`）、M2 SRS v1.1.0 及 `DECISION-M3-SRS-NA-001` |
| 门禁变更 | OPEN-05 已按负责人决策关闭；OPEN-01a 三层 Schema 兼容验证属于 CC-M3-01 实施验收，不是开工门禁；OPEN-01b handoff Spike 仍是 CC-M3-02 前置；测试环境在实际执行前核实，不要求在技术冻结前指定环境或人员。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 负责人指示“批准冻结cc，进入实施”；据此批准与冻结 CC-M3-01 所需的计划修订，并完成基线对齐。 |
| 经办人确认 | 使用三 CC 计划；本计划不授权 CC-M3-02/03。 |

### CC-M3-01-001

| 字段 | 记录 |
|---|---|
| 批准事项 | `docs/implementation/CC-M3-01_Retriever_Enhancement_v0.2.md` |
| 冻结结果 | `Frozen`; CC-M3-01 开始实施 |
| 授权范围 | 仅实施 CC-M3-01 范围内的下游 `office_engine_m3` addon 与相应测试；不修改上游 `odoo-llm`、M2 addon 或其他 CC。 |
| 数据库边界 | 只允许使用现有开发数据库 `odoo18e_llm`。禁止创建新数据库、连接生产数据库或修改既有业务记录 / ACL。合成测试通过 Odoo 测试事务回滚。 |
| Provider 边界 | 本记录授权 CC 范围内编码与本地 / Odoo 测试；真实 Provider 调用仍须满足 CC 的专项授权要求。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人明确指示：“批准冻结cc，进入实施”，并补充：“我们现在是开发环境，不批准新建数据库，只允许使用odoo18e_llm数据库，继续实施。” |
| 经办人确认 | 负责人命令作为本 CC 的 Coding Authorization；不授权生产操作、外部数据外发、其他 CC 或发布。 |

## M3 v0.4 / Plan v0.3 / CC-M3-02 v0.2 — 带未决项冻结授权

### EXEMPTION-TDD-M3-V04-OPEN-01B-001

| 字段 | 记录 |
|---|---|
| 豁免项 | TDD v0.4 / Plan v0.3 / CC-M3-02 v0.2 的 `OPEN-01b`：Hosted Code Interpreter handoff 最小可行性 Spike 尚未执行。 |
| 状态 | `Missing`（前置 Spike）；完整 148 条及更大有界数据集验收为 `NOT RUN`。 |
| 原因 | 本次授权仅冻结设计、计划和 CC 文档；Spike 与完整导出测试留在获准的后续阶段执行。 |
| 影响 | 本记录只授权三个文档按 `FROZEN WITH OPEN ITEMS` 冻结，不宣称 handoff 可行，不豁免最终验收。OPEN-01b Spike 通过前，CC-M3-02 不得实施；148 条、更大数据集和 Hosted CI 实读验收仍为强制要求。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 负责人已获知 OPEN-01b Spike Missing 及实施仍受门禁限制后，于 2026-11-13 明确指示：“批准冻结3份文档”。 |
| 经办人确认 | 仅按带未决项方式冻结文档；Spike 状态保持 Missing，CC-M3-02 实施仍被阻断，另需 Coding Authorization。 |

### EXEMPTION-TDD-M3-V04-OPEN-02-001

| 字段 | 记录 |
|---|---|
| 豁免项 | TDD v0.4 / Plan v0.3 / CC-M3-02 v0.2 的 `OPEN-02`：有界资源可行性 Spike 未执行；有限预算及限额验收尚未取得。 |
| 状态 | `Missing`（前置 Spike）；限额及实施验收为 `NOT RUN`。 |
| 原因 | 本次授权仅冻结文档；资源区间和信号测量 Spike 留在后续 CC-M3-02 门禁内。 |
| 影响 | 只允许文档带 OPEN 状态冻结，不代表可无界处理数据。OPEN-02 Spike 通过前不得开始 CC-M3-02 实施；实施时仍须测定有限预算，并通过限额内、边界和超限测试。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 负责人已获知 OPEN-02 Spike Missing 及实施仍受门禁限制后，于 2026-11-13 明确指示：“批准冻结3份文档”。 |
| 经办人确认 | 仅按带未决项方式冻结文档；OPEN-02 仍是 CC-M3-02 实施前置门禁。 |

### EXEMPTION-TDD-M3-V04-OPEN-03-001

| 字段 | 记录 |
|---|---|
| 豁免项 | TDD v0.4 / Plan v0.3 / CC-M3-02 v0.2 的 `OPEN-03`：同一 cursor / transaction 读视图的最小可行性 Spike 未执行。 |
| 状态 | `Missing`（前置 Spike）；读视图和并发变化实施验收为 `NOT RUN`。 |
| 原因 | 本次授权仅冻结文档；目标调用边界验证留在后续 CC-M3-02 门禁内。 |
| 影响 | 只允许文档带 OPEN 状态冻结，不证明目标运行路径已有同一读视图保证。OPEN-03 Spike 通过前不得开始 CC-M3-02 实施；实现验收仍须核验跨页及关联查询的一致性和 freshness 边界。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 负责人已获知 OPEN-03 Spike Missing 及实施仍受门禁限制后，于 2026-11-13 明确指示：“批准冻结3份文档”。 |
| 经办人确认 | 仅按带未决项方式冻结文档；OPEN-03 仍是 CC-M3-02 实施前置门禁。 |

### EXEMPTION-TDD-M3-V04-OPEN-04-001

| 字段 | 记录 |
|---|---|
| 豁免项 | TDD v0.4 / Plan v0.3 / CC-M3-02 v0.2 的 `OPEN-04`：现有 Candidate / 文件路径的客观输出核验可行性 Spike 未执行。 |
| 状态 | `Missing`（前置 Spike）；投影、Hosted CI 输出及版本完整性实施验收为 `NOT RUN`。 |
| 原因 | 本次授权仅冻结文档；最小文件 / identity 核验 Spike 留在后续 CC-M3-02 门禁内。 |
| 影响 | 只允许文档带 OPEN 状态冻结，不降低完整性交付门槛。OPEN-04 Spike 通过前不得开始 CC-M3-02 实施；客观完整性检查及任务级验证等级仍须满足冻结 TDD。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 负责人已获知 OPEN-04 Spike Missing 及实施仍受门禁限制后，于 2026-11-13 明确指示：“批准冻结3份文档”。 |
| 经办人确认 | 仅按带未决项方式冻结文档；OPEN-04 仍是 CC-M3-02 实施前置门禁。 |

### EXEMPTION-TDD-M3-V04-OPEN-06-BUS-001

| 字段 | 记录 |
|---|---|
| 豁免项 | TDD v0.4 / Plan v0.3 的 `OPEN-06` Bus / Discuss 首次通知时序和真实 UI 可见性未验证。 |
| 状态 | `Missing`。 |
| 原因 | 本次授权仅冻结三份文档；Bus fan-out / 真实 UI 验证属于后续 CC-M3-03。 |
| 影响 | 只允许 TDD 和计划按 `FROZEN WITH OPEN ITEMS` 冻结，不宣称全链路 Silent Retrieval 通过。CC-M3-03 对任何声称静默的路径仍须先取得相应证据。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 负责人已获知 Bus/UI 证据 Missing 后，于 2026-11-13 明确指示：“批准冻结3份文档”。 |
| 经办人确认 | Bus/UI 状态保持 Missing；此授权不豁免 CC-M3-03 对所交付静默路径的验收。 |

### EXEMPTION-TDD-M3-V04-OPEN-06-STREAM-001

| 字段 | 记录 |
|---|---|
| 豁免项 | TDD v0.4 / Plan v0.3 的流式工具续接路径未能将 generator return value 传至后续工具执行。 |
| 状态 | `Failed`（原 TV 结果保持不变）。 |
| 原因 | Silent Retrieval TV 实际流式工具续接失败；本次只冻结文档，不修复或重测。 |
| 影响 | 只允许 TDD 和计划以 `FROZEN WITH OPEN ITEMS` 发布，不代表流式路径可用或静默通过。不得隐藏未验证流式工具消息；若该路径纳入后续交付，须先修复并验证，且不得修改上游 `odoo-llm`。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 负责人已获知流式续接 Failed 后，于 2026-11-13 明确指示：“批准冻结3份文档”。 |
| 经办人确认 | 原始 Failed 状态保持不变；本授权不宣称通过，也不授权实施。 |

### TDD-M3-003

| 字段 | 记录 |
|---|---|
| 批准事项 | `docs/design/TDD_office_engine_m3_v0.4.md`（Office Engine M3 技术详细设计 v0.4） |
| 冻结结果 | `FROZEN WITH OPEN ITEMS`；当前技术基线；版本 v0.3 保留为历史基线 |
| 豁免记录 ID | `EXEMPTION-TDD-M3-V04-OPEN-01B-001`、`EXEMPTION-TDD-M3-V04-OPEN-02-001`、`EXEMPTION-TDD-M3-V04-OPEN-03-001`、`EXEMPTION-TDD-M3-V04-OPEN-04-001`、`EXEMPTION-TDD-M3-V04-OPEN-06-BUS-001`、`EXEMPTION-TDD-M3-V04-OPEN-06-STREAM-001` |
| 批准范围 | 冻结 TDD v0.4 作为后续设计 / CC 的技术基线；所有 OPEN、Missing、Failed 和 NOT RUN 状态按原义保留。 |
| 未授权事项 | 不授权 CC 实施、Provider 调用或外发、数据库操作 / 模块升级、部署、发布，亦不改变 CC-M3-02 的前置 Spike 门禁。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 负责人已获知三份文档的 OPEN 状态及 CC-M3-02 实施门禁仍阻断后，于 2026-11-13 明确指示：“批准冻结3份文档”。 |
| 经办人确认 | 仅按 FWOI 冻结，不把任何未执行验证标记为 Passed，不放行实现。 |

### PLAN-M3-003

| 字段 | 记录 |
|---|---|
| 批准事项 | `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m3_v0.3.md`（Office Engine M3 Implementation Plan v0.3） |
| 冻结结果 | `Frozen with open items`；baseline validity `VALID`；当前计划基线 |
| 豁免记录 ID | 同 `TDD-M3-003` 列出的六项 `EXEMPTION-TDD-M3-V04-*` 记录；底层状态保持 Missing / Failed |
| 批准范围 | 冻结三 CC 次序、范围和门禁映射；CC-M3-02 已冻结但 OPEN-01b/02/03/04 未完成且无 Coding Authorization，不能实施。 |
| 未授权事项 | 不授权任何 CC-M3-02/03 实施、Provider 调用或外发、数据库操作 / 模块升级、部署或发布。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 负责人于 2026-11-13 明确指示：“批准冻结3份文档”；该指示只批准基线冻结。 |
| 经办人确认 | 计划已更新为 v0.3 / `VALID`；OPEN 门禁状态未更改，任何实现仍须独立授权。 |

### CC-M3-02-001

| 字段 | 记录 |
|---|---|
| 批准事项 | `docs/implementation/CC-M3-02_完整数据至Office_v0.2.md`（CC-M3-02 v0.2） |
| 冻结结果 | `FROZEN WITH OPEN GATES`；CC 范围与验收契约冻结，未授权实施 |
| 豁免记录 ID | `EXEMPTION-TDD-M3-V04-OPEN-01B-001`、`EXEMPTION-TDD-M3-V04-OPEN-02-001`、`EXEMPTION-TDD-M3-V04-OPEN-03-001`、`EXEMPTION-TDD-M3-V04-OPEN-04-001` |
| 批准范围 | 冻结 CC 的范围、入口 Spike、实施验收和完成定义；四项最小前置 Spike 仍为 Missing，最终实施测试仍为 NOT RUN。 |
| Coding Authorization | **未批准。** 本记录不准许开始编码或 Provider / Hosted CI 外发。四项 Spike 通过后仍须单独取得 Coding Authorization。 |
| 数据库边界 | 任何后续获准测试仅使用现有开发数据库 `odoo18e_llm`；禁止新建数据库或访问生产环境。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 负责人于 2026-11-13 明确指示：“批准冻结3份文档”；本指示不包含 CC-M3-02 实施授权。 |
| 经办人确认 | 仅冻结文档；未调用 Provider、未访问数据库、未修改代码、未运行实施测试、未提交或推送 Git。 |

`Freeze disposition: FROZEN WITH OPEN ITEMS` 仅适用于本次获批的文档冻结。以上未决证据状态、实施前 Spike、最终验收要求和独立 Coding Authorization 门禁均保持有效。

### CC-M3-02-002

| 字段 | 记录 |
|---|---|
| 批准事项 | `docs/implementation/CC-M3-02_完整数据至Office_v0.2.md`（CC-M3-02 v0.2） |
| 授权范围 | 按冻结 CC-M3-02 实施范围开展下游 `office_engine_m3` 编码与自动化 / ORM / 集成测试；不得修改 `odoo-llm`、`office_engine_m2`、其他 addon 或扩大 CC。 |
| 前置门禁 | OPEN-01b / 02 / 03 / 04 最小可行性 Spike 均通过；证据见 `docs/implementation/ATR-M3-02_Preimplementation_Spikes.md` 与 `docs/verification/TV_CC_M3_02_Preimplementation_Spikes_20261115.md`。完整实施验收仍为 NOT RUN。 |
| 数据库边界 | 只允许使用现有开发数据库 `odoo18e_llm`；禁止创建数据库、访问生产库或修改既有业务记录。测试使用合成数据和回滚事务；任何模块安装 / 升级先核对目标库。 |
| Provider 边界 | Coding Authorization 不构成新的 Provider / Hosted Code Interpreter 外发授权；真实 Provider 调用仍须按 CC 在每次请求前取得专项授权，且只可发送合成数据。 |
| 其他未授权事项 | 不授权部署、发布、真实业务数据外发、CC-M3-03、Git 提交或推送。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 负责人于 2026-11-15 明确指示：“授权进入cc-02实施”。 |
| 经办人确认 | 仅按 CC-M3-02 v0.2 实施；TDD v0.4 / Plan v0.3 保持冻结基线；实现与验收证据持续写入本 CC 的 IHR / ATR。 |

### CC-M3-02-003

| 字段 | 记录 |
|---|---|
| 批准事项 | 继续实施 CC-M3-02；解决 M3 新建工作簿与现有 M2 Candidate 生命周期的兼容性 |
| 授权范围 | 负责人于 2026-11-16 明确授权优先复用 Candidate → Accept → Finalize；允许为此作必要的下游 M2 兼容性修改，须保留 M2 原有行为和用户确认门禁。授权完成 CC-M3-02 代码、自动化测试、真实 Provider 集成验证，并更新兼容性设计补充、IHR 与 ATR。 |
| Provider 边界 | 允许使用已配置的真实 Provider / Hosted Code Interpreter 验证；只使用合成数据。`OpenAI GPT-5.6 Luna` 的测试 token 上限仅为进程级覆盖，不持久化修改 Provider 配置。 |
| 数据库边界 | 仅现有开发数据库 `odoo18e_llm`；不创建数据库、不访问生产库或其他数据库；业务测试数据使用合成记录和回滚事务。 |
| 保留约束 | 不修改 `odoo-llm`；M2 `action="create"` legacy direct-V1 行为保持；M3 不绕过 Candidate、Accept、Reject、Finalize；不生成本地 Excel 业务内容；不部署、不发布。 |
| Git 边界 | 本次未授权 Git commit / push；不得提交或推送。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`） |
| 授权证据 | 负责人于 2026-11-16 明确指示：“继续实施 CC-M3-02……已授权解决 M3 新建工作簿与 M2 Candidate 生命周期的兼容性问题……完成代码修改、自动化测试及真实 Provider 集成验证……不要因正常的接口兼容性问题反复停止开发或申请授权。” |
| 经办人确认 | 此项授权仅扩展 CC-M3-02 的兼容性实施和 Provider 测试边界；实际结果按 ATR 记录。真实 Provider 输出验证未通过，CC 不关闭。 |
