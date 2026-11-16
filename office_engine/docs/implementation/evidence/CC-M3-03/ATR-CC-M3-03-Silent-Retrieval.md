<!--
模板来源：office_engine/docs/skill/odoo-project-workflow/references/templates/Coding/ATR模板.md
模板版本 / 状态：v1.0.0 Frozen
模板同步检查：PASS（2026-11-16；--repo-root office_engine）
-->

# ATR — CC-M3-03 静默检索与最终 HVR 验收测试记录

## 1. 执行信息

| 字段 | 值 |
|---|---|
| Intent ID | `CC-M3-03` |
| CC | [`CC-M3-03 v0.2`](../../CC-M3-03_静默检索与最终HVR_v0.2.md)，FROZEN WITH OPEN ITEMS |
| IHR | [`IHR-CC-M3-03-Silent-Retrieval.md`](IHR-CC-M3-03-Silent-Retrieval.md) |
| 模块 | `office_engine_m3` |
| 环境 | Odoo 18 开发环境；仅使用数据库 `odoo18e_llm` |
| 分支 / 基线 | `codex/cc-m3-01-provider-acceptance` / `48e25a52ec45938b2ff8a4c9e3ac32365317a5f7` |
| 执行状态 | 实施及核心 HVR 已完成；等待关闭评审 |
| 数据处理 | 创建并核验 148 个合成订单和 185 条明细，随后通过 ORM 清理；未使用生产数据 |
| 最近 M3 测试 | `test-run-006-attachment-context-regression.log`；42 项，0 failures，0 errors |

## 2. 验收测试结果

| 测试 ID | 结果 | 证据与限制 |
|---|---|---|
| `TEST-SILENT-001` | 成功纯 Retriever 路径 PASS | 真实 HVR 线程 677 中，6 条 Retriever 消息带有静默标记；Odoo UI 显示 Office 操作和最终回复，但未显示探索消息。见 `hvr_actual_trace_thread_677.json`、`silent_path_observations.md`。 |
| `TEST-SILENT-002` | PASS（确定性边界） | 自动化覆盖成功零结果仍为 success、工具失败会清除静默标记并恢复工具 / assistant 消息、错误和澄清 / final 消息保持可见；真实 HVR 验证 final 可见。无需让 Provider 随机生成 ACL 错误或澄清。未声称线程 677 实际发生过这些分支。 |
| `TEST-SILENT-003` | PASS（确定性边界） | 自动化直接构造含 Retriever 与 Office 的同一 assistant 消息，证明该消息不被静默；无需等待 Provider 随机生成 mixed tool call。真实 trace 中未观察到该场景。 |
| `TEST-SILENT-004` | PASS（当前路径边界） | 真实 UI HVR 及尝试 290 / 312 记录覆盖当前非流式路径首次 Bus 分发前的抑制；自动化覆盖 SSE `message_create/update` 过滤、Discuss 历史和 `_notify_thread` 默认及显式 `partner_ids` 入口。显式订阅由确定性方法边界测试证明，未声称捕获了独立真实订阅者 UI 事件；本轮不扩展到其他 subscriber 组合。 |
| `TEST-SILENT-005` | PASS（流式安全可见边界） | 自动化证明流式 Office 路径不打静默标记，因此不进入 Silent Retrieval 的消息过滤；本轮不要求 generator 续接成功、修复上游或提供流式静默。没有真实 UI 流式执行证据。 |
| `TEST-HVR-001` | PASS | 真实 Provider 和已登录 Odoo UI 完成自主发现、导出计划、Candidate、Accept、Finalize；最终附件及浏览器实际下载文件的内容字节和 SHA 均已独立核对。平台状态仍为 `PARTIALLY_VERIFIED`，已向用户披露，未将其改写。下载证据见 `browser_download_verification_v395.json`。 |
| `TEST-REG-001` | **PASS（范围化；本轮未发现回归）** | CC 范围内的 M2 定向 12 项、M3 42 项及真实 HVR Candidate → Accept → Finalize 均通过。M2 全量运行原始结果仍为 208 项中 13 failures / 69 errors，不能记为全量 PASS；67 个 OfficeCore worker pipe EOF 原因未明，不归类为环境问题或 M3 回归。依赖第二家公司的 1 项失败和 1 项 setup error 按本 CC 范围列为 N/A。详见 `test-run-005-m2-regression-status.md` 和 `test-run-007-targeted-m2-regression.log`。 |

