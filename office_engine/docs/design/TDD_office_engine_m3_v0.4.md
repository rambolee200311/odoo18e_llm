<!--
Template source: office_engine/docs/skill/odoo-project-workflow/references/templates/Designing/TDD模板.md
Template version/status: v1.0.0 Frozen; template-sync check: PASS (2026-11-13)
Engineering-guideline sync check: PASS (reviewed against docs/AGENTS.md and project workflow skill, 2026-11-13)
Frozen v0.4 baseline with open implementation gates. Approval is recorded as `TDD-M3-003`; see `docs/implementation/AUTHORIZATION_RECORDS.md`.
-->

# Office Engine M3 技术详细设计 v0.4

| 项目 | 内容 |
|---|---|
| 文档编号 | TDD-OFFICE-ENGINE-M3 |
| 版本 | v0.4 |
| 状态 | **FROZEN WITH OPEN ITEMS — 冻结设计基线；未授权实施** |
| 项目 | `odoo18e_llm` / `office_engine` |
| 编写日期 | 2026-11-13 |
| 技术负责人 | 项目负责人（授权记录：`TDD-M3-003`） |
| 上游业务基线 | M2 SRS v1.1.0 Frozen，仅作为 M2 兼容约束；M3 专属 SRS 已由负责人裁定 N/A（`DECISION-M3-SRS-NA-001`） |
| 上游技术基线 | M2 TDD v2.1.0 Frozen，连同有效的 v2.1.1 工具边界修订、v2.1.2 CC-09 as-built amendment；详见 §0.2 |
| 技术验证输入 | M2 Route B/Hosted Code Interpreter 实际代码与既有 TV、Registry Discovery TV、Silent Retrieval TV、Retriever 查询能力只读检查；状态和限制见 §0.2 |

> 负责人于 2026-11-13 批准本 v0.4 冻结并登记为 `TDD-M3-003`。v0.3（`TDD-M3-002`）原文保留为历史基线；本 v0.4 是当前设计基线。冻结时 OPEN-01b/02/03/04/06 的未决证据按授权登记保持原始状态，不代表通过，也不解除实施门禁；本 TDD 冻结不授权编码、Provider 调用、数据库操作或发布。

Freeze disposition: `FROZEN WITH OPEN ITEMS`; authorization register: `docs/implementation/AUTHORIZATION_RECORDS.md`; records: `TDD-M3-003` plus the six `EXEMPTION-TDD-M3-V04-*` items cited in §20.

---

## 0 文档说明

### 0.1 文档定位

本 TDD 定义 M3 的技术架构、工具契约、数据收集与交接完整性、Office 文件生命周期、消息可见性、安全、验证和后续实施边界。LLM 负责自然语言查询意图理解、模型 / 字段选择、关联范围确定及输出计划；本地 Collector 仅执行已确定且经当前用户权限校验的通用查询计划，完成确定性分页、批量收集和完整性检查，不实现业务规划器或模型专用规则。M3 保留 M2 Route B：LLM + Hosted Code Interpreter 负责 Excel 内容生成、复杂聚合和语义计算或修改；Odoo / Office Engine 确定性地负责权限、数据收集 / handoff、客观数据与文件 / 版本完整性、Candidate 及用户确认门禁。服务端不得取代模型生成工作簿内容，也不得实现本地报表或复杂计算引擎。

本 TDD 不替代或改写既有 SRS。负责人于 2026-11-13 明确裁定 M3 是现有 Office Engine 的优化，M3 专属 SRS 不适用；该适用性决定记录于 `docs/implementation/AUTHORIZATION_RECORDS.md` 的 `DECISION-M3-SRS-NA-001`。M2 SRS 继续约束原有业务语义；本 TDD 定义本次优化的技术契约。

### 0.2 上游基线与证据

| 输入 | 当前状态 | 本稿采用方式 / 边界 |
|---|---|---|
| `docs/requirement/SRS_office_engine_m2_ai_mapping_v1.1.0.md` | Frozen v1.1.0；仅覆盖 M2 | Candidate、用户决策、数据刷新、预览新鲜度等既有语义继续适用；不能充当 M3 全量导出需求基线 |
| `docs/design/TDD_office_engine_m2_v2.1.0_LLM_Native.md` | Frozen | 保留唯一 `office` 生命周期入口、Retriever 分离、当前用户权限、Candidate/Accept/Reject/Finalize 与现有版本门 |
| `docs/design/TDD_office_engine_m2_v2.1.1_CC07_ToolBoundary_Amendment.md` | 已批准的工具边界修订 | 保留 `odoo_record_retriever` 与 `office` 两个现有公开工具；不得新增第三个公开工具 |
| `docs/design/TDD_office_engine_m2_v2.1.2_CC09_Fileless_Create_AsBuilt_Amendment.md` | Frozen as-built amendment | 原有无源 `office(action="create")` 直达 V1 的窄例外保持原状；M3 数据导出不继承该直达 V1 例外 |
| Registry Discovery TV | Draft 报告；3 个隔离用例通过；无真实 Provider 回合 | 下游继承、单工具 Schema / dispatch、`discover/describe/search` 扩展点可行；没有证明模型会自主选对操作。元数据可见范围已由负责人本轮明确：discover/describe 返回 Registry Schema，不按业务 ACL、Record Rules 或字段组过滤；实施证据仍待取得 |
| Silent Retrieval TV | **NOT VERIFIED（完整目标）** | GPT-5 Office 非流式的 Mock 工具回合验证了 SSE / Discuss 隐藏和审计保留；Odoo Bus 显式订阅路径未验证；流式工具调用续接未通过 |
| Retriever 查询能力只读检查 | 源码及现有测试审查；未运行本次测试 | 已有 1–500 单页 limit、offset、可选分页；默认不返回分页信息；空 order 不保证 ID 稳定排序；domain Schema 未表达 `in` 列表；错误只有通用 status/error |
| M3 专属 SRS / DDD | M3 SRS 经负责人裁定 N/A；未发现 M3 DDD | M2 SRS 继续约束既有业务语义；M3 为现有 Office Engine 的优化，M3 专属 SRS 不适用；本次设计未引入新业务领域聚合。授权与适用性记录见 `DECISION-M3-SRS-NA-001` |

M2 Route B 的实际文件能力核查：

| 路径 / 证据 | 当前能力 | 对 M3 的影响 |
|---|---|---|
| `odoo-llm/llm_openai/services/responses_adapter.py` 的 `ResponsesAdapter.execute()` | `edit` 可发送一份 XLSX `input_file` 与 `input_text`；`create` 不带输入 XLSX；启用 Hosted Code Interpreter，返回端要求恰好一个带 `container_file_citation` 的 XLSX 并下载真实字节，做 bounded ZIP/OOXML 检查、SHA 与结果分类 | 能保留 M2 的单工作簿输入 / XLSX 输出 Route B；当前 Adapter 没有通用 supplemental file 输入参数，也不接收多个文件 |
| `office_engine_m2/services/edit_orchestrator.py::_authorized_retriever_context()`、`_provider_instruction()`、`_fileless_creation_instruction()` | 从同 Thread / user turn 已成功的 Retriever tool messages 取结果，规范化为 JSON 文本嵌入 Responses `input_text`；受现有附件大小上限约束 | 已存在小数据 inline 路径；没有证明它可无损承载多页、大数据集或 Provider context 上限内完整消费 |
| `odoo/sql_db.py:254-296` | Odoo cursor 默认设置 PostgreSQL `REPEATABLE READ` 隔离级别 | 全部分页和关系 ORM 读取应由同一个 Odoo cursor / transaction 执行，以该事务读视图定义源集一致性；部署环境和实际调用边界仍须验证 |
| `TV_LLM_Native_Excel_Production.md` / M2 Route B TV | 简单 XLSX 的 Hosted Code Interpreter 输入→真实 XLSX 输出有实证；小型 Retriever 数据随 instruction 生成文件有有限实证 | 只证明小样本 / 简单工作簿；不证明 148 条、多页、任意交接载体或复杂工作簿完整性 |
| 交接载体结论 | **尚未选择 JSON、CSV、XLSX 或其他格式** | OPEN-01b 的实施前 Spike 只证明至少一种候选载体能经当前 Route B 到达并由 Hosted CI 读取；据此选载体。148 条、更大数据集及实际边界属于 CC-M3-02 实施验收，不要求在 Spike 前完成。M3 内部先定义格式无关 handoff contract。OPEN-01a（Domain Schema）三层兼容性属于已关闭 CC-M3-01 的验收证据 |

当前实现的主要扩展点（以下是基线定位，不代表 M3 已实施）：

| 能力 | 当前代码 / 测试位置 | M3 设计用途 |
|---|---|---|
| Retriever Tool Schema | `office_engine/office_engine_m2/models/llm_thread.py:835`；`odoo-llm/llm_tool/models/llm_tool.py:171` | 下游继承方法签名并扩展同一 Tool Schema；由真实 `.execute()` 校验测试覆盖 |
| Retriever ORM 查询与权限 | `odoo-llm/llm_tool/models/llm_tool_record_retriever.py:19` | `super()` 兼容旧 search；新版 search 与批量关系查询继续使用当前 ORM 权限上下文 |
| Tool 消息分发 | `odoo-llm/llm_tool/models/mail_message.py:226` | 复用现有 Tool 名称和执行链，不注册新工具 |
| Office Tool / Retriever 集成 | `office_engine/office_engine_m2/models/llm_thread.py:17`（Tool 名称集合）、`:663`（分发）；`office_engine/office_engine_m2/models/office_mapping_tools.py` | 扩展同一 Office 入口的 `export_records` action，并复用当前 Thread 已绑定 Retriever |
| Candidate / Version | `office_engine/office_engine_m2/services/workbook_version_service.py`；`office_engine/office_engine_m2/models/office_workbook_version.py` | 只在既有 Version / Candidate 门禁上绑定紧凑 receipt，不新增状态机 |
| Silent Retrieval 消息时序 | `odoo-llm/llm_thread/models/mail_message.py:258`；`odoo/addons/mail/models/mail_thread.py:2272` | `body_json` 当前在 `super().message_post()` 后写入，而通知可在返回前发出；下游分类必须提前 |
| M2 关联回归 | `office_engine/office_engine_m2/tests/test_office_retriever_integration.py`；`office_engine/office_engine_m2/tests/test_edit_orchestration.py` | 作为既有行为和 M2 生命周期回归入口；本轮未运行这些测试 |

### 0.3 本文回答与不回答的内容

| 本 TDD 回答 | 不在本稿内作出 |
|---|---|
| 下游扩展点、Schema、分页 / 关联 / 错误契约、全量数据交接、文件完整性与消息可见性方案 | 具体用户角色的业务授权；按 M2 既有 SRS / ACL 执行 |
| M2 Candidate、Current、Accept、Reject、Finalize 的 M3 接入方式 | 自然语言字段选择一定正确，或文件内容满足所有业务语义 |
| 只读 ORM 业务记录权限、限制、错误分类、资源上限策略 | 生产环境配置、真实 Provider 使用授权、具体上线 / 回滚执行命令 |
| 自动化测试与真实 Agent UI HVR 设计 | 本次执行 Provider、HVR、真实数据库读写、安装升级或发布 |

### 0.4 内容分类

| 类别 | 本稿用法 |
|---|---|
| ① 工程强制标准 | 不绕过 ACL / Record Rules / 字段权限；工具成功不等于文件完整；不完整文件不得标为完整结果；Candidate 未 Accept 不得推进 Current；静默不得删除审计或工具上下文 |
| ② 待基线化变量 | 当前部署 Python / PostgreSQL 精确版本、M3 总记录 / 关系行 / 字节预算、discover / describe 的分页上限、Odoo UI 验收环境和真实 Provider 配置 |
| ③ 项目决策 | 采用同步有界收集、只增加一个 `office` action、由 M2 Route B / Hosted CI 生成文件、以既有 `office.workbook.version` 存储紧凑完整性凭据；具体 TD 见附录 B |

所有待测假设、未选定上限和未验证路径均用 **OPEN / NOT VERIFIED** 标示。负责人已确定的元数据权限设计不再作为 OPEN 决策；相关实施测试仍按 NOT RUN 记录，不能写成通过。

