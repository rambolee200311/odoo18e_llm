# ATR — CC-M3-01 Retriever Enhancement

| 项目 | 记录 |
|---|---|
| 日期 | 2026-11-13 |
| 状态 | **验收通过；CC-M3-01 关闭评审 PASS** |
| 实施模块 | `office_engine_m3` `18.0.1.0.0` |
| 目标 Odoo 业务库 | `odoo18e_llm`；另有 Odoo CLI 系统库目录查询，见范围更正 |
| 基线 | M3 TDD v0.3、Implementation Plan v0.2、冻结 CC-M3-01 v0.2 |

## 实施内容

- 新增下游 addon `office_engine_m3`，依赖 M2；未修改 `odoo-llm` 或 M2 源码。
- 在现有唯一工具 `odoo_record_retriever` 上增加 `discover`、`describe`、`search`。省略 `operation` 时继续委托 M2 / 上游旧搜索实现并保持旧成功响应形状。
- `discover` / `describe` 直接读取运行时 Registry；不做模型 ACL、Record Rule、字段组检查，不读取业务记录，也不使用 `sudo()`。
- 显式 `search` 走当前用户 ORM，支持分页、默认 ID 升序、显式排序 ID tie-breaker、`in` / `not in` 标量数组及稳定错误码。
- `ACCESS_DENIED` 保持 Odoo `AccessError` 异常语义；Retriever 工具错误消息增加 `error_code` 和 `diagnostic_id`，不暴露内部查询异常文本。

主要代码：

- `office_engine/office_engine_m3/models/llm_tool.py`
- `office_engine/office_engine_m3/models/mail_message.py`
- `office_engine/office_engine_m3/models/retriever_errors.py`
- `office_engine/office_engine_m3/tests/test_retriever.py`

## 验证结果

面向业务数据和模块状态的 Odoo 命令都显式指定 `-d odoo18e_llm --no-database-list`。只读 Odoo shell 在测试前确认该库存在；测试后再次确认 M3 模块状态为 `installed/18.0.1.0.0`，现有 Retriever Schema 暴露 `discover,describe,search`。本次 Provider 验收也通过直接 Registry 的 Odoo shell 连接该目标库，未执行模块升级 / 初始化。

**数据库范围更正：** Odoo CLI 的 `--init/--update` 启动路径会在处理 `-d` 数据库前调用 `db_connect('postgres')` 并查询 `pg_database`，即使设置了 `--no-database-list` 也是如此。测试启动时曾有一次沙箱连接失败；后续测试进程通过系统库确认指定的 `odoo18e_llm` 已存在，随后才连接并升级 / 测试该库，未执行 `CREATE DATABASE`。没有连接其他 Odoo 业务数据库，但这次目录查询不符合“字面上只访问 `odoo18e_llm`”的最严格边界。发现该行为后没有继续运行 Odoo CLI 测试命令；本记录如实保留此范围偏差。

| 验证项 | 结果 | 证据 |
|---|---|---|
| Python 语法与差异空白检查 | PASS | `venv/bin/python -m py_compile ...`；`git diff --check` |
| M3 TransactionCase | PASS | Odoo 汇总：`0 failed, 0 error(s) of 8 tests`；覆盖旧接口、Registry 权限隔离、关系 / Selection 元数据、`in` / `not in`、分页与稳定排序、错误分类及错误消息码 |
| Tool Execute + ORM Domain | PASS | 测试经实际 `llm.tool.execute()`；测试读写均使用 Odoo ORM 和 TransactionCase 合成记录 |
| M2 Retriever 回归文件 | PASS（选定文件） | `test_office_retriever_integration.py` 的 6 个测试方法均启动；`--test-file` 方式未输出失败标记，命令退出码为 0。它使用测试 Adapter，不是真实 Provider 验收 |
| 真实 OpenAI Provider Schema / Tool Calling | **PASS** | 指定配置 `OpenAI GPT-5.6 Luna` / `gpt-5.6-luna`；OpenAI 端点接受 Odoo `format_tools()` 生成的 Retriever Schema。三次成功请求覆盖 `in` 数组、`not in` 数组及普通标量 Domain，完整请求与调用参数见 Provider 证据 JSON |
| Provider 返回参数的真实 `llm.tool.execute()` | **PASS** | `in`、`not in` 通过显式 `search` 路径；标量请求由 Provider 合法省略可选 `operation`，按 CC 兼容路径执行 legacy search。三次查询均返回成功零结果 |
| Odoo UI / 真实 Agent / HVR | 不属于本 CC | 留待 CC-M3-03；本次未执行 |

### TEST-RET-004：真实 Provider 证据