### 2.1 附加回归：附件上下文与新建导出意图

以下是实施后的自动化回归，不修改冻结 CC 原测试矩阵，也不替代真实 Provider / UI HVR：

| 回归项 | 结果 | 证据 |
|---|---|---|
| 上传附件后追加 106 条用户消息，附件不在 LLM 最近 25 条历史内仍可定位；连续 Provider 参数构建均含引用 | PASS | `test-run-006-attachment-context-regression.log`、`附件上下文丢失调查与修复.md` |
| 用户明确提及历史附件文件名时，历史附件优先于最新附件 | PASS | 同上 |
| Silent Retrieval 消息仍进入后续 LLM 上下文 | PASS | 同上 |
| “整理成一个 Excel”的无附件 Odoo 导出请求绑定 M3 工具，并明确无需上传源文件 | PASS | 同上；未调用 Provider |

## 3. 自动化测试记录

| 项目 | 结果 |
|---|---|
| `ATR-RUN-004` 命令 | `./venv/bin/python odoo-bin -c odoo.conf -d odoo18e_llm --http-port=8093 --workers=0 --max-cron-threads=0 --stop-after-init -u office_engine_m3 --test-tags /office_engine_m3 --logfile=/tmp/cc_m3_03_exact_copy_tests.log --log-level=info` |
| 执行结果 | ATR-RUN-004 退出码 0；Odoo 测试结果：`0 failed, 0 error(s) of 38 tests`。追加 ATR-RUN-006 退出码 0；`0 failed, 0 error(s) of 42 tests`。 |
| `ATR-RUN-007` 命令 / 结果 | 临时 shim runner `/tmp/cc_m3_03_targeted_m2_runner.py` 使用测试标签 `/office_engine_m2:TestWorkbookVersionState,/office_engine_m2:TestNativeOfficeChatIntegration.test_fileless_xlsx_request_binds_route_b_tools_for_create_and_followup_turns`。退出码 0；`0 failed, 0 error(s) of 12 tests`。原始日志：`test-run-007-targeted-m2-regression.log`。 |
| 覆盖范围 | Retriever / Office 消息分类、Discuss 历史与 SSE 边界、M3 导出分页、关联数据收集、完整性核验、资源限制、Candidate 生命周期、Provider Schema、日期比较及源值照抄指令；ATR-RUN-006 另覆盖 100+ 用户消息后的附件引用、历史附件优先、静默消息上下文保留和中文无附件导出路由。ATR-RUN-007 覆盖 M2 版本状态类及 fileless Route B 工具绑定，共 12 项。 |
| M2 全量运行原始结果 | 常规 `/office_engine_m2` 发现流程因 `addons/auditlog/tests/common.py` 缺少 `SETATTR_SOURCES` 而中止。兼容 shim 后全量结果为 208 项中 13 failures / 69 errors；67 个 worker pipe EOF 原因未明，另有失败创建后的 `current` 不可用错误。第二家公司依赖的 1 项失败和 1 项 setup error 为本 CC 范围 N/A。该全量运行不记 PASS；`TEST-REG-001` 的范围化结论依据定向 12 项、M3 42 项和真实 HVR。原始日志已归档为 `test-run-005-m2-regression-normal-import.log` 和 `test-run-005-m2-regression-full-compat.log`。 |

## 4. HVR 证据摘要