### 0.5 冻结与变更规则

冻结版 v0.2、v0.3 均原样保留；v0.4 是当前有效技术基线，由 `TDD-M3-003` 冻结。Implementation Plan v0.3 已同步基线化；CC-M3-02 v0.2 已冻结，但 OPEN-01b/02/03/04 前置 Spike 未通过前不得实施，且仍需单独 Coding Authorization。任何改变 M2 已冻结业务语义或用户确认门禁的提案，仍须退回对应上游审批。

### 0.6 编号规则

本 TDD 使用 `M3-REQ-*` 标识负责人提供的优化需求输入；因 M3 SRS 经批准判定 N/A，这些标识不是 SRS 编号。使用 `T-*` 标识实现门禁，`API-*` 标识工具 / 内部报文，`ERR-*` 标识错误，`TEST-*` 标识拟议验证，`TD-*` 标识项目设计决策。冻结后编号永久保留，不回收或重排。

### 0.7 规范措辞

“必须 / 不得”表示本 TDD 的实现硬门；“应”表示原则要求；“OPEN”表示证据或适用阶段门禁仍未关闭。已由负责人决定的设计事项不因实施证据尚未取得而继续标为设计 OPEN。FROZEN WITH OPEN ITEMS 不等于测试通过；实施范围仍由各 CC 单独授权。

### 0.8 单一事实来源（SSOT）

| 事实 | 唯一定义章节 |
|---|---|
| Registry / Retriever JSON 与 Schema | §5 |
| 数据发现、收集、Route B 内容生成、完整性核验及 Candidate 流程 | §6 |
| 版本和导出技术状态 | §9 |
| 并发和数据变化边界 | §10 |
| 错误码 | §11 |
| ACL / Bus / 静默边界 | §12 |
| Candidate 数据完整性凭据 | §3、§5.2、§6、§15 |
| 实施门禁 | §18 |

---

## 1 技术上下文与基线

### 1.1 技术栈

| 层次 | 选型 | 版本 / 状态 | 说明 |
|---|---|---|---|
| Odoo / ORM | Odoo | 18.0（项目基线） | Registry 模型 / 字段定义及 ORM `search_read/search_count`；元数据不走业务记录读取 |
| 语言 | Python | 实施记录中的 Odoo 18 环境为 Python 3.11.9；当前运行实例未核验 | CC-05 记录不能替代 M3 部署环境核对 |
| 数据库 | PostgreSQL | 当前具体版本未核验 | 业务数据只经 ORM；不定义自建 SQL 查询 |
| 文件内容生成 | M2 Route B：Responses API + Hosted Code Interpreter | 已有真实小型 XLSX 输入 / 输出证据；多页大数据交接未验证 | LLM + Hosted Code Interpreter 生成或修改工作簿；本地不写入或修补 Excel 内容 |
| 文件核验 | 现有 Adapter ZIP/OOXML 检查、Candidate Validator / `office_verify` | 已实现；适用特性与规模受各自验证证据限制 | 只核验安全、字节、结构及任务声明的可判定完整性；不承担内容生成 |
| Agent / 消息 | 现有 `odoo-llm` + M2 `office` | 保持兼容 | M3 只在下游 addon 继承 / 扩展 |
| 队列 / 缓存 | 首版不引入 | 同步有界操作 | 超限时失败或请求用户重新确定范围；不静默截断，不新增 Partial Candidate 机制 |

### 1.2 模块依赖与扩展关系

拟新增 `office_engine_m3` Odoo addon，依赖 `office_engine_m2` 及其既有依赖；只扩展下游 `llm.tool`、既有 `office` action、`mail.message` 与 `office.workbook.version`，并复用 M2 Responses Adapter / Hosted Code Interpreter 内容生成能力。不注册公开 Registry / Batch Query Tool，不新增报表生成器或第二套 Candidate / Current / Version 服务。

M2 Responses Adapter 目前只接受 `input_xlsx` 与 instruction，不能接收额外数据文件。M3 的格式无关 handoff contract 应通过既有 Route B 单一 Responses 请求进入 Hosted Code Interpreter；隔离兼容 TV 先确定当前调用路径可用的载体与读取限制。下游是否可通过现有继承点扩展请求内容，须在 CC-M3-03 / CC-M3-04 前核实；若做不到，相关 CC 阻断并返回 TDD 版本化修订，不得复制一套 Adapter 或静默修改 `odoo-llm`。另需核对 addon 载入顺序及迁移路径。

### 1.3 非功能约束

| 项 | M3 TDD 设计 |
|---|---|
| 单页读取 | 复用 Retriever `limit` 1–500；自动 collector 每页最多 500 条 |
| 总量 / 字节 / 关系行 / 墙钟时间 | **OPEN-02**：实施前最小 Spike 证明至少存在可行的有界执行区间及测量方法；实施期基准测试再确定具体服务端限额，并覆盖限额内、临界与超限行为。未有具体限额前不得宣称支持无限或超限完整导出 |
| 全量完整性 | M3-REQ-03：服务端收齐所有页面 / 关系数据，并核对交接载体与任务适配的最终文件覆盖前不得声明完整 |
| 交接与 Provider | 仅将本任务最少授权数据通过获批 Route B 请求交给 Hosted Code Interpreter；工具上下文不承担多页数据传输 |
| UX 等待时间 | 在经验证的输入字节 / 条数 / token / wall-clock 预算内执行；超限失败或请求用户收窄范围，不截断并伪装完整 |
| 数据完整性 / 新鲜度 | 完整性由单次收集 receipt、交接 digest 和任务对应的输出校验说明；新鲜度记录采集时间与权限范围，不默认 Accept 前重查全部记录，见 §10 |

---

## 2 模块目录结构

```text
office_engine_m3/
├── __manifest__.py                 # 依赖 office_engine_m2；无新公开工具注册
├── models/
│   ├── llm_tool.py                 # 同一 odoo_record_retriever 操作扩展
│   ├── office_action.py            # 既有 office Tool 新增 export_records action
│   ├── mail_message.py             # 静默分类、历史过滤、失败消息恢复可见
│   └── office_workbook_version.py  # Candidate 完整性凭据的受控不可变字段
├── services/
│   ├── registry_metadata.py        # 内部 Registry discover / describe
│   ├── dataset_collector.py        # 执行已确定的通用计划：分页、关系批量收集与完整性校验；不做业务规划
│   ├── data_handoff.py             # 格式无关数据集契约、manifest / digest、传递核对
│   ├── route_b_dispatch.py         # 复用 Responses / Hosted Code Interpreter 内容生成链
│   ├── export_verification.py      # 仅做客观数据、文件、版本 / SHA 完整性核验，不实现报表或计算引擎
│   └── retriever_visibility.py     # SSE / Bus / Discuss 可见性判定
├── security/                       # 仅在版本凭据字段需要时最小 ACL 扩展
└── tests/                          # TransactionCase、消息链路、集成与 HVR 支撑
```

目录是建议结构，不要求为每个函数保留单独服务层。上述服务不是新的公开 Tool；`dataset_collector` / `data_handoff` 只负责读取、确定性序列化 / 传递校验，不写 Excel 内容、不缓存 Odoo 数据、不允许任意模型代码执行。`route_b_dispatch` 是 Route B 的最小交接扩展，不是独立报表引擎；必须优先复用 M2 Adapter 并先验证下游扩展点。

---

## 3 ORM 模型与持久化设计

### 3.1 模型映射

| 对象 | 现有 / 提议 ORM 模型 | M3 用途 |
|---|---|---|
| Agent 工具记录 | `llm.tool` | 继续复用既有唯一 `odoo_record_retriever` 和 `office`；不创建 Registry / Batch 工具记录 |
| Discuss 消息 | `mail.message` | 增加静默成功 Retriever 消息标记；原始消息和 `body_json` 不删除 |
| Candidate / Version | `office.workbook.version` | 在现有版本 lineage 上记录紧凑的 data-integrity receipt；Candidate/Current 状态机不另建 |
| 导出数据集 / handoff | 不新增持久化模型 | 所有页及交接载体仅在一次有界 `office` 调用中处理；仅把摘要 receipt 绑定 Candidate，不保留完整源数据副本 |

### 3.2 字段契约

| 模型.字段 | 类型 | 用途 | 约束 |
|---|---|---|---|
| `mail.message.llm_silent_retrieval` | Boolean, default false | 标记成功 Retriever 消息，只用于 Discuss / Bus / SSE 用户可见性 | 创建消息时分类；错误时必须清除标记并发布可见错误；不参与 LLM 上下文过滤 |
| `office.workbook.version.data_integrity_receipt_json` | Text, readonly, copy=False, nullable | Candidate 关联的源集 / handoff / 输出覆盖与新鲜度摘要 | 只能由既有版本服务受控写入；不含完整业务记录值；字段格式在 §5.2 固定 |

不新增数据集缓存表、Snapshot、CDC、业务模型字段或与具体订单 / 产品模型绑定的字段。为两字段提供兼容默认值；老版本记录默认 false / null，不回填虚构凭据。

### 3.3 方法契约

| 方法 / 边界 | 行为 | 事务 / 权限 |
|---|---|---|
| 继承 `llm.tool.odoo_record_retriever_execute()` | 按 `operation` 分发；无 operation 的既有 `search` 调 `super()` 并保留旧成功返回形状 | 当前 `env`，ORM 权限；不使用 `sudo()` |
| 内部 `_collect_export_dataset()` / `_build_handoff()` | 通过当前 Thread 已绑定 Retriever 的 `.execute()` 自动取页、分组关联，生成格式无关的 handoff manifest / payload，并逐字节校验传递输入 | 无独立 ACL 绕过；限额由可信服务端配置；传输格式待 TV 选择 |
| 既有 `office` 增加 `action="export_records"` | 解析新建或当前工作簿来源、执行完整采集 / handoff、调用 M2 Route B 生成实际 XLSX，再按任务验证契约登记 Candidate | 复用 M2 Session、Adapter、Candidate / Accept / Reject / Finalize；不本地生成 Excel |
| `mail.message.message_post/create/write` 可见性扩展 | 根据 `llm_role`、工具名、tool call id 和结果状态分类，不依据消息文字猜测 | 静默判定须发生在首次通知之前；错误需重新发布可见消息 |

---

## 4 数据约束与索引

M3 不新增 Odoo 业务记录，不新增唯一业务键或查询索引。`data_integrity_receipt_json` 随既有 version 记录存储，候选版本本身的 `version_uuid`、版本号、幂等键、request digest 和绑定约束继续由 M2 管理。

页内和页间记录唯一性由服务端使用 `(model, id)` 集合核验；One2many 明细用 `(relation_model, child_id)` 识别，关系完整性另以 `(parent_model, parent_id, child_model, child_id)` 对验证。重复 ID 不得静默去重后继续报完整：检测到重复即触发一致性错误；Dedup 只作为输出集合保护，重复事实必须导致失败 / 重取。

---

## 5 JSON / 报文 Schema

### 5.1 对外接口

不新增公开 Tool。对外仍为两个现有入口：`odoo_record_retriever` 与 `office`。M3 给 Retriever 加 operation 参数，给同一 `office` Tool 加一个 `export_records` action。

#### API-RET-001：`odoo_record_retriever`

方法签名的兼容语义：`operation` 默认 `null`。`operation` 未提供时表示既有调用，模型参数仍必需，执行原始 `search` 并保持原成功返回形状；显式 `operation="search"` 使用 M3 分页契约。Registry 操作允许省略 `model`。

| 参数 | 类型 / 约束 | 默认 / 说明 |
|---|---|---|
| `operation` | `null \| "search" \| "discover" \| "describe"` | `null` 代表旧 `search` 调用 |
| `model` | nullable string | `search` / `describe` 必须提供；`discover` 可省略 |
| `query` | nullable string, max 256 | `discover` 按技术名 / `_description` 子串匹配；不发起业务记录查询 |
| `domain` | Odoo Domain | `search` 使用；`in` / `not in` 的 value 可为 JSON 标量数组；支持 Odoo 标准叶子和前缀逻辑 token，具体 schema 见 §5.2 |
| `fields` | string array | `search` 指定业务字段；`describe` 可选指定要描述的字段子集 |
| `limit` | integer 1–500 | `search` 单页上限；`discover/describe` 的返回页上限按 §5.2 |
| `offset` | integer ≥ 0 | `search` 分页起点；`discover/describe` 元数据分页起点 |
| `order` | string ≤ 512 | 空值按 `id asc`；非空值经 ORM 校验并追加 ID tie-breaker |
| `include_pagination` | boolean | 旧调用默认 false；显式 `search` 默认为 true；internal collector 总是 true |