使用配置的 `OpenAI GPT-5.6 Luna` Provider（服务 `openai`，模型 `gpt-5.6-luna`）。Provider 请求通过 Odoo `llm.provider.openai_chat()` 发送，并使用 `llm.provider.format_tools()` 生成的实际 Retriever Tool Schema；请求显式设置 `reasoning_effort="none"`，与 M2 GPT-5 工具调用路径一致。SDK 自动重试关闭。每个 Domain 额外包含 `id = 0`，只请求 `res.partner` 的 `id` 字段，避免返回业务记录；三次工具执行都在 Odoo 用户 ID 2 的 ORM 环境运行并返回零条记录。

| Provider 用例 | Request ID | Tool Call ID | Provider 参数 / 执行结果 |
|---|---|---|---|
| `in` 数组 | `req_c6439dfd3cb9456aa281e4c58946827a` | `call_V6RAddIgJxqQAggFE089fSEO` | Provider 返回 `name in ["__cc_m3_01_provider_in_a__", "__cc_m3_01_provider_in_b__"]`；`llm.tool.execute()` 返回 `status=success, count=0, returned_count=0` |
| `not in` 数组 | `req_6abdcf3fb5c34d339d35266927253fda` | `call_Eq4vAeJPJqlyvSNz4YGECHJ4` | Provider 返回 `name not in ["__cc_m3_01_provider_not_in__"]`；`llm.tool.execute()` 返回 `status=success, count=0, returned_count=0` |
| 普通标量条件 | `req_e0dc944e5cc74276af2ccc68e1d11aaf` | `call_c19pqBS9fgHnLetnwUaW6jIS` | Provider 返回 `id = 0` 并省略可选 `operation`；按冻结兼容契约走 legacy search，原参数经 `llm.tool.execute()` 返回 `records=[], count=0`，旧响应 shape 保留 |

`provider_tool_call_evidence_attempt03.json` 保存三次成功请求的完整消息、Odoo Provider Formatter 输出的 Tool Schema、API 返回的 tool call 参数、usage 与 ORM 执行结果。`provider_tool_call_evidence_attempt01.json` 和 `provider_tool_call_evidence_attempt02.json` 保留初始诊断请求。共保留 5 次 Provider 请求尝试：前两次均未带项目 GPT-5 路径要求的 `reasoning_effort="none"`，返回 HTTP 400 且未产生 tool call；第二次的脱敏错误明确指出该参数要求。核对 [`office_engine_m2/models/llm_thread.py`](../../../../office_engine_m2/models/llm_thread.py) 后修正探针调用参数，再以三次真实 Provider 请求通过全部用例。首个 Provider 失败不是数组 Schema 不兼容；没有修改 Retriever 生产代码。

标量用例首次被探针断言误判：Provider 省略了非必填的 `operation`，原 runner 却要求必须显式为 `search`。保留原始 Provider 响应后，将其原样交给 legacy search 并确认成功；runner 的当前版本接受此契约允许的旧调用形式。没有重发该标量 Provider 请求。

## 测试期间观察

- 最初的沙箱测试进程无法连接 `127.0.0.1:5555`，Odoo CLI 的空库检查在连接失败时退出，没有创建数据库。之后使用不会初始化数据库的只读 Odoo shell 确认 `odoo18e_llm` 已存在，再运行测试；Odoo CLI 启动过程仍通过 `postgres` 做了上述存在性目录查询。
- 测试进程第一次尝试绑定 `8091` 与现有服务冲突；后续使用操作系统分配的临时 HTTP 端口。最终 `http://127.0.0.1:8091/web/login` 返回 HTTP 200，原服务保持运行。
- Odoo 启动日志出现 `column.filter.field.info` 无表诊断；其模型在现有 `addons/column_reorder/models/column_filter.py` 声明 `_auto = False`，与 M3 Retriever 无关。M3 测试汇总仍为 0 failures / 0 errors。
- 当前开发库 filestore 在测试日志中出现缺失文件读取；M2 测试结束时 Odoo 记录 `filestore gc 10 checked, 10 removed`，日志没有列出这些文件对应的附件记录，故不推断其归属。未手工改动或修复 filestore。
- M3 测试日志中的 `ACCESS_DENIED` 与 `QUERY_FAILED` 记录来自权限拒绝和故障注入测试，均为预期分支。

## 门禁状态

- `TEST-RET-001` 至 `TEST-RET-005`：按本 ATR 记录的自动化、Tool Execute、ORM 与真实 Provider 证据通过；M2 Retriever 选定回归文件通过。
- CC-M3-01 完成定义与验收证据齐备，关闭评审结论 **PASS**；Odoo UI / 真实 Agent HVR 不属于本 CC，留待 CC-M3-03。
- 仅在现有 `odoo18e_llm` 安装了 M3 模块；提交范围限定为 M3 addon 与本 CC 证据，不包含其他未跟踪文件。