| 项目 | 结果 |
|---|---|
| 真实 UI 线程 | `677`；Provider `OpenAI GPT-5.6 Luna`；模型 `gpt-5.6-luna` |
| Agent 规划 | 用户只提供自然语言业务需求。Agent 自行调用 `discover`、描述两个模型，再提交 `export_records` 计划；没有预先注入模型 / 字段 / Domain / 工具参数。 |
| Candidate / 最终状态 | 版本 `395`；状态 `finalized`；交付状态 `delivered`；用户显式确认消息“接受”；最终消息 `467369`；Candidate 与最终附件 ID 均为 `10278` |
| 工作簿 | `worlddepot_m3cc03_synthetic_acceptance_dcb17989be_outbound_orders.xlsx`；14,052 字节；工作表 `Outbound Orders`、`明细` |
| 最终附件独立核验 | PASS：148 个订单身份和请求字段值；185 条明细身份、产品与数量值；185 组父子关联；无遗漏、重复、额外、错值或错关联。 |
| 浏览器下载副本 | PASS：14,052 字节；可由 openpyxl 打开；与 Candidate 和最终附件 ORM 回读字节一致。详情见 `browser_download_verification_v395.json`。 |
| SHA-256 | Candidate、receipt 绑定输出、最终附件相同：`92d6c0ac972bf406eb220701a637d7b36668c3950821b6c61e2276f5b948a5ee` |
| 其他摘要 | 源数据快照 `28f5d21ca9890e242327ed667e325d209e9f6ff47993be5bf54afda1e96dde67`；源身份集合 `bee7f6482b3805997885faea731f77a6960b08f1d9cc596542ddfab68091af14`；handoff `4e14a703bcbf33d6b1513acc97399e70a3f1340e0872a218b8bbae9648682a42`；Provider 输入 `8765c9813e9a3917b518b7cdbd933dde62ed0215e44e5088e42f7b0e5d40bde6` |
| 合成数据清理 | PASS：按唯一标记删除项目、148 个订单、185 条明细、2 个产品模板、1 个类别及 1 个收件人；清理后搜索计数均为 0。 |

详见 [`HVR-M3-03-001.md`](HVR-M3-03-001.md)、`hvr_actual_trace_thread_677.json`、`hvr_agent_plan_thread_677.json`、`workbook_verification_v395.json`、`browser_download_verification_v395.json`、`fixture_verification.json`、`fixture_cleanup.json` 和 Candidate / 最终附件 XLSX 证据文件。

## 5. 实施变更

- 新增下游 OpenAI 工具格式化，使现有 Office 工具向 Provider 暴露有效 M3 Schema。
- 增加通用模型发现、关联表规划及 Route B `export_records` 指引。
- 增加持久静默标记、首次 Bus 通知抑制、Discuss 历史过滤、SSE 消息事件过滤和失败消息恢复可见；原消息及工具数据继续保留。
- 加强 Hosted CI handoff 指令，要求逐格照抄源值并重新打开工作簿校验。
- 为 Odoo `Date` 字段加入按日历日期比较的 XLSX 核验，并增加正反向测试。
- M3 下游附件上下文修复：完整扫描 Thread 的有效附件关系，为每次 Provider 参数构建加入文本引用；显式历史文件名优先；为中文“整理成 Excel”补足 fileless 路由及无需上传指引。详情见 `附件上下文丢失调查与修复.md`。

## 6. 范围化结论及保留事项

`TEST-REG-001` 建议 **PASS（范围化；本轮未发现回归）**。依据为 M2 定向 12 项、M3 全套 42 项、最终真实 HVR 与变更范围审查。依赖第二公司的 1 项失败和 1 项 setup error 列为本 CC 不适用，不要求新增公司 fixture。全量 M2 测试原始结果继续保留为 13 failures / 69 errors；67 个 worker EOF 原因未明，另有跟随失败创建的 `current` 不可用错误。不得把全量结果写成 PASS，也不得把原因不明的 worker 错误称为环境问题。该全量结果未能证明本轮引入了回归；M2 / OfficeCore 均未被本 CC 修改。

确定性 Silent Retrieval 边界 `TEST-SILENT-002`–`005` 已按当前实现路径自动化验收，不依赖 Provider 随机产生特定 tool-call 形态。

## 7. 交接状态

实施和 HVR 证据已整理，`TEST-REG-001` 范围化结论及原始全量结果已提交关闭评审。CC-M3-03 **仍待负责人批准关闭**。未提交或推送；冻结 CC 要求在关闭评审通过后再提交本 CC 成果。任务启动的临时服务已停止。