`discover` / `describe` 读取运行时 Odoo Registry 定义，向现有 Retriever 工具调用者提供模型与字段 Schema；这两种操作不检查当前用户的业务模型 ACL、Record Rules 或字段组，不读取业务记录，也不授予业务记录访问权。实现不得使用 `sudo()`。`search` 只读业务记录，并严格使用调用者当前 ORM 环境与权限。所有参数是不可信 Agent 输入。`operation` 缺失兼容只保证原有 `search` 请求；新增参数不得改变旧输入的业务数据授权语义。

#### API-OFFICE-EXPORT-001：既有 `office` Tool 的 `export_records` action

| 参数 | Schema / 语义 |
|---|---|
| `action` | 既有 `office` action 枚举新增 `export_records`；不得创建 `office_export` 等新 Tool |
| `workbook_source` | `"new"` 或 `"current"`；`current` 必须由服务端解析该用户 Thread / Session 的 Accepted Current 附件和 SHA，不能由 Agent 指定路径或 ID |
| `source_query` | `{model, domain, fields, order?}`；不接收 Agent 控制的 `offset` / `limit` 循环；服务端负责完整分页 |
| `collections` | 可选数组，每项 `{key, relation_field, relation_model, inverse_field?, fields, order?}`；服务端使用 Registry 元数据校验关系类型 / comodel / inverse，并按父 ID 批量收集 |
| `tables` | 非空数组，每项 `{name, source: "root" \| collection_key, columns:[{label, source_field}]}`；作为给 LLM/Hosted CI 的内容要求及核验映射，不是本地 writer 指令；不含 Excel 坐标、模板路径或业务模型分支 |
| `verification_profile` | Agent 已确定的任务类别：`record_projection`、`grouped_aggregate`、`semantic_transform`；用于安排 Hosted CI 的内容规划与本地客观数据 / 文件 / 版本完整性检查，不是本地聚合或语义计算指令；不定义工作簿布局 |

LLM / Agent 从当前用户消息理解任务，并确定模型、字段、关系范围、表格内容及 `verification_profile`；Office 服务端校验该通用计划的 Schema、Registry 关系和调用者权限后执行，不负责替 Agent 推断业务模型、字段或输出规划。`verification_profile` 不改变用户意图，不自动授权全量读取或 Provider 外发，也不触发本地业务计算。缺字段、非法关系、未授权字段、交接不完整或超限时失败；M3 首版不创建 Partial Candidate。

### 5.2 Schema 与成功响应

#### Domain JSON Schema 语义

```json
{
  "type": "array",
  "description": "Odoo 标准 domain：叶子条件、隐式 AND，以及 |、&、! 前缀逻辑 token",
  "items": {
    "oneOf": [
      {"type": "string", "enum": ["|", "&", "!"]},
      {
        "type": "array",
        "minItems": 3,
        "maxItems": 3,
        "prefixItems": [
          {"type": "string"},
          {"type": "string"},
          {
            "oneOf": [
              {"type": ["string", "integer", "number", "boolean", "null"]},
              {"type": "array", "items": {"type": ["string", "integer", "number", "boolean", "null"]}, "maxItems": 1000}
            ]
          }
        ]
      }
    ]
  }
}
```

`in` / `not in` 必须使用数组值；其他 operator 的实际合法性由 Odoo ORM 最终校验。M3 不自创 domain 语言、不执行 SQL。Domain 中列表最大长度暂定 1000；须在实施计划按 Provider 工具 Schema / Odoo 环境确认。

该 Schema 当前只是 TDD 候选契约。必须分别验证：Odoo 生成的工具 Schema 能被当前 Provider 接受；实际 `llm.tool.execute()` 能校验 / 分发嵌套数组；Retriever 传入 Odoo ORM 后按 Domain 语义返回授权结果。未完成三个边界的集成验证前，不把 `in` list 能力标为端到端 VERIFIED。

#### Registry `discover` 响应

```json
{
  "status": "success",
  "operation": "discover",
  "query": "outbound",
  "models": [
    {"model": "world.depot.outbound.order", "description": "Outbound Order", "rec_name": "billno"}
  ],
  "count": 1,
  "offset": 0,
  "limit": 100,
  "returned_count": 1,
  "has_more": false,
  "next_offset": null
}
```

匹配范围严格为当前数据库运行 Registry 中的 `_name` 与 `_description`；排序按技术模型名稳定排序。所有现有 Retriever 工具调用者均可通过 `discover` 发现符合条件的模型；不按当前用户的业务模型 ACL、Record Rules 或字段组过滤。只读 Registry Schema，不查询模型业务记录，不使用 `sudo()`。发现结果分页以避免大型 Registry 响应无界。

#### Registry `describe` 响应

```json
{
  "status": "success",
  "operation": "describe",
  "model": "world.depot.outbound.order",
  "description": "Outbound Order",
  "rec_name": "billno",
  "fields": [
    {"name": "project", "label": "Project", "type": "many2one", "relation": "project.project"},
    {"name": "outbound_order_product_ids", "label": "Products", "type": "one2many", "relation": "world.depot.outbound.order.product", "inverse_field": "outbound_order_id"},
    {"name": "state", "label": "Status", "type": "selection", "selection": [{"value": "draft", "label": "Draft"}]}
  ],
  "count": 3,
  "offset": 0,
  "limit": 200,
  "returned_count": 3,
  "has_more": false,
  "next_offset": null
}
```

字段条目来自运行时 Registry 的字段定义，覆盖模型声明的全部字段，不按调用者的模型 ACL、Record Rules 或字段组做过滤。返回技术名、标签、类型、关联模型、One2many 反向字段及 Selection 定义；Selection 的 key 与 label 分开返回。静态 Selection 返回声明的选项；动态 Selection 只描述其动态定义，不为生成选项而调用可能读取业务记录的函数。Many2many 返回 comodel 与可得的 relation metadata，不伪造反向字段。默认 `describe` 分页 200 个字段，最大单页 500；用户可请求字段子集。直接读取 Registry 定义，不调用 `sudo()`；不得通过业务记录查询生成 Schema。

#### 新版 `search` 分页响应

完整响应示例（共 3 条、每页 2 条；数组长度与 `returned_count` 一致）：

```json
{"status":"success","operation":"search","records":[{"id":1,"billno":"OUT-001"},{"id":2,"billno":"OUT-002"}],"count":3,"offset":0,"limit":2,"returned_count":2,"has_more":true,"next_offset":2}
```

末页：

```json
{"status":"success","operation":"search","records":[{"id":3,"billno":"OUT-003"}],"count":3,"offset":2,"limit":2,"returned_count":1,"has_more":false,"next_offset":null}
```

148 条 / page size 100 的验收按同一契约收到 `100 + 48` 条；示例不用省略号伪装成合法 JSON。

`count` 始终是该用户、该公司上下文、该 domain 下 ORM 可见的匹配记录数；不是全库数。`returned_count = len(records)`。`next_offset = offset + returned_count` 仅在 `has_more=true` 时提供，否则为 null。空排序解析为 `id asc`；显式排序末尾追加 `id`（若排序中已经包含 ID 则不重复）。旧 operation 缺失时，成功响应仍保持旧 list 或 `{records,count,offset,limit,has_more}` 结构，不添加 M3 键。

#### API-HANDOFF-001：格式无关的数据交接对象

Office 内部 collector 输出 source dataset 与 handoff object。handoff object 的固定元数据包括 `schema_version`、`query_scope_digest`、`model`、`record_count`、有序 / 规范 identity digest、关系 pair 数与摘要、payload 字节数和 SHA-256。`payload` 是不透明字节 / 文件输入集合；`media_type`、文件数及序列化格式**由前置隔离 Hosted CI 兼容 TV 选定，本 TDD 不预设 JSON、CSV、XLSX 或其他格式**。

`Route B` 请求必须同时携带完整 handoff、（修改现有 workbook 时）M2 当前 Accepted Current XLSX 和用户任务指令。只有经 Responses / Hosted CI 真实验证可完整读取的 transport profile 才能启用；输入 Schema / 文件承载不兼容、record / byte / identity digest 不匹配或达到 provider 上限时，返回失败，不回退到 LLM 历史中的分页文本，不静默截断。M2 既有小数据 inline Retriever context 可继续服务普通 M2 路由，不作为 M3 全量导出的合格交接方式。

#### API-EXPORT-RECEIPT-001：Candidate 完整性摘要

```json
{
  "schema_version": "office.data-handoff-receipt.v3",
  "source": {"query_sha256":"<64 hex>","root_count":148,"collected_count":148,"identity_sha256":"<64 hex>","relation_pair_count":312,"relation_sha256":"<64 hex>"},
  "handoff": {"profile":"<verified transport profile>","payload_bytes":123456,"payload_sha256":"<64 hex>","record_count":148,"submitted":true},
  "workbook": {"profile":"record_projection","integrity_validation":"verified","task_computation":"provider_generated","semantic_verification":"not_independently_recomputed","expected_records":148,"matched_records":148,"missing":0,"duplicate":0},
  "collection_window": {"started_at":"<UTC>","completed_at":"<UTC>","source_view":"single_odoo_transaction","read_consistency":"repeatable_read"},
  "freshness": {"checked_at_collection":true,"requeried_before_accept":false},
  "output_sha256":"<64 hex>"
}
```

Receipt v3 只保存 query / 关系范围摘要、计数、身份 / 交接摘要、客观文件 / 数据完整性结果、任务计算执行方与独立验证状态、时间和输出 SHA；不得保存整份源数据、原始敏感 domain 值、密钥、Provider prompt 或完整业务记录。全部页面和关系查询须在同一 Odoo cursor / PostgreSQL `REPEATABLE READ` transaction 内执行；receipt 记录该 source view，但不持久化业务数据快照。数据完整性、文件完整性、任务语义验证等级和源数据新鲜度为不同事实；复杂聚合 / 语义计算由 LLM + Hosted CI 执行，本地不重算。不能独立验证语义时必须按 M2 既有 `PARTIALLY_VERIFIED` / 用户审阅语义记录，不得声称语义结果已独立证明。该事务读视图不代表 Accept 时最新。

### 5.3 错误响应契约

Tool 失败必须保留既有 `tool_execution.status="error"`，并增加稳定 `error_code`；不得以成功的空 `records` 表示失败。

```json
{
  "type": "tool_execution",
  "tool_name": "odoo_record_retriever",
  "status": "error",
  "error_code": "INVALID_QUERY",
  "error": "The requested domain is invalid.",
  "diagnostic_id": "<opaque correlation id>"
}
```

成功空结果是 `status="completed"` 加 `records=[]`、`count=0`；Record Rule 隐藏的记录不报错、不推断全库为空。内部 stack / ORM 细节进入受控日志，不回传给用户或 LLM。

---

## 6 领域行为与数据导出流程

### 6.1 组件职责与调用链

