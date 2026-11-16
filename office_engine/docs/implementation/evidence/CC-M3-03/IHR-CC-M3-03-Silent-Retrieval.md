<!--
模板来源：office_engine/docs/skill/odoo-project-workflow/references/templates/Coding/IHR模板.md
模板版本 / 状态：v1.0.0 Frozen
模板同步检查：PASS（2026-11-16；--repo-root office_engine）
-->

# IHR — CC-M3-03 静默检索与最终 HVR

## 1. 执行信息

| 字段 | 值 |
|---|---|
| Intent ID | `CC-M3-03` |
| CC | [`CC-M3-03 v0.2`](../../CC-M3-03_静默检索与最终HVR_v0.2.md)，FROZEN WITH OPEN ITEMS |
| 模块 | `office_engine_m3` |
| 实施人 | Codex；负责人 Li Jianqiang |
| 开始日期 | 2026-11-16 |
| 实施状态 | 核心代码和 HVR 已完成；等待关闭评审 |
| 分支 / 基线 | `codex/cc-m3-01-provider-acceptance` / `48e25a52ec45938b2ff8a4c9e3ac32365317a5f7` |
| 数据库 | 仅使用现有开发库 `odoo18e_llm` |
| 授权 | [`CC-M3-03-001`](../../AUTHORIZATION_RECORDS.md#cc-m3-03-001) |

## 2. 实施历史

### IHR-001 — 冻结与授权

| 字段 | 记录 |
|---|---|
| 日期 / 阶段 | 2026-11-16 / 冻结与授权 |
| 操作 | 负责人指示“冻结cc-03,进入实施”。CC-M3-03 v0.2 以保留开放项的方式冻结；单次授权覆盖下游开发、现有开发库合成数据、真实 Provider / Hosted CI、UI HVR、清理、证据记录及本 CC 范围的 Git 工作。 |
| 结果 | 已完成。该授权不代表验收已通过。 |
| 偏离 | 无。 |

### IHR-002 — 实施评估

| 字段 | 记录 |
|---|---|
| 日期 / 阶段 | 2026-11-16 / 实施评估 |
| 操作 | 确认可通过下游扩展 `llm.thread`、`mail.message`、OpenAI 工具格式化及 M2 非流式 Route B。保留用户在 8091 的服务不动；本任务的测试及 HVR 服务使用 8092。 |
| 结果 | 可在下游模块完成，不需要改上游或 M2 addon。 |
| 偏离 | 无。 |

### IHR-003 — 静默检索与路由实现

| 字段 | 记录 |
|---|---|
| 日期 / 阶段 | 2026-11-16 / 实施 |
| 文件 | `models/llm_thread.py`、`models/mail_message.py`、`models/llm_provider.py`、`models/__init__.py`、`__manifest__.py` |
| 操作 | 添加通用模型发现、关联表规划及 `export_records` 指引；识别非流式 Office 路径，包括新建无附件工作簿的请求；在首次通知前标记静默消息；过滤 Bus 通知、Discuss 历史和 SSE 消息事件；查询失败时恢复错误消息可见性；为 OpenAI 工具调用提供有效 M3 Office Schema。原始 `mail.message`、工具参数与结果、Agent 上下文仍保留。 |
| 结果 | 自动化边界测试和最终真实 UI 路径已验证；详见 ATR。 |
| 偏离 | 未改变冻结架构。 |

### IHR-004 — HVR 发现问题与修正

| 字段 | 记录 |
|---|---|
| 日期 / 阶段 | 2026-11-16 / Provider HVR 修复与重试 |
| 操作 | 真实 Agent 试运行发现：① 使用旧 `action=create` 绕过 Candidate；② 关联工作表用了无效的点分路径；③ 增加了用户未请求的通用 `display_name` 列；④ Hosted CI 改写了源数量。受影响的结果均被拒绝或停止，没有作为完整导出交付。随后更新下游通用指引，要求使用 `export_records`、按 collection key 独立生成子表、只保留请求列，并逐格照抄源值、重新打开并校验；另修复 Odoo `Date` 与 XLSX 午夜时间的比较。 |
| 文件 | `models/llm_thread.py`、`services/data_handoff.py`、`services/export_verification.py`、`tests/test_export.py` |
| 结果 | 最终线程 677 的独立数据和身份核验通过；随后按显式 Accept / Finalize 流程完成 Candidate 生命周期。详细记录见 `HVR-M3-03-001.md`。 |
| 偏离 | 未改冻结 TDD / Plan / CC，未改上游或 M2 代码。 |

### IHR-005 — 自动化验证

| 字段 | 记录 |
|---|---|
| 日期 / 阶段 | 2026-11-16 / 测试 |
| 操作 | 在 `odoo18e_llm` 上运行 `office_engine_m3` 模块测试，原有 38 项和追加附件上下文回归后的 42 项均通过。尝试 M2 全量回归：正常发现流程在导入 auditlog 时因缺少 `odoo.tests.common.SETATTR_SOURCES` 中止；使用隔离兼容 shim 后继续运行，208 项中仍有 13 failures、69 errors。 |
| 结果 | M3 测试通过；M2 全量回归未验证通过，不得记为 PASS。 |
| 证据 | ATR §3；`test-run-004-exact-copy-pass.log`、`test-run-006-attachment-context-regression.log`；`test-run-005-m2-regression-status.md`。 |

### IHR-006 — 最终 HVR 与合成数据清理

| 字段 | 记录 |
|---|---|
| 日期 / 阶段 | 2026-11-16 / HVR |
| 操作 | 在已登录的 Odoo UI 中，以 OpenAI GPT-5.6 Luna 执行自然语言任务。Agent 自主发现并描述模型、选择字段及关联，生成 Candidate 395；用户在页面发送“接受”后，Agent 执行 Accept 和 Finalize。通过只读 ORM 读取记录核对 receipt、Candidate / 最终附件和最终消息；独立 XLSX 验证器核对源身份、字段值及父子关系。随后实际下载浏览器附件并核对其 SHA；最后仅通过 ORM 删除本次唯一标记的合成 fixture，并确认相关计数归零。 |
| 结果 | Agent 规划、Candidate 生命周期、最终附件与浏览器下载文件内容 / SHA 核验通过。平台显示的 `PARTIALLY_VERIFIED` 状态已向用户披露，未被改写。 |
| 证据 | [`HVR-M3-03-001.md`](HVR-M3-03-001.md)、`hvr_actual_trace_thread_677.json`、`workbook_verification_v395.json`、`browser_download_verification_v395.json`、`fixture_cleanup.json`。 |
| 偏离 | 未绕过 M2 确认门禁；未修改本次合成数据以外的业务记录。 |

### IHR-007 — 附件上下文缺陷修复

| 字段 | 记录 |
|---|---|
| 日期 / 阶段 | 2026-11-16 / HVR 问题调查与回归 |
| 操作 | 检查失败线程 264、M3/M2 Provider 参数构建、Office Schema、附件定位和 Silent Retrieval。确认 M2 附件发现仅扫描最近 25 条用户消息；另确认无附件消息“整理成一个 Excel”没有命中 fileless 路由。M3 下游完整扫描 Thread 附件关系、加入纯文本附件引用、支持明确文件名选择历史附件，并补足中文路由 / 不上传提示；Silent Retrieval 上下文筛选不变。 |
| 结果 | M3 自动化测试 42 项全部通过；覆盖 >100 条用户消息、历史附件优先、静默消息保留上下文及无附件 Odoo 导出路由。未再次调用真实 Provider。 |
| 证据 | [`附件上下文丢失调查与修复.md`](附件上下文丢失调查与修复.md)、`test-run-006-attachment-context-regression.log`。 |
| 偏离 | 未改上游或 M2 源码；未改 TDD、Plan、冻结 CC；没有将失败线程 264 描述为历史附件丢失，因为该线程没有上传附件。 |

### IHR-008 — M2 回归分流与 Silent Retrieval 边界复核

| 字段 | 记录 |
|---|---|
| 日期 / 阶段 | 2026-11-16 / CC 收尾回归 |
| 操作 | 复核 M2 全量回归原始日志；运行 `TestWorkbookVersionState` 全类及 `test_fileless_xlsx_request_binds_route_b_tools_for_create_and_followup_turns` 定向测试。并按负责人此前要求，复核 `TEST-SILENT-002`–`005` 对确定性自动化边界的充分性。 |
| 结果 | M2 全量原始结果仍为 208 项中的 13 failures / 69 errors，不记全量 PASS。定向 M2 测试 12 项、0 failures、0 errors；M3 42 项及真实 HVR 通过。67 个全量错误是 OfficeCore 隔离 worker 异常退出（IPC pipe `EOFError`），具体原因未明，未归类为环境问题或 M3 回归。另有 failed-create 后的 current 不可用错误。依赖第二家公司的 1 项失败和 1 项 setup error 按 CC 范围列为 N/A。依据本轮测试与变更范围审查，`TEST-REG-001` 建议 PASS（范围化；本轮未发现回归）；不声称 M2 全量套件通过。 |
| 证据 | [`test-run-005-m2-regression-status.md`](test-run-005-m2-regression-status.md)、原始日志 `test-run-005-m2-regression-normal-import.log` / `test-run-005-m2-regression-full-compat.log`、[`test-run-007-targeted-m2-regression.log`](test-run-007-targeted-m2-regression.log)。 |
| Silent 边界 | `TEST-SILENT-002`–`005` 的确定性安全 / 可见性边界由自动化覆盖；HVR 只报告实际观察到的非流式成功路径，不声称实际触发 Provider 随机错误或 mixed tool call。流式只验收未静默隐藏，不声称 generator 续接通过。 |
| 偏离 | 未修改 M2 / OfficeCore、冻结 TDD / Plan / CC；未扩大测试环境或创建第二家公司。 |

## 3. 实际变更清单

| 文件 | 变更 | CC 追溯 |
|---|---|---|
| `office_engine_m3/models/llm_provider.py` | OpenAI 使用现有 Office 工具的有效 M3 Schema | `CC-CHANGE-004/006` |
| `office_engine_m3/models/llm_thread.py` | 通用发现 / 导出规划、非流式 Silent Retrieval、全历史附件发现及 Provider 文本引用 | `CC-CHANGE-001/002/003/004` |
| `office_engine_m3/models/mail_message.py` | 持久静默标记、Discuss 历史过滤、失败消息恢复可见 | `CC-CHANGE-001/002`、`CC-PRESERVE-001` |
| `office_engine_m3/services/data_handoff.py` | 要求 Hosted CI 按源字段逐格照抄 | `CC-CHANGE-005` |
| `office_engine_m3/services/export_verification.py` | Odoo Date 字段按日历日期比较 | `CC-CHANGE-005` |
| `office_engine_m3/tests/test_silent_retrieval.py` | 静默、错误、历史、SSE、混合工具、流式边界和附件上下文回归 | `TEST-SILENT-001`–`005`；附加回归 |
| `office_engine_m3/tests/test_export.py` | OpenAI Schema、源值照抄指引、日期值测试 | `TEST-HVR-001`、`TEST-REG-001` |
| `office_engine_m3/__manifest__.py` | M3 addon 版本升级 | 实施需要 |

## 4. 偏离与未完成项

| 项目 | 处置 |
|---|---|
| 真实 Agent 生成的 Candidate 计划或内容不匹配 | 拒绝或停止受影响结果，再修正通用指引和验证后重试；没有将失败 Candidate 推进为 Current。 |
| M2 全量运行非绿色 | 保留原始 13 failures / 69 errors 记录；不把 67 个 worker 异常退出归类为环境问题或 M3 回归。M2 / OfficeCore 源码未改；依赖第二家公司的两项结果为本 CC 不适用。按本轮验收范围，`TEST-REG-001` 建议 PASS（范围化）。 |
| 未观察到真实混合工具 assistant 消息 | 通过确定性 mixed-message 自动化边界验收；HVR 明确记为未实际观察，不等待 Provider 随机生成。 |
| 未捕获独立显式接收者 UI 事件 | 当前 `_notify_thread` 默认及显式 `partner_ids` 边界已有自动化验证，真实 HVR 覆盖默认路径；未扩展到未使用的 subscriber 组合。 |
| 附件上下文回归为自动化而非真实 Provider 证据 | >100 消息和历史文件选择由 M3 自动化测试验证；本轮未再次调用真实 Provider，不能声称现场 Provider 做过该压力场景。 |

## 5. 当前状态与交接

核心实现、附件上下文回归、确定性 Silent Retrieval 边界及最终数据 / 生命周期 HVR 已完成。`TEST-REG-001` 范围化结论和保留的全量原始结果已提交关闭评审。**CC-M3-03 尚待负责人批准关闭。** 冻结的 TDD v0.4、Plan v0.3 和 CC v0.2 均未修改。当前未提交或推送；未合并、部署或发布。