| 阶段 | 组件与行为 | 用户 / Agent 可见结果 |
|---|---|---|
| 业务理解 / 查询规划 | LLM 根据自然语言发现并选择模型、字段、关联范围、查询条件、输出表格 / 列及任务类型；信息不足时向用户澄清 | Agent 负责业务意图规划；不得推断全库权限或未授权字段 |
| Retriever / Collector | 同一公开 Retriever 提供 Registry / ORM 能力；Office Collector 只接收已确定的通用 query plan，并做 Schema / 权限校验、自动分页、关联批量收集、去重与完整性核对 | 不要求 LLM 记忆或拼接页数据；Collector 不替 Agent 选择模型、字段或业务关系；权限错误可见 |
| Data Handoff | Office Engine 从当前授权查询结果构造格式无关的 payload + manifest / digest，并通过 Route B 请求交接；物理文件格式须先经兼容 TV 决定 | Agent tool context 仅持任务计划和状态，不携带多页完整结果 |
| Route B | 既有 `office` action 把（可选）Current XLSX、完整数据 handoff 与任务指令送给 Responses / Hosted Code Interpreter；CI 生成 / 修改 Excel | 返回 Provider 真正产出的 XLSX 文件及请求 lineage |
| Candidate 核验 | 本地复用 Adapter 的字节 / ZIP / OOXML、源 / handoff 记录数与 identity / relation 覆盖、SHA / version binding 检查；不重写、不修补、不重算复杂聚合或语义 | 客观数据、文件及版本完整性满足要求后，按 M2 既有验证等级登记 Candidate；无法独立证明的计算结果如实标记 |
| 用户决策 | 复用 Candidate → Accept / Reject；保留 M2 Current、revision、owner / Thread / SHA 门禁 | Reject 不推进 Current；机器核验不替代用户接受 |
| Finalize | 复用 M2 Finalize 交付 Accepted Current 的精确字节 | 不重跑查询或改变内容；只在附件实际交付后报告成功 |

新建与修改均由 Route B 产出文件。M3 数据导出动作即使没有源工作簿，也必须登记为可审阅 Candidate 并经 Accept；不借用 CC-09 `office(action="create")` 的 fileless direct-V1 初始化例外。M2 普通 `create` 行为仍按其已冻结范围不变；现有文件的 Route B edit 仍以上一 Accept Current 的真实 XLSX 和 SHA 为输入。

### 6.2 自动分页与完整性算法

服务端收集器输入是 LLM / Agent 已确定、用户请求支持且由当前用户 ORM 再授权的通用 query plan；Collector 只校验计划结构 / Registry 关系并执行，不做模型、字段、关联或业务输出规划。数据外发授权与预算必须在传递前检查。每个 root / relation plan 独立执行以下步骤：

1. 规范化查询；缺省 `order` 为 `id asc`，显式排序追加唯一 ID tie-breaker；保留 root / relation 身份与用户选定字段。
2. 先取得当前权限下的总 `count`，再请求 `limit=min(configured_page_size,500)`、`offset=0`、`include_pagination=true`。
3. 每页验证 model / query scope / order / limit / offset / count 与响应形状；`returned_count == len(records)`。使用 ordered identity set 发现跨页重复、缺失、页内重复及异常终止。
4. 仅当 `has_more=true` 且 `returned_count>0`、`next_offset=offset+returned_count` 严格前进时继续；只有 `has_more=false` 才是 Retriever 分页终点。
5. 终止后检查收集总数与该次查询返回的可见 count、unique identities、所有 parent-child pairs 完全相符。任何 ACL 错误、关系缺项、count 变化或异常都失败关闭。
6. 全部 root / relation 页面必须使用当前用户的同一 `env`、cursor 和 transaction；Odoo 当前 `sql_db.Cursor` 默认 `REPEATABLE READ`，因此各页读取同一事务读视图。不得在页间 commit、切换 cursor 或拆成多个 Retriever HTTP / Provider 回合。以该一致读视图中的可见匹配集定义 source dataset；若目标部署或执行链不能保证单事务边界，则阻断完整导出，不以 count 相同推断无遗漏。
7. 不默认对全部记录执行第二次查询。Receipt 记录事务 source view、查询 scope、采集时间窗、可见 count、身份摘要与关系摘要；事务快照只用于本次收集一致性，不持久化，也不证明数据在 Accept 时仍为最新。
8. 从 collected dataset 生成格式无关的 handoff payload。序列化前后分别验证记录数、身份摘要、payload 字节数 / SHA 与 manifest；发现差异则不向 Provider 发送。
9. Route B Adapter 在同一获批 Responses 请求中传送完整 handoff、可选的 Current XLSX 及任务指令。请求前检查权限、Provider schema / input limits 和实际 payload digest；响应 indeterminate / timeout 不盲目重试。
10. Hosted Code Interpreter 生成或修改 XLSX，并执行复杂聚合 / 语义计算；本地仅检查真实输出字节、M2 文件安全验证、可客观核对的源 identity / field coverage、relation / count、SHA 与 version binding。不得实现本地报表、通用聚合重算或语义计算引擎。任何缺失 / 重复身份、记录行数不符或交接 / 文件完整性无法验证都不得标为完整。
11. 客观数据与文件完整性通过后，将真实 Hosted CI 返回字节、SHA 与 receipt 登记为 M2 Candidate。任务语义无法独立验证时，按 M2 既有 `PARTIALLY_VERIFIED` / 用户审阅语义记录；不创建新的 Partial Candidate 状态。所有 Candidate 均等用户 Accept，Finalize 只交付 Accepted Current。

新旧 `search` 调用兼容只影响单次返回形状；全量 export 强制走服务器端页循环和 handoff。LLM 负责 query / output plan，不负责分页、拼接多页数据、去重或判定终止条件。148 条每页 100 条必须得到 100 + 48 个 identity；逐行 projection 要对最终 XLSX 核对身份 / 目标字段，复杂聚合 / 语义由 LLM + Hosted CI 执行并保留其实际验证等级，不由本地代码重算。

### 6.3 关联批量查询

关联处理只支持用户明确选择的直接关系字段，第一版单跳，不递归展开任意图：

| Odoo 关系 | 批量策略 | 身份 / 分组规则 |
|---|---|---|
| Many2one | Root 页保留关系 ID；对所有不同的 related IDs 使用 `id in [...]` 批量读取被选字段，若 ID 集超过单个 Domain operand 上限则按有界 chunk 批量读取 | 每条 root 映射到其 Many2one ID；不以 display label 作为唯一键 |
| One2many | 从可见 Registry metadata 获取 relation model / inverse field；用 `inverse_field in parent_ids` 批量查子行 | 子行必须返回 inverse Many2one ID；按 parent ID 分组；子行本身继续遵守 ACL / Record Rules |
| Many2many | Root 读取关系 ID 集并去重；一次或有限分块查询 union related IDs；按各 parent 原始关系 ID 集恢复关联 | 一条 related 记录可链接多个 parent；保留所有 parent-child pair，不仅按 child ID 去重 |

所有业务读取仍复用 Retriever 当前用户 ORM。列表值只用于标准 Odoo `in` domain；不新增公开 Batch Query Tool、不复制 ORM ACL 逻辑。执行批量查询的 chunk 数必须受 §1.3 上限约束；超过上限失败并说明可重新收窄范围，不返回 Partial Candidate。

### 6.4 Route B 数据交接及 Candidate 判定伪代码

```python
def export_records(env, thread, message, query_plan, table_plan, workbook_source, verification_contract):
    session = require_current_owner_session(thread, message)
    plan = validate_against_retriever_schema_and_registry(query_plan, table_plan)
    require_external_data_export_permission(env.user, plan)
    dataset = collect_all_pages_via_bound_retriever(plan, max_page_size=500)
    handoff = serialize_using_tv_approved_transport(dataset)
    if not verify_handoff_manifest(dataset, handoff.manifest, handoff.bytes):
        return blocked("DATA_HANDOFF_INCOMPLETE")
    source_xlsx = resolve_accepted_current_if_requested(session, workbook_source)
    result = invoke_existing_route_b(
        source_xlsx=source_xlsx,
        handoff=handoff,
        user_instruction=message,
    )
    if not result.candidate_received or not valid_xlsx_bytes_and_sha(result):
        return failed_without_candidate("PROVIDER_FILE_UNAVAILABLE")
    verification = verify_candidate_against_contract(
        result.candidate_bytes, dataset, handoff.manifest, verification_contract
    )
    if not verification.acceptable:
        return failed_without_candidate("OUTPUT_INCOMPLETE")
    candidate = register_export_candidate_using_m2_version_service(
        env, session, result.candidate_bytes, source=source_xlsx,
        receipt=verification.receipt, provider_lineage=result.to_dict(),
    )
    return candidate_result(candidate, verification.receipt)
```

此伪代码只描述边界，不指定 handoff 编码或批准具体版本服务调用；实施前必须以隔离 TV 验证传输载体、Schema 和 Hosted CI 文件可见性。不得本地生成、补写或修复 XLSX 内容。新建 workbook 也进入 Candidate，不能使用 CC-09 的无源直达 V1 例外。

### 6.5 验证 profile、上限和失败关闭

- `record_projection`：用于逐项列出源记录。LLM 决定字段和输出规划；Hosted CI 生成工作簿。本地 verifier 可客观读取输出 identity 与用户要求保持的字段，核对每个 source identity 恰好出现一次、字段值按允许类型规范化后相等；不得使用固定 sheet / cell 坐标，也不得生成或修补内容。无法读取必要 identity / 字段时不标为数据完整。
- `grouped_aggregate`：LLM 规划分组与输出要求，Hosted CI 执行聚合计算并生成文件。本地只核对 source / handoff 完整性、文件字节 / 结构 / SHA、Candidate 版本绑定及可客观读取的交付元数据；不得运行通用聚合重算器。合成集成测试可用预先确定的 fixture expected constants 检查真实 Hosted CI 输出，但这些常量断言只用于测试，不形成运行时计算引擎。生产任务的聚合语义未独立核对时，沿用 M2 的 `PARTIALLY_VERIFIED` / 用户审阅语义；不得声称数学结果已由本地独立证明。
- `semantic_transform`：LLM 规划内容，Hosted CI 执行转换并生成文件。本地只核对数据 / handoff 来源完整、真实文件可读、结构 / 字节 / SHA 及版本绑定；不得实现语义判定器。自然语言语义不伪称已被机器证明，按 M2 既有 `PARTIALLY_VERIFIED` / 用户审阅语义处理。若用户明确要求独立机器证明且当前没有客观验证契约，则先澄清 / 说明能力边界，不得伪称满足。
- Receipt 分开记录 source / handoff completeness、objective workbook integrity、M2 task validation level 和 source freshness。文件可打开不等于源数据完整；源 / handoff 完整也不等于复杂聚合或语义正确。
- 资源预算未配置、输入字节或 Provider / Hosted CI 上限超出、页缺失、count / identity / relation 不一致、交接摘要不符、Provider 失败或文件 / 版本核验失败时，返回 BLOCKED / FAILED / INDETERMINATE，不创建完整 Candidate、不静默截断。可以请用户缩小条件后新建请求；首版没有独立 Partial Candidate / partial Accept 特殊流程。M2 既有 `PARTIALLY_VERIFIED` 是验证等级，不是 M3 部分数据 Candidate。

---

## 7 外部服务 Adapter

M3 保留 M2 Route B 和同一 Responses Adapter / Hosted Code Interpreter 工作簿内容生成路径。当前 Adapter 的 `input_xlsx` + `instruction` 接口没有通用 supplemental file 参数；M3 先通过隔离 TV 确定受支持的完整数据交接方式，再定义最小 Route B 输入扩展。完整 Odoo 数据集不经 LLM 对话上下文逐页记忆或拼接；Office Engine 确定性组包后在同一个获批 Route B 请求内传输，并在请求前校验 byte count、record count、identity digest 和 payload SHA。具体中间文件格式尚未选择。

| Adapter | M3 用途 | Timeout / Retry / Failure |
|---|---|---|
| 现有 Responses Adapter / Hosted Code Interpreter | 接收当前工作簿（可选）、获批数据 handoff、用户要求；由 LLM+CI 生成或修改 XLSX | 保留 M2 模型、timeout、重试、网络、cleanup 与输出文件语义；不得未授权调用 |
| Odoo ORM / Registry | 业务记录由当前用户 ORM 读取；Schema 元数据从运行时 Registry 读取 | 无外部网络调用；业务记录权限由 ORM 决定，Registry Schema 不做业务 ACL / Record Rule / 字段组筛选 |
| 本地 Office / Candidate Validator | data handoff completeness、真实输出字节 / SHA、现有文件安全检查及 task profile 的只读核验 | 不生成、改写或修补工作簿；失败不登记完整 Candidate |

不在 Odoo worker 执行 LLM 生成的 Python，不让 Hosted Code Interpreter 接触 Odoo 凭据、ORM、数据库或本地路径。M3 不新增文件生成引擎，也不改变 M2 通用 Route B 的新建 / 修改能力。

---

## 8 执行方式、Worker 与可靠投递

### 8.1 同步 / 异步评估

M3 采用同步、有界工具调用：完整收集、handoff 组包与核验、单次 Route B 请求和 Candidate 结果处理发生在一个 export action 中；全量结果不跨 Agent/Provider 对话轮次传递。无数据副本缓存或队列。此选择须按已验证输入规模、字节 / token / wall-clock 预算确认。

超出已测条数 / 关系行 / payload / token / 时间预算时立即失败或请用户收窄范围。不在失败后自动排队、悄悄截断或创建 Partial Candidate。若实测证明同步不能满足冻结 NFR，先修订 TDD 评估 Odoo 原生队列；本稿不预先引入。

### 8.2 Worker / Cron

不新增 Worker、Cron 或外部队列。M3 数据收集是只读；候选注册、Accept / Reject、Finalize 继续由现有 Office version service 管理。

### 8.3 可靠投递与幂等

Candidate 注册复用现有 version `idempotency_key` 与 `request_digest`；摘要必须覆盖 Thread / Session / user intent、query digest、字段、排序、关系计划、表计划和输入输出 SHA。重复 Tool call 可返回同一 Candidate 事实，不得生成重复 Current。Ambiguous Provider / 工具错误按 M2 status 处理，不盲目宣称已交付。

---

## 9 技术状态

业务流程状态沿用 M2；M3 只增加数据集验证事实，不将其混入 `office.workbook.version.state`。

| 数据与核验事实 | 条件 | Candidate / Current 影响 |
|---|---|---|
| Source collection | 当前用户同一 Odoo transaction read view 下的分页、identity 和关系数量核对完成 | 说明该事务读视图内所有可见匹配身份均已收集；不持久化 source snapshot，也不表示 Accept 时仍最新 |
| Handoff | 数据包 record count / identity digest / bytes / SHA 与 source dataset 一致，实际进入 Route B request | 不依赖 Agent memory；失败则不调用 Provider 或不继续登记 |
| Workbook task validation | 本地核验客观 identity / selected-field coverage、handoff、文件与版本完整性；聚合 / 语义由 LLM + Hosted CI 执行，不在生产运行时本地重算 | 结果是 `VERIFIED`、M2 `PARTIALLY_VERIFIED` 或 `FAILED`；不等价于 source completeness；无法独立验证的复杂计算如实使用 M2 审阅等级 |
| Blocked / Failed / Indeterminate | ACL、预算、handoff、Provider、文件或输出核验失败 | 不登记为完整 Candidate；Current 不变 |

`office.workbook.version.state` 继续使用 M2 的 Draft / Candidate / Accepted / Rejected / Finalized 实际映射，不新增另一套版本状态。技术收集状态记录在 receipt / result 中。

---

## 10 并发、事务与一致性

- Retriever 页和关系查询必须在一个 Office export 请求的同一个 Odoo `env.cr` transaction 中执行。项目当前 `odoo/sql_db.py` 为 cursor 设置 PostgreSQL `REPEATABLE READ`；实现与 HVR 必须确认查询没有跨 cursor / transaction、没有页间 commit，并验证目标环境保留该隔离语义。不锁业务源记录，也不修改 Odoo 业务记录。
- Query scope、count、排序、offset / `next_offset` 和 ordered identities 必须固定；以事务 read view 内匹配集作为本次 source dataset。count、身份及 parent-child relation 校验用于检测分页 / handoff 缺漏，不用“count 相同”替代单事务读视图保证。
- **数据完整性**指事务 read view 中当前用户 domain / 公司上下文的所有可见匹配身份均被收集、交接并按 task profile 验证；**新鲜度**指该 read view 在采集后、尤其 Accept 时是否仍代表最新源数据，二者分别记录。
- M3 不默认在 Accept 前重复查询全部记录。Receipt 记录 source transaction read view、采集开始 / 结束时间、用户 / 公司范围摘要、query digest、可见 count、身份及关系 digest。M2 的 workbook source version / SHA freshness checks 继续适用；这不等于 Odoo 业务源数据在 Accept 时 fresh。
- 用户显式要求“截至 Accept 时最新”或业务策略要求 freshness 时，通过新的用户授权查询刷新并创建新 Candidate；首版不得默默引入完整二次扫描、快照表或缓存。刷新结果仍需 Accept。
- Finalize 只交付已 Accept 的确切 Candidate/Current bytes，并按 M2 验证 SHA；Finalize 不再重新查 Odoo。
- OPEN-03：待验证当前部署与调用链是否保持单个 Odoo `REPEATABLE READ` transaction read view，并由 Implementation Plan / M3 HVR 确认 fresh-at-accept 任务语义；事务读视图不持久化，也不默认在 Accept 前再次查询全部记录。

### 10.2 事务与锁

数据读取、handoff 组包和 Route B Provider IO 期间不持有 Session / Version 行锁；分页 ORM 读取不可按页 commit。Candidate 登记前必须依据 M2 版本服务重新检查当前用户、Thread、Session revision、父版本和幂等键；Concurrent revision mismatch 时不注册旧结果。具体读事务与 Candidate 写事务如何衔接须沿用并验证现有 M2 request / version-service 边界，不能为了缩短事务而把数据分页拆到多个 read view。Accept 使用 M2 既有并发保护。

### 10.3 幂等

同一 Session、用户意图和相同规范化 query / table plan 的重复 export，以既有版本幂等约束判断是否复用 Candidate。数据 receipt / output SHA 不同则视为新鲜度变化，不能用旧 Candidate 覆盖或悄然复用。完整 idempotency key 字段策略沿用 M2，具体 digest canonicalization 在实施前测试冻结。

---

## 11 错误分类与告警

### 11.1 Retriever 错误码

| Error code | 触发 | Agent 处置 | 用户信息边界 |
|---|---|---|---|
| `MODEL_NOT_FOUND` | 当前 Registry 不存在该技术模型 | 可重新 `discover` / 澄清；禁止当作零结果 | 不提供 traceback |
| `FIELD_NOT_FOUND` | 请求的字段在模型定义中不存在 | 可重新 `describe` 并改正字段 | 不泄漏 SQL / 内部路径 |
| `ACCESS_DENIED` | `search` / 关联业务记录读取遭到 ORM 模型 ACL、字段访问、Record Rule 外的显式授权或公司上下文拒绝 | 不得改用 sudo 或报告无记录；必要时说明无权限 | 区别权限拒绝和零结果；不用于 `discover/describe` |
| `INVALID_QUERY` | 参数、domain 结构、operator、order、limit/offset 或字段组合不合法 | 可依据安全 message 修复 query | 脱敏具体敏感值 |
| `QUERY_FAILED` | ORM / Runtime 未归类异常或失败状态不确定 | 停止把它当成功；保留诊断 id | 用户只见可操作概述；内部日志保存受控异常 |
| `DATA_CHANGED_DURING_READ` | 分页期间可见 count / identity / relation 响应不一致 | 失败关闭，可重试或澄清 | 显示数据变化导致本次未能生成完整结果 |
| `DATA_HANDOFF_INCOMPLETE` | source receipt 与传输 payload 的 count / identity / bytes / SHA 不符 | 不调用 Provider 或阻断 Candidate | 显示数据交接完整性验证失败 |
| `INPUT_LIMIT_EXCEEDED` | 超过已批准的行、关系、payload、Provider token/bytes 或时间预算 | 请求用户缩小查询范围后新建请求 | 不生成 Partial Candidate |
| `OUTPUT_INCOMPLETE` | 文件缺失 / 不能读取，或客观可验证的记录身份、字段覆盖、关系、handoff、文件 / 版本完整性不通过 | 禁止按完整结果 Accept / Finalize | 报告实际核验项与失败类别；复杂计算未独立验证时沿用 M2 `PARTIALLY_VERIFIED` / 用户审阅语义，不伪称已证明 |

Registry `describe` 不按字段组隐藏字段；字段在 Registry 中存在即按 Schema 契约描述。`FIELD_NOT_FOUND` 仅用于 Registry 中不存在的字段。`ACCESS_DENIED` 用于 `search` 或关联业务读取实际遭到 ORM 权限拒绝的情形；错误分类不得把 Registry 元数据发现改成权限检查。

### 11.2 零结果与 Record Rule

成功查询零结果使用 success/completed、`records=[]`、`count=0`。ORM Record Rules 过滤行时 `records/count` 仅表示当前用户可见结果；不得用 Registry / 管理员环境补数，不得向 Agent / 用户泄露被过滤记录是否存在。权限不足与模型不存在分别走 `ACCESS_DENIED` / `MODEL_NOT_FOUND`，不得互报。

### 11.3 诊断与告警

每次请求按现有 `tool_call_id` / request id 关联日志；记录 model、operation、offset、limit、count、page result size、handoff profile / bytes / SHA、Response lineage、耗时、error code、diagnostic id 和 output SHA。不得记录完整 domain 值、全部 record payload、密钥或 Provider prompt。重复页、count drift、超限与完整性核验失败进入受控 error log；M3 不额外接入 APM。

---

## 12 安全与权限矩阵

| 动作 | 是否检查当前用户业务权限 | 数据来源 / 边界 | `sudo()` |
|---|---|---|---|
| `discover` 模型 Schema | 不检查业务模型 ACL、Record Rules 或字段组 | 运行时 Registry 的 `_name`、`_description`、`_rec_name`；不读取业务记录 | 禁止 |
| `describe` 字段 Schema | 不检查业务模型 ACL、Record Rules 或字段组 | 运行时 Registry 的全部字段定义、关系与 Selection 定义；不读取业务记录 | 禁止 |
| Retriever `search` | 必须检查并遵守调用者当前 ORM 的 model ACL、Record Rules、字段访问及公司上下文 | 通过 ORM 查询业务记录；Registry 描述不授予访问权 | 禁止 |
| Batch relation collection | 每次 related query 都走同一 Retriever / 当前 env | 关系 model / inverse 必须与 Registry 一致 | 禁止 |
| Office XLSX Candidate / Route B handoff | 仅传送当前用户 ORM 可读且本任务需要的数据；须通过现行外发授权；数据经当前 Route B 请求到 Hosted CI | handoff 不改变数据访问 ACL；候选文件由现有版本和附件服务检查 | 禁止 |
| Candidate / Accept / Reject / Finalize | M2 Thread、user、Session、revision、attachment 和 receipt 绑定保持 | 不适用 | 继续使用 M2 受控服务，不新增用户可直接写 version 的入口 |
| Silent Retrieval | 仅影响面向 Discuss 用户的消息投递与历史结果 | 不隐藏错误、澄清或 Office tool | 不适用 |

Registry Schema 对现有 Retriever 工具调用者可见，不代表业务数据可读。成功 `discover` / `describe` 不授予 `search` 权限；也不需要先检查当前用户的模型 ACL、Record Rules 或字段组。`search` 严格遵守当前用户 ORM 权限。全量 Odoo 数据将进入 Hosted CI，因此调用前必须满足 M2 既有外发授权及数据最小化要求；用户 Accept 不能补做 Provider 外发授权。

---

## 13 UI / 消息契约

### 13.1 Discuss 可见性边界

| 内容 / 事件 | 处理 |
|---|---|
| 成功的纯 Retriever assistant tool-call 消息 | Discuss / SSE 隐藏；保留原始 mail.message 和 LLM tool_calls 上下文 |
| 成功的 Retriever 参数、结果、requested / executing / completed 消息更新 | Discuss / SSE 隐藏；保留 `mail.message.body_json`、tool 状态、参数 / 结果和服务端诊断日志 |
| `tool_called/succeeded/failed` 内部事件 | 作为内部状态 / diagnostics 保留；现有 Store 对这些事件不渲染成聊天气泡 |
| Retriever error / failed tool result | 必须可见；如果初始 requested 消息被隐藏，失败时发出可创建可见消息的 SSE `message_create`，并从历史隐藏标记解除 |
| 最终 assistant 回答、必要澄清、普通错误说明 | 可见 |
| `office` tool、Candidate、Accept、Reject、Finalize、确认请求、用户确认 | 保持 M2 可见行为，不按 Retriever 规则过滤 |
| 混合 tool_calls assistant 消息 | 只要包含一个非 Retriever Tool，整条 assistant 消息可见；不得隐藏整条 assistant 消息；成功 Retriever result message 可单独隐藏 |

Silent Retrieval 不修改 `get_llm_messages()` 的现有历史范围；不删除 `mail.message`；不把成功工具记录从 Agent 下一轮上下文拿掉。分类依赖 `tool_name`、tool_call ID、状态和消息角色，不依赖模型自然语言文本。

### 13.2 SSE、Discuss 历史、Bus 通知

消息必须在 `message_post()` 通知前被分类。建议下游在原始 incoming `llm_role/body_json` 路径识别纯 Retriever assistant call 与 Retriever tool message，在记录创建阶段写入 `llm_silent_retrieval`，并在 Odoo `_notify_thread` / Bus recipient 路径抑制成功静默消息；不允许在 `message_post()` 返回后才补标志。

Discuss `_message_fetch()` 按标志过滤成功静默消息，LLM `get_llm_messages()` 不过滤。SSE 只抑制相应成功消息的 `message_create/update`；内部 tool events 仍保留。失败时解除标记并发布可见 create/update。Odoo 默认 / 显式订阅者的 Bus 通知都必须验证。TV 只验证了临时扩展的 SSE / history，显式 Bus fan-out 仍 **NOT VERIFIED**；本节是待实现和测试契约，不是通过声明。

### 13.3 GPT-5 与流式处理边界

- 已有 TV 在临时下游 addon、Mock tool calls 和真实 ORM 下验证了项目 GPT-5 Office 非流式路径：成功 Retriever assistant/tool 消息未进入 SSE / Discuss，mail.message、tool 参数 / 结果、LLM context、tool events、最终答案、error 与澄清保留；Candidate / Accept / Reject / Finalize 相关既有 4 项 ORM 测试通过。
- 该范围不是实际运行时路由核验，也不是真实 Provider / UI HVR，不验证 Bus 显式订阅；完整 Silent Retrieval 总结仍是 **NOT VERIFIED**。
- M2 普通流式分支已在 TV 发现 generator `yield from super()` 后未透传生成器 return value，导致 Provider assistant tool-call 未续接到工具执行。M3 不得宣称流式已通过。首版 Silent Retrieval 保证只覆盖经 M3 回归通过的 GPT-5 非流式 Office 路径；流式非 Office 路径继续可见，不做成功静默过滤，直到下游 return-value 透传和完整 SSE / UI 回归通过。不得修改上游 `odoo-llm`。
- 若 M3 评审要求所有流式模型也静默，该项先作为独立实施前置 CC / TV 关闭，再扩展保证范围；TV 失败不得靠隐藏 assistant call 掩盖。

---

## 14 测试设计

### 14.1 测试分层

| 层级 | 内容 | 工具 / 环境 |
|---|---|---|
| Schema / unit | Domain JSON Schema/provider serialization、operation 兼容、page loop 终止 / duplicate guard、handoff manifest 与 digest | Odoo unit / Python tests；不访问业务库 |
| Odoo ORM TransactionCase | Registry permission、当前用户 ACL / Record Rules / 字段限制、多个 page / 多个父子关系、Candidate version binding | 只使用现有开发数据库 `odoo18e_llm` 与 synthetic fixtures；事务回滚；不创建数据库、不访问生产 |
| Hosted CI handoff TV | 用项目实际 Responses Schema / SDK 与 Hosted CI 验证候选 file-input 方法、文件在容器内可见、整包 digest / record count / payload 大小及返回真实 XLSX | 只用 synthetic data；测试载体不得在 TV 前预先固定；Provider 独立授权；本次未执行；不创建数据库 |
| 消息集成 | `message_post` 时序、mail.message、LLM context、Discuss `_message_fetch`、SSE event 类型、Bus recipient、错误恢复可见 | 只使用现有开发数据库 `odoo18e_llm`；synthetic fixtures 与事务回滚 |
| Route B file integration | Hosted CI 真实输出候选；复用 M2 Candidate Validator / `office_verify`；客观核对 source identity / 字段覆盖、handoff、文件结构 / 字节 / SHA 与 receipt；复杂聚合 / 语义由 Hosted CI 计算 | Synthetic dataset；预先确定的 fixture 常量可验证测试输出；运行时不得实现本地聚合 / 语义计算器，也不得本地生成 / 修改 XLSX 内容 |
| M2 Regression | Candidate、Current、Accept、Reject、Finalize、version / confirmation / file security / old Retriever | M2 现存 TransactionCase 定向回归 |
| Real Agent UI HVR | 真实 Provider 与 Odoo UI，从自然语言到最终下载文件的完整链路 | 只用现有开发数据库 `odoo18e_llm` 与合成 / 明确授权数据；有效 Provider 外发授权及当前会话内置浏览器；本次未执行；不得创建数据库 |

### 14.2 追溯原则

每个 M3-REQ 与每个 TDD `T-*` 至少有一个可自动化的契约测试；真实 Agent 自主发现和用户可见消息行为另有 HVR。Mock Provider 不能证明自然语言模型会选对 query；Registry ORM 测试不能证明真实 Provider E2E；Candidate 文件存在不能证明 completeness；测试结论按实际层级分别报告。

### 14.3 测试矩阵

| TEST | 覆盖 | Given / When | Then |
|---|---|---|---|
| `TEST-RET-001` | Registry Schema / legacy compatibility | operation 缺失的旧 search 请求、显式 `discover/describe/search` | 旧成功 list / pagination shape 不变；新操作使用同一工具分发；未知 operation 是 INVALID_QUERY |
| `TEST-RET-002` | Registry Schema / 业务记录权限边界 | 无业务模型读 ACL 用户执行 discover / describe / search；模型含字段组受限字段 | discover / describe 返回 Registry 声明的全部模型与字段 Schema，不查询记录、不执行 ACL / Record Rule / 字段组过滤；search 由当前用户 ORM 权限允许或拒绝 |
| `TEST-RET-003` | 分页排序与输出 shape | 空 order、重复排序字段、limit=500 / 超界、offset | 空 order ID asc；显示 ID tie-breaker；1–500 正常、越界有 error；显式 search count/has_more/next_offset 正确；旧调用兼容 |
| `TEST-RET-004` | `in` Domain Schema 兼容性 | 对同一实际 schema 运行 Provider Schema、Tool `execute` 参数校验与 Odoo ORM Domain | 每层均接受标量和 list-valued `in`；ORM 结果遵守 ACL / Record Rules；这是 CC-M3-01 的实施验收条件，失败或未取得证据阻断 CC 验收，不作为编码前冻结门禁，也不以“本地 schema valid”推断 Provider 接受 |
| `TEST-RET-005` | 稳定错误 | unknown model、unknown field、search 请求中的 group-restricted field、bad domain/order、model ACL denied、Record Rule zero | 五个固定 code 覆盖；error 是 Tool status error；成功 zero 与 ACL / rule 语义可区别；不把 permission 当 model not found |
| `TEST-DATA-001` | 148 条端到端完整导出 | 148 条 synthetic root records、page size 100，经 Retriever→collector→handoff→Hosted CI→Candidate | 源 IDs=148；handoff parse / count / digest 与 source 一致；最终 workbook 的记录 identity 全量恰好一次且目标字段值匹配；无遗漏 / 重复；Candidate SHA / receipt 对应实际文件 |
| `TEST-DATA-002` | 更大多页数据 | 超过两页且处于实测预算内的合成集 | 同一机制完整传输；任何 payload / token / provider 限额均明确失败，不静默截断 |
| `TEST-DATA-003` | Parent-to-child batch | 多个 parent、有多条和零 child；关系 domain 用 `in` | 少量批次完成，无逐父 N+1；parent-child pairs 全量到 handoff，任务输出按 profile 验证 |
| `TEST-DATA-004` | Fail-closed | page exception、count drift、duplicate ID、missing inverse、handoff digest mismatch、Provider / output mismatch | 不创建完整 Candidate；Current / Last Valid / Document Revision 不变；诊断可追踪 |
| `TEST-DATA-005` | 资源超限 | root / relation rows、handoff bytes 或 Provider token/time 预算超限 | 失败并说明缩小范围；不产生 Partial Candidate、不截断后继续 |
| `TEST-DATA-006` | Transaction consistency and freshness | 用另一事务在分页期间提交 insert / update / delete；Accept 前不自动做第二遍完整查询 | 同一收集 transaction 的各页 / 关系仍对应一致 read view；receipt 记 source transaction read view；不称为 Accept 时最新；显式刷新创建新 Candidate |
| `TEST-XLSX-001` | Task-profile evidence and objective integrity | identity-preserving rows、Hosted CI aggregation、semantic transform，含重复值、null/false/0、Selection 和关联 | projection 客观核对全量 identity / 指定字段；Hosted CI 执行聚合 / 语义计算。测试可用预先确定的 fixture 常量断言已知输出；生产运行时不本地重算。不能独立验证的复杂计算使用 M2 `PARTIALLY_VERIFIED` / 用户审阅语义；文件、handoff、版本完整性仍须通过 |
| `TEST-LIFE-001` | Candidate lifecycle | 完整 export Candidate、Accept、Reject、Finalize | Candidate 之前 Current 未变；Accept 仅升级当前已核验 Candidate；Reject 不改 pointers；Finalize 交付同 SHA Accepted Current |
| `TEST-SILENT-001` | SSE / history / context | 多次成功 Retriever | Discuss 与 SSE 不出成功内部消息；原 mail.message、tool args/results/status、context、内部 tool events 保留 |
| `TEST-SILENT-002` | errors / clarifications | success 后 error、ACL failure、zero、assistant clarification | Error/clarification 可见；zero 不误报 error；失败消息不会继续静默 |
| `TEST-SILENT-003` | mixed calls | 同一 assistant message 包含 Retriever + Office Tool | 整条 assistant message 保持可见；只过滤成功 Retriever result |
| `TEST-SILENT-004` | Bus timing | 默认和显式订阅者，created / updated / failed message | 成功 silent 消息在首次 notify 前被阻止；错误转可见；无早发 Bus payload |
| `TEST-SILENT-005` | Streaming boundary | 流式 Tool call 与异常 generator return | 不得宣称已通过；在 generator return 透传修复和 SSE 回归前保持可见或明确不支持 silent |
| `TEST-HVR-001` | 真 Provider + Odoo UI | 自然语言只给业务名称；真实自定义模型；148 条 / 多 parent relation；点 Accept 后 Finalize | UI 实际工具卡 / 消息可见性正确；下载文件可重开；核对全量记录身份、数量、关系和 SHA；仅使用已授权的现有开发数据库 `odoo18e_llm`，不得创建数据库 |
| `TEST-REG-001` | M2 / old retriever regression | 旧 search schema、M1 mapping、Route B、versioning / security | 已有 M1/M2 tests 全部回归通过；不改变 M2 既有 Candidate、确认、版本、文件安全语义 |

`world.depot.outbound.order` 可作为隔离 fixture 的验收样例，检查 `billno`、`project`、`outbound_order_product_ids` 和 `outbound_order_id`；模型名仅出现在测试 fixture / assertions，不进入通用实现分支。M3 HVR 不得在生产库执行，也不得把 Registry TV 的 synthetic 记录发现当作实际 148 条数据证据。

---

## 15 可观测性与数据保留

保留既有 `mail.message`、Tool call/result、SSE 内部 tool events 和服务端诊断日志。静默仅改变 UI 投递，不删除或覆盖 `body_json`。每次完整导出把 §5.2 compact receipt 绑定到 Candidate version/output SHA，记录 source scope digest、根记录数、每个 relation 行数、handoff 摘要、profile 输出验证、耗时、完整状态及 `diagnostic_id`。

不保存整批业务记录副本作为缓存或 snapshot；不记录完整 payload / 私人 domain 常量到普通日志。Receipt 保存 source / handoff / output 的紧凑 digest、counts、profile、时间窗和 freshness 语义，继承 M2 版本历史保留策略；若当前存储策略不适配，Implementation Plan 再确认最小 schema migration。

---

## 16 部署、配置与升级

### 16.1 运行前置

| 前置 | 要求 |
|---|---|
| Odoo | 18.0；实际目标环境与 addons path 由 Implementation Plan 锁定 |
| 用户权限 | 当前用户已有的 model / field ACL、Record Rules 与公司上下文；不调整 ACL 来通过导出 |
| Agent Tools | 同一现有 `odoo_record_retriever` 与 `office` Tool 必须在对应 Thread 可用 |
| Provider | E2E 所用 Provider 只能在获得独立外发授权和负责人确认的开发环境范围后使用；本 TDD 冻结本身不授权 Provider 调用 |
| Runtime | 当前 Python / PostgreSQL 与 M2 `office_verify` 资源策略实施前核对；M3 不依赖本地 Excel Writer |

### 16.2 配置项

| 配置 | 默认 / 状态 | 生效 |
|---|---|---|
| `office_engine_m3.page_size` | 100；允许范围 1–500 | 每个新的 export action |
| `office_engine_m3.max_export_records` | **OPEN-02，须测量后给出有限正整数** | 每次 export；超过不截断 |
| `office_engine_m3.max_relation_rows` | **OPEN-02，须测量后给出有限正整数** | 每次 export 全 relation aggregate |
| `office_engine_m3.max_handoff_bytes` / `max_input_tokens` | **OPEN-02，需由 Provider / Hosted CI 实测** | 交接 payload 和完整 Responses request input |
| `office_engine_m3.max_output_bytes` | 复用现有 Adapter / Office ResourceBudget；若无可复用项则 OPEN-02 | Hosted CI XLSX Candidate 下载和验证 |
| `office_engine_m3.max_wall_seconds` | **OPEN-02，须按 Odoo runtime budget 给出** | 同步查询 / 单事务分页 / handoff / Provider 请求总预算 |

配置由管理员维护；模型参数不能提高上限。超过上限不生成 Partial Candidate，只失败或要求收窄用户查询。

### 16.3 数据迁移

升级新增 nullable Boolean / Text 字段，不改已有记录值和 version state；旧数据为 `llm_silent_retrieval=false`、receipt null。无全表回填、删除或业务行迁移。回滚代码后，新字段可保留为空字段；卸载是否移除列依 Odoo addon uninstall 语义与备份规则，实施 Plan 必须明确。不允许回滚时删除 M2 Candidate / Version / mail.message 历史。

---

## 17 技术风险与防护

| 风险 | 触发条件 | 防护 | 剩余限制 |
|---|---|---|---|
| 页循环未完成却报告完整 | Agent 停止分页、工具默认关闭 pagination | 全量导出仅由服务器 collector 循环；严格检查 has_more / offset / count | M3 上限数值需测试定标 |
| Route B 输入丢失或截断 | 现有 Adapter 没有通用 supplemental file 参数；inline instruction 有 token / 规模边界 | 先 TV 选择可读载体；handoff manifest 核查 byte / record / identity digests；Provider 输入超限即失败 | Hosted CI 对候选载体完整读取仍待验证 |
| Offset 期间数据增删 | collector 跨 cursor / transaction 或隔离级别不符合预期 | 单一 Odoo cursor `REPEATABLE READ` 执行所有 page / relation ORM 查询；核对目标环境与 HVR；不做二遍全量读取 | 事务读视图是本次 source consistency 边界，不代表 Accept 时最新；跨事务完整性不得宣称 |
| 长事务保留旧读视图 | 同步 Route B 请求在 ORM 收集后耗时较长 | 对查询至 Provider / Candidate 的总时长设有限预算，不持 Session / Version 行锁；不按页 commit 或切换 read view | `max_wall_seconds` 需包含实际事务生命周期，目标环境要实测 |
| Parent/child 漏关联 | 只查询 root 或按 name 关联 | `in` 批量查询 + direct ID pairs + handoff relation digest + profile 核验 | 仅第一版单跳关系；深层链延期 |
| Agent Schema 约束导致逐父 N+1 | domain value 不支持数组 | Schema 支持 `in`；collector 同一 export action 内 server-side batch | Provider / Tool Execute / ORM Schema 兼容须实测 |
| Permission/model confusion | 错误文字被 Agent 当成空结果 | 稳定 error_code + Tool status error；Record Rule 语义定义 | 文案 / locale 与错误分类要单独测试 |
| Registry 元数据可见范围 | 所有现有 Retriever 工具调用者均可发现 Registry 模型和字段结构 | 按负责人决策公开完整 Schema；不读取业务记录、不做业务权限过滤、不使用 `sudo()`；`search` 仍严格走当前用户 ORM | 元数据开放属于已决定的通用发现范围；不另设 OPEN-05 决策门禁 |
| Silent Bus 早到 | `message_post()` 通知发生在返回前 | create-time marker + `_notify_thread` 过滤，测默认 / 显式订阅 | TV 尚未验证 Bus fan-out |
| Streaming tool loop 被截断 | generator return 丢失 | M3 暂不对 streaming claim silent；先解决下游 return forwarding 并覆盖 | 不可修改上游；是否列 M3 实施范围待评审 |
| 文件内容由本地生成 | 在 M3 引入 deterministic XLSX writer | 全部 Excel 内容由 M2 Route B / LLM + Hosted CI 产出；本地只验证 | 不得在实现时回退成 local writer |
| 高内存 / 超时 | 全量采集、handoff、Provider request 无界 | 有界配置，超限失败或请求收窄，不截断、不使用 Partial Candidate | Provider bytes / token 与 Odoo wall-clock 数值待 TV |
| Freshness 与 completeness 混淆 | 将采集完整误作 Accept 时最新 | receipt 分开记录数据完整性和新鲜度；默认不二次查询 | 用户要求 fresh-at-accept 时需另行定义 refresh 流程 |

---

## 18 Implementation Guardrails / Coding Contract Baseline

| 编号 | 实现门禁 | 强度 / 验收 |
|---|---|---|
| `T-M3-SEC-001` | `discover/describe` 只读运行时 Registry Schema，不检查当前用户的业务 ACL、Record Rules 或字段组，也不查询业务记录；`search` 与关联业务读取严格遵守调用者当前 ORM 权限；禁止 `sudo()` | 必须；Schema 可见性与 ORM 业务读取分别验证 |
| `T-M3-RET-001` | 缺省排序 `id asc`；显式排序追加 ID；分页 count/has_more/next_offset 合法；旧 operation 缺失的成功 shape 兼容 | 必须；API tests |
| `T-M3-RET-002` | Domain Schema 经实际 `llm.tool.execute()` 接受 scalar 与 `in` 数组；只允许 Odoo 标准 domain | 必须；Schema + ORM tests，不能只直调 Python method |
| `T-M3-DATA-001` | 服务端页循环、identity / relation 收集和格式无关 handoff；不得依赖 Agent context 拼页 | 必须；148、多页、交接 digest / limit 测试 |
| `T-M3-DATA-002` | Hosted CI 真实产出 XLSX；本地只核对客观 identity / 字段、handoff、文件 / 版本完整性；复杂聚合 / 语义由 Hosted CI 计算，无法独立验证时沿用 M2 `PARTIALLY_VERIFIED` / 用户审阅语义 | 必须；真实 Provider / Hosted CI integration、固定 synthetic fixture 预期值断言及只读客观核验；不得增加运行时本地计算引擎 |
| `T-M3-DATA-003` | 页、关系、handoff、Provider input 或输出完整性失败时，不得作为完整 Candidate；资源超限不创建 Partial Candidate | 必须；失败注入及资源边界测试 |
| `T-M3-DATA-004` | freshness 与 completeness 分开；Accept 前不默认二次全量查询；Fresh-at-accept 必须显式 refresh | 必须；采集窗口 / refresh 语义测试 |
| `T-M3-VERSION-001` | M3 export 一律走既有 Candidate → Accept/Reject → Current → Finalize；不得使用 M2 fileless-create direct V1 例外绕过 | 必须；version tests |
| `T-M3-MSG-001` | 仅成功纯 Retriever 消息可静默；失败、澄清、final、Office、确认必须可见；保留持久记录和上下文 | 必须；SSE/history/mixed call tests |
| `T-M3-MSG-002` | 静默标记在 Bus notify 前生效；未通过 Bus tests 不得声称全链路静默 | 必须；默认与显式订阅测试 |
| `T-M3-MSG-003` | 流式路径未修复 generator 返回值 / 未回归前不承诺静默且不隐藏工具续接消息 | 必须；防止误报通过 |
| `T-M3-PRIV-001` | 仅在 M2 外发政策允许后将最少但完整的 handoff 发给 Hosted CI；完整 payload 不写日志或持久缓存 | 必须；代码审查和外发策略审查 |
| `T-M3-COMP-001` | M2 M1 / Route B / confirmation / version / security tests 在最终基线回归 | 必须；ATR 覆盖 |

本章定义上游实现门禁，不授权开始实现。各 CC 必须在已冻结 TDD 和已基线化 Implementation Plan 下裁剪条目。当前技术基线为 TDD v0.4 / Plan v0.3；CC-M3-02 已按 `CC-M3-02-001` 冻结，但未获得 Coding Authorization，且入口 Spike 仍未完成。

### 18.1 Implementation Plan / CC 边界

三个 CC 阶段边界沿用已冻结的 Plan v0.3。负责人已关闭 OPEN-05 的元数据范围设计决策；CC-M3-01 已单独关闭；CC-M3-02 已冻结但无实施授权；CC-M3-03 仍须单独评审与授权。OPEN-01a 的 Provider / Tool Execute / ORM 三层兼容验证已在 CC-M3-01 验收通过并记录 ATR；OPEN-01b/02/03/04 的最小前置 Spike 与实施验收分别见 §20。M3 SRS 已由负责人裁定 N/A，记录见 `DECISION-M3-SRS-NA-001`。任何验证若证明当前 Route B 无法通过允许的下游扩展承载完整 handoff，必须停止受影响 CC 并走 TDD 版本化修订。

| 阶段 | CC | 范围 / 前置 |
|---|---|---|
| 1 | `CC-M3-01 Retriever Enhancement` | Registry discover / describe / search、旧调用兼容、分页、稳定排序、`in` Domain、结构化错误及当前用户 ORM 业务权限；三层 Schema 集成测试已通过并记入 CC-M3-01 ATR |
| 2 | `CC-M3-02 Complete Data → Office` | LLM 确定业务查询 / 关系 / 输出计划；Collector 仅执行通用计划、分页、批量收集与完整性检查；Hosted CI 生成 Excel；本地做客观完整性核验并复用 M2 Candidate 生命周期。开始前完成 OPEN-01b/02/03/04 的最小技术可行性 Spike |
| 3 | `CC-M3-03 Silent Retrieval + Final HVR` | SSE / Discuss / Bus 静默处理、完整 Agent UI E2E、148 条记录验证及 M2 回归 |

技术冻结不要求预先指定实现、评审、测试人员或测试环境。CC-M3-01 只使用现有开发环境数据库 `odoo18e_llm`，不得新建数据库；实际执行测试前核实运行配置仍指向该库，测试使用合成数据并按 Odoo TransactionCase 回滚。

## 19 需求追溯矩阵

### 19.1 M3 请求输入 → TDD

| M3 优化需求输入 | 来源 | TDD 落地 | 状态 |
|---|---|---|---|
| `M3-REQ-01` 模型发现与字段关系说明 | 负责人指令；M3 SRS N/A 已批准 | API-RET-001、§5.2、`T-M3-SEC-001` | 元数据范围已决策；实施测试 Planned |
| `M3-REQ-02` 分页 / 排序 / batch `in` / 结构化错误 | 本轮负责人指令与 Retriever 只读检查 | §5.1–5.3、§6.2–6.3、`T-M3-RET-*` | Frozen with open items |
| `M3-REQ-03` 最终文件必须包含完整可交付匹配集 | 本轮负责人指令；M3 SRS N/A 由负责人批准 | §5.2、§6.2–6.5、API-EXPORT-RECEIPT-001、`T-M3-DATA-*` | Frozen with open items |
| `M3-REQ-04` Silent Retrieval 保留审计并处理 SSE / Discuss / Bus | 本轮负责人指令和 TV_Silent_Retrieval | §13、`T-M3-MSG-*` | Frozen with open items；Bus / streaming NOT VERIFIED |
| `M3-REQ-05` Candidate / Accept / Reject / Finalize 保持 | M2 Frozen TDD / SRS | §6.1、§9、§18 | 兼容约束 |
| `M3-REQ-06` 不新增工具、不改上游、不硬编码 WMS | 本轮负责人指令、Registry TV | §1.2、§2、§5、§18 | Frozen |

### 19.2 TDD → TEST

| 契约 | 测试覆盖 | 状态 |
|---|---|---|
| `T-M3-SEC-001` | `TEST-RET-002`, `TEST-RET-005`, `TEST-DATA-003` | Planned；尚无实施证据 |
| `T-M3-RET-001/002` | `TEST-RET-001`–`TEST-RET-005` | Planned |
| `T-M3-DATA-001/002/003/004` | `TEST-DATA-001`–`TEST-DATA-006`, `TEST-XLSX-001` | Planned |
| `T-M3-VERSION-001` | `TEST-LIFE-001`, `TEST-REG-001` | Planned |
| `T-M3-MSG-001/002/003` | `TEST-SILENT-001`–`TEST-SILENT-005` | Planned / existing TV gap disclosed |
| `T-M3-PRIV-001` | `TEST-HVR-001` + data-handling review | Planned; no Provider run in this task |
| `T-M3-COMP-001` | `TEST-REG-001` plus M2 selected regressions | Planned |

---

## 附录 A 术语表

| 术语 | 定义 |
|---|---|
| Full export / complete | 当前用户权限、已明确 query / 关系范围下，所有可见匹配 source identities 在实际 XLSX 中均有一份对应输出，且 receipt 核对通过 |
| Data Handoff | 本地 collector 所采集数据集到同一 Responses / Hosted CI 请求的完整传递；含数据计数、identity / relation digest 和 payload SHA，不等同于文件语义验证 |
| Registry metadata | Odoo 当前运行的 model / field description，不包含业务记录读取授权 |
| Data integrity receipt | 与 Candidate bytes SHA 绑定的计数、身份和关系验证摘要，不是整批数据 snapshot |
| Silent Retrieval | 只隐藏用户界面中的成功 Retriever 中间消息；不删除日志、消息或 LLM 工具上下文 |
| 父子身份 | `(parent_model,parent_id,child_model,child_id)`，不以显示名称或 Excel 行号为身份 |

---

## 附录 B 技术决策记录

| TD | 冻结决策 | 选择 / 备选 | 理由与待办 |
|---|---|---|---|
| `TD-001` | 复用现有 Retriever，新增 `operation` 可选参数 | 同工具扩展 / 新 Registry Tool | 选同工具扩展，兼容旧 `search`；Registry TV 已验证下游 Schema / dispatch 技术可行 |
| `TD-002` | Full export 页循环在 Office 服务端完成 | LLM page memory / local collector | 选 local collector；Agent 上下文不负责拼全量数据 |
| `TD-003` | Excel 内容继续由 M2 Route B / LLM + Hosted CI 生成或修改 | Hosted CI / local writer | 保留 M2 Route B；本地只承担 handoff、完整性和文件治理，不写内容 |
| `TD-004` | Handoff 内部 contract 与物理 payload format 分离 | 预选 JSON / CSV / XLSX / other | 暂不选格式；先通过 Hosted CI handoff compatibility TV，避免根据小样本或 API 想象定型 |
| `TD-005` | 首版同步、有界，不引入队列 / cache / snapshot model | Async / cache / snapshot / synchronous | 选 synchronous；总量与 wall-clock 上限需 benchmark；超限失败 / 收窄 |
| `TD-006` | receipt 持久化在现有 Candidate version | 新数据快照表 / mail message blob / version metadata | 只留 compact receipt，不留完整数据副本；字段 migration 最小化 |
| `TD-007` | Silent Retrieval mark 于消息首次 notify 前建立 | post-message 标记 / create-time 标记 | 选 create-time + Bus filter；TV 已证实 post-message 写 `body_json` 可能错过 Bus 时序 |
| `TD-008` | 首版静默范围遵循实际已验证路径 | 未验证 streaming 也视为通过 / 明示边界 | GPT-5 非流式仅是 isolated TV；Bus / real UI 未验证，streaming return-value 问题未解决，不写成整体通过 |
| `TD-009` | Registry Schema Discovery 的元数据权限范围 | 按业务 ACL / Record Rules / field groups 过滤 / 对所有现有 Retriever 调用者开放 Registry Schema | 采用后者：discover / describe 不读取业务记录、不核查当前用户业务权限、不使用 sudo；search 仍遵守当前用户 ORM。负责人于 2026-11-13 明确决定；实施验证由 TEST-RET-002 承担 |

---

## 附录 C 版本变更记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-13 | Draft | 首次整合 M2 Frozen 设计、Registry / Silent Retrieval TV 和 Retriever 查询能力检查；未冻结、未授权实施 |
| v0.2 | 2026-11-13 | FROZEN WITH OPEN ITEMS | 保留 M2 Route B；格式无关 handoff、任务类型验证与 freshness 区分；按负责人裁定 M3 SRS N/A；OPEN-01 至 OPEN-06 维持原状态并登记授权，不代表已验证或授权实施 |
| v0.3 | 2026-11-13 | FROZEN WITH OPEN ITEMS | 按负责人决策开放 Registry Schema Discovery 元数据范围；关闭 OPEN-05 设计决策门禁；将 OPEN-01 Domain Schema 三层兼容测试归为 CC-M3-01 实施验收，并把 Hosted CI handoff Spike 保留为 CC-M3-02 前置；同步三 CC 边界与现有开发数据库限制。记录 `TDD-M3-002` |
| v0.4 | 2026-11-13 | FROZEN WITH OPEN ITEMS | 明确 LLM 业务规划与通用 Collector 执行边界；将本地核验限定为客观数据 / 文件 / 版本完整性，复杂计算由 Hosted CI 执行；拆分 OPEN-01b/02/03/04 最小前置 Spike 与实施验收；仅使用既有 `odoo18e_llm` 测试环境。记录 `TDD-M3-003`；未决状态及门禁不变 |

---

## §20 门禁状态与后续证据（v0.4 冻结版）

本章区分设计决策和实施证据。v0.2、v0.3 及其授权记录保留为历史基线；v0.4 是当前冻结技术基线。已完成测试按既有 CC 证据记录；未执行测试保持 `NOT RUN / Missing`，不声称 Passed。只使用现有开发数据库 `odoo18e_llm`，不得新建数据库。

| ID | 事项 | v0.4 当前状态 | 关闭 / 验收条件及影响 |
|---|---|---|---|
| `OPEN-01a`（原 OPEN-01 Domain Schema facet） | Provider Tool Schema、实际 `llm.tool.execute()` 与 Odoo ORM 对标量及 `in` / `not in` 数组的兼容性 | **已通过并随 CC-M3-01 关闭；证据见其 ATR / Provider 记录** | 三层真实兼容性验证已完成；冻结设计要求仍作为回归约束保留。不能以本地 Schema 检查替代 Provider 证据 |
| `OPEN-01b`（原 OPEN-01 Hosted CI handoff facet） | 格式无关 handoff 是否可由现有 Responses 路径送达 Hosted CI 并读取 | **前置 Spike Missing；实施验收 NOT RUN**；`EXEMPTION-TDD-M3-V04-OPEN-01B-001` | **实施前最小 Spike：**只用合成 sentinel 验证至少一种候选载体经现有 Route B 到达且 Hosted CI 能读取，确定载体可行性；不要求预先证明 148 条 / 大数据完整性。**实施验收：**TEST-DATA-001/002 验证 148 条及更大有界数据集完整交接、实际读取、digest 与限额；只用既有 `odoo18e_llm` 开发库，不新建数据库。 |
| `OPEN-02` | root rows、relation rows、handoff bytes、Provider tokens 与 wall-clock 有界值 | **前置 Spike Missing；实施验收 NOT RUN**；冻结豁免 `EXEMPTION-TDD-M3-V04-OPEN-02-001`；历史 `EXEMPTION-TDD-M3-OPEN-02-001` 保留 | **实施前最小 Spike：**证明存在一个有界可行执行区间，并能采集行数 / 字节 / Provider 输入输出 / 耗时等测量信号；不在 Spike 中冻结生产上限。**实施验收：**实测并配置有限上限，覆盖限额内、临界与超限；超限失败或请用户收窄。 |
| `OPEN-03` | 所有分页与关系查询共用同一 `REPEATABLE READ` transaction，freshness 语义可接受 | **前置 Spike Missing；实施验收 NOT RUN**；冻结豁免 `EXEMPTION-TDD-M3-V04-OPEN-03-001`；历史 `EXEMPTION-TDD-M3-OPEN-03-001` 保留 | **实施前最小 Spike：**确认拟用 Odoo 调用边界能让多页读取沿用同一 cursor / transaction，且不按页 commit。**实施验收：**在现有 `odoo18e_llm` 中测试 root / relation 查询和并发变化下的 read view、freshness 记录与显式刷新；不默认重复全量查询。 |
| `OPEN-04` | 输出的客观数据 / 文件 / 版本完整性检查可行，复杂计算的验证等级清晰 | **前置 Spike Missing；实施验收 NOT RUN**；冻结豁免 `EXEMPTION-TDD-M3-V04-OPEN-04-001`；历史 `EXEMPTION-TDD-M3-OPEN-04-001` 保留 | **实施前最小 Spike：**确认现有 Candidate / 文件检查路径可核验输出文件与可客观读取的身份完整性；约定不可独立验证的复杂聚合 / 语义结果使用 M2 `PARTIALLY_VERIFIED` / 用户审阅语义，不声称独立证明。**实施验收：**projection identity / 字段，Hosted CI 真实输出，已知 fixture 聚合断言，文件 / SHA / 版本绑定均按测试矩阵验证；不实现本地聚合或语义计算器。 |
| `OPEN-05` | Registry 模型与字段 Schema 的公开范围 | **Closed — 负责人决策（本轮指令）**：所有现有 Retriever 工具调用者可发现 Registry Schema；不检查业务模型 ACL、Record Rules 或字段组；不读取业务记录、不使用 `sudo()`。`search` 仍严格遵守当前用户 ORM 权限 | 这是设计决策关闭，不代表 `TEST-RET-002` 已通过；`TEST-RET-002` 在 CC-M3-01 实施阶段验证并保留 ATR。无需在 CC-M3-01 前重复审批，不设元数据权限 OPEN 门禁 |
| `OPEN-06` | Silent Retrieval Bus 与流式路径能否从下游稳健满足 | **Mixed：Bus/UI Missing；stream continuation Failed**；冻结记录 `EXEMPTION-TDD-M3-V04-OPEN-06-BUS-001` / `EXEMPTION-TDD-M3-V04-OPEN-06-STREAM-001`；历史授权 `EXEMPTION-TDD-M3-OPEN-06-*` 保留 | CC-M3-03 验证 Bus、mixed calls 与 UI；未通过的路径保持可见，不宣称静默 |
| `OPEN-07` | M3 专属 SRS 是否适用 | **Closed — N/A**：负责人于 2026-11-13 裁定本期是现有 Office Engine 优化；`DECISION-M3-SRS-NA-001` | M2 SRS 继续约束既有业务语义 |

**门禁汇总（v0.4 冻结基线）：** OPEN-05 是已关闭的设计决策；OPEN-01a Provider / Tool Execute / ORM 验证属于 CC-M3-01 实施验收且已通过。OPEN-01b/02/03/04 各自拆为实施前最小技术可行性 Spike 与 CC-M3-02 实施验收：前者仅确认设计方向可行，不替代 148 条 / 更大数据集、资源边界、事务一致性、真实文件与 Candidate 完整性等最终验收。当前四项前置 Spike 均 Missing，其他未执行实施测试保持 NOT RUN；不得标记 Passed。TDD v0.4 / Plan v0.3 为当前冻结基线，CC-M3-02 虽已冻结但不得在 Spike 完成并取得独立 Coding Authorization 前开工。本次冻结不授权实施、Provider 调用或数据库操作。测试仅限既有开发数据库 `odoo18e_llm`，不得新建数据库。
