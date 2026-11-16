# CC-M3-02 — 自动化测试记录（ATR）

## 执行基线

| 项目 | 记录 |
|---|---|
| CC | CC-M3-02 v0.2（Frozen baseline；兼容性偏差见实施补充设计） |
| Coding Authorization | `CC-M3-02-002`；M2 Candidate 兼容及 Provider 集成授权补记为 `CC-M3-02-003` |
| TDD / Plan | M3 TDD v0.4 / Plan v0.3；兼容性说明见 [`TDD_office_engine_m3_v0.4_Implementation_Compatibility_Addendum_20261116.md`](../../../design/TDD_office_engine_m3_v0.4_Implementation_Compatibility_Addendum_20261116.md) |
| 模块版本 | `office_engine_m3` installed `18.0.2.0.0`；`data_integrity_receipt_json` 已注册，见 `module-version-check-20261116.txt` |
| 数据库边界 | 仅现有开发库 `odoo18e_llm`；未创建数据库、未访问其他数据库或生产环境 |
| 合成数据边界 | ORM/TransactionCase 合成数据，测试事务回滚；Provider 请求仅包含合成联系人数据 |
| Provider | `OpenAI GPT-5.6 Luna` / `gpt-5.6-luna`；一次性测试进程把输出 token 上限覆盖为 8192，未持久化修改 Odoo 配置 |
| Git | 未提交、未推送；未包含无关文件 |

## 测试覆盖及状态

| 测试 ID | 名称 | 状态 | 证据与边界 |
|---|---|---|---|
| `TEST-DATA-001` | 148 条跨页完整导出 | **PASS（真实 Provider + 生命周期）** | 148 条经 source→handoff→Hosted CI→XLSX；以同事务 ORM source 比对 identity / Name / Email 每行完全相等，输出 148/148 唯一身份；Candidate 前 Current 未变，Accept 后 Current revision=1，Finalize 与 Candidate SHA 相同。真实 Provider 证据见 `real-provider-148-helper-tolerant-lifecycle-summary.json`。 |
| `TEST-DATA-002` | 更大有界数据集 | **PASS（真实 Provider）** | 251 条三页 `100+100+51`；handoff 30,199 bytes，真实 Hosted CI 返还 251 行，所有 identity 与字段值逐行相等；Candidate 前 Current 未变。见 `real-provider-251-summary.json` / `real-provider-251-candidate.xlsx`。 |
| `TEST-DATA-003` | 多父直接关系批量读取 | **PASS（自动化）** | M2O、O2M、M2M 通过批量读取并保留 parent-child pairs；共享子记录映射到两个父记录，零 / 多明细皆覆盖；并对生成关系表的缺行及父子错配做核验。真实 148 / 251 根表任务没有请求关系集合。 |
| `TEST-DATA-004` | 故障关闭及状态不变 | **PASS（自动化）** | 覆盖分页失败 / count drift / 重复 ID、关系记录缺失、O2M inverse 指向集合外父记录、输出缺行 / 错配、错误字段、handoff digest 被篡改、Provider 无文件及 invalid XLSX。失败路径不创建可接受 Candidate、不推进 Current；相关用例见 `odoo-test-m3-export-final.result.txt`。 |
| `TEST-DATA-005` | 资源边界及超限失败 | **PASS（自动化 + 实测）** | root / relation / payload 精确阈值允许通过，超过阈值失败；已有一过界 Collector fail-closed 用例；原 ResponsesAdapter 的输入超限、输出字节超限、Provider timeout 三项离线断言通过。真实 Provider 148 / 251 总耗时分别 24.660s / 28.000s，均低于配置 120s。 |
| `TEST-DATA-006` | 同一读视图及 freshness | **PASS（隔离事务）** | 另一 ORM cursor 提交并发 insert/update/delete 后，原 collector transaction 仍看到初始 3 个 identity 及原字段值；2 页完成；receipt 仍标明 `single_odoo_transaction` / `repeatable_read`，Accept 前不二次全量查询。证据 `freshness-repeatable-read-orm.result.json`。 |
| `TEST-XLSX-001` | 输出 identity、文件和版本核验 | **PASS（真实 Provider + 自动化）** | 两次真实输出分别验证 148 和 251 行；文件可读，identity 和选定字段与 source 完全一致，Candidate SHA / Finalize SHA 正确。旧 diagnostic 文件另见 `legacy-148-output-inspection.json`；其空白辅助列已不再导致拒绝。复杂计算仍不由本地重算。 |
| `TEST-LIFE-001` | Candidate / Accept / Reject / Finalize | **PASS（自动化 + 真实 Provider）** | 自动化覆盖新建 / current-source / Reject；真实 148 行 Provider Candidate 待用户确认，确认前 Current 空，明确“接受”后推进，Finalize 交付同一 SHA。M2 legacy direct-V1 `create` 和旧 edit 回归仍通过。 |
| `TEST-REG-001` | M2 / Retriever 定向回归 | **PASS（已选定回归范围）** | M2 Edit / Validator / Version State / Office-Retriever 集成 33 项，M3 Retriever / Registry 8 项通过。全 addon suite 未执行。 |

## 执行记录

### ATR-RUN-001 — 定向自动化与兼容性回归

- 数据库：`odoo18e_llm`；Odoo 自动化监听端口：`18091`。首次受限沙箱连接被操作系统拒绝（`Operation not permitted`），随后依已授权范围在可连接本机 DB 的执行上下文中重跑；无测试失败由此产生。
- M3 `test_export.py`：**14 项通过**，日志 `odoo-test-m3-export-final10.log`。覆盖 148 条 100+48 收集、251 条三页收集、count drift / 重复身份拒绝、批量关系、receipt v3、root/relation/payload 资源限额、查询异常 fail-closed、错误投影拒绝、indeterminate Provider 不自动重放、new/current Candidate Accept/Reject/Finalize。
- M2 `test_edit_orchestration.py`：**11 项通过**，日志 `odoo-test-m2-edit-orchestration-final.log`。
- M2 `test_candidate_validator.py`：**5 项通过**，日志 `odoo-test-m2-candidate-validator.log`。
- M2 `test_workbook_version_state.py`：**11 项通过**，日志 `odoo-test-m2-version-state.log`。
- M2 `test_office_retriever_integration.py`：**6 项通过**，日志 `odoo-test-m2-retriever-integration-final.log`。
- M3 `test_retriever.py`：**8 项通过**，日志 `odoo-test-m3-retriever-final.log`。
- 合计：原定向集合为 **55 项**（M3 export 14 + M3 Retriever 8 + M2 定向回归 33）。IHR-006 因新增核验与故障注入，本轮重新运行 M3 export **20 项全部通过**；M3 Retriever 8 项与 M2 定向回归 33 项代码未变，沿用原通过证据，不重复执行。当前可追溯的定向结果合计 61 项通过；另有 3 项未修改上游 ResponsesAdapter 的离线资源断言通过。最终 M3 export 结果保存在 `odoo-test-m3-export-final.result.txt`。
- 命令模板：

  ```sh
  venv/bin/python odoo-bin -c odoo.conf -d odoo18e_llm --http-port=18091 \
    --test-file=<测试文件路径> --stop-after-init \
    --logfile=office_engine/docs/implementation/evidence/CC-M3-02/<日志文件> \
    --log-level=info
  ```

### ATR-RUN-002 — 真实 Provider Hosted CI 验证（未通过）

- Provider：Odoo 当前配置 `OpenAI GPT-5.6 Luna` / `gpt-5.6-luna`。使用合成 `res.partner` 数据。更高输出 token 限额仅对测试进程生效，不写回配置。
- 一次 4096 token 输出限额的 Provider 响应达到上限并报告 `provider_response_incomplete`，没有 Candidate：`real-provider-148.log` / `real-provider-148-summary.json`。
- 一次真实 Hosted CI 调用返回 XLSX，文件可读、149 行（含表头），148 个 identity 均存在；但 root 表包含 `__office_parent_id`，违反 root 表仅需 `__office_record_id` 的契约。M3 验证器拒绝 Candidate，Current 未推进。原始合成文件只作诊断证据：`real-provider-148-diagnostic-candidate.xlsx`、`real-provider-148-diagnostic-summary.json`。
- 修正 root 表指令后，分别发起两次新请求；均在 Provider 连接 / 响应阶段超时，无响应 ID、无可用 XLSX、清理状态 `unknown`，Adapter 的 `retry_decision` 为 `not_automatic`：`real-provider-148-final-summary.json`、`real-provider-148-last-summary.json`。为避免重复发送无明确恢复条件的请求，本轮未再重试。
- 结论：已验证真实 Provider/Hosted CI 可接收 handoff 并生成文件，但输出契约未通过；修正后的完整 148 条输出与 Candidate → Accept → Finalize 真实 Provider 链路**未验证通过**。这不降低最终验收要求。

### ATR-RUN-003 — 通用输出核验、资源 / freshness、真实 Provider 与生命周期补验

- **旧 148 行 XLSX 的结论：** `real-provider-148-diagnostic-candidate.xlsx` 实际有 149 行（含表头）、148 条数据、148 个唯一且连续 identity（3272–3419）；Name / Email 均 148/148 非空且唯一；`__office_parent_id` 148 行全空；没有公式，且原任务未选择关系集合。旧事务已回滚，未留存 146 条中间源值，故不能追溯比较旧文件的每个字段值；首尾值与已保存的 Provider 诊断摘要一致。结构检查明细见 `legacy-148-output-inspection.json`。
- **通用核验器修订：** root 表可有可无地带空白 `__office_parent_id`，其他未知辅助列也可出现在任意位置但必须全空；它们不影响对计划可见列的映射。仍严格要求计划列唯一且有序、identity 列唯一、行数一致、每个 identity 恰好一次、每个所选值逐字段匹配；root parent identity 必须空，关系表 parent-child pair 必须精确，非空未知列 / 缺失 / 重复 / 错值继续拒绝。新测试证明空白辅助列被接受，填值辅助列、错值、重复身份仍被拒绝。
- **实现中发现并修复的缺陷：** 关系 XLSX 验证器曾从 Provider handoff `dataset` 读取不存在的 `field_types`，触发 `KeyError`；现改从本地已解析 collection plan 取字段类型。真实 Candidate 响应的 `workbook_source` / `provider_input_sha256` 曾从 receipt 错误顶层读取，现改取 `source.kind` / `handoff.provider_input_sha256` 并有断言。
- **自动化：** M3 `TestM3Export` 20/20 通过；增加 M2O / O2M / M2M relation pair，错 inverse / 缺 relation，handoff 摘要篡改时无 Provider / Candidate，Provider 无输出失败状态，root / relation / handoff bytes 临界值和超限，空白辅助列核验。完成日志及结果摘要：`odoo-test-m3-export-final.log`、`odoo-test-m3-export-final.result.txt`。并发 freshness 用两条 Odoo ORM cursor 验证 3 条 initial rows 在 insert/update/delete 之后仍按同一个 `REPEATABLE READ` read view 完整可见；3 条 synthetic row 通过 ORM 清理，见 `freshness-repeatable-read-orm.result.json`。
- **ResponsesAdapter 资源边界：** 受限 venv 没有 pytest；通过既有未修改的 assertion 测试函数作离线直接执行，覆盖 input bytes 超限预检、output bytes 限制失败关闭、Provider timeout→indeterminate，3 项均 PASS，见 `responses-adapter-resource-check.result.txt`。未发出网络请求。
- **真实 Provider 148 行：** `OpenAI GPT-5.6 Luna` / `gpt-5.6-luna`，timeout 配置 120 秒，输出 token 仅本进程设为 8192，未持久修改配置。Hosted CI 用时 24.660 秒，返回 148 行 XLSX；同一事务源行与输出 `(identity, Name, Email)` 顺序 / 字段完全相等。摘要中的 canonical source-row digest（`source_rows_sha256`）与 XLSX 投影行 digest（`output_rows_sha256`）均为 `58d865a7a09e60bfb970d1cb589ee55dbf1ff09971d3875320936f44497f9162`。完整数据 handoff payload 的 SHA（`handoff_sha256`）为 `7a12b60a04b1b8566cf177c84d9f10ea49781bce1ca1bed7eacbb2f02eb1f8b0`，大小 17,794 bytes；发给 Provider 的 input digest 是 `8765c9813e9a3917b518b7cdbd933dde62ed0215e44e5088e42f7b0e5d40bde6`。Candidate XLSX 字节 SHA（`candidate_output_sha256`，并经独立文件读取重算）为 `ea65f0ddbbb12831027397861d94b9c2ea537f68e0b2d283257f1e800950b288`；Finalize 文件 SHA 与它相同。Candidate 创建前 Current 为空、revision 0；明确用户消息“接受”后成为 Current、revision 1。Final validation grade 仍为 M2 `PARTIALLY_VERIFIED`，未被 Accept 提升。Provider response/request/download IDs、usage、container cleanup 与完整边界状态见 `real-provider-148-helper-tolerant-lifecycle-summary.json`；XLSX 为 `real-provider-148-final-candidate.xlsx`。
- **真实 Provider 251 行：** 100+100+51 三页、handoff 30,199 bytes，Hosted CI 用时 28.000 秒，输出 XLSX 251/251 identity 与所选字段逐行相等。canonical source-row digest（`source_rows_sha256`）与 XLSX 投影行 digest（`output_rows_sha256`）均为 `820f15633fff795788a2a5f8ff8874e116972126a3f9851679a0a3d93fab45ff`；完整数据 handoff payload SHA（`handoff_sha256`）为 `55fc5ac463f8c797aade36c226f90e01afcfcadd1b7c0ce830dd8b332afcfd3e`；Provider input digest 为 `8765c9813e9a3917b518b7cdbd933dde62ed0215e44e5088e42f7b0e5d40bde6`。Candidate XLSX 字节 SHA（`candidate_sha256`，并经独立文件读取重算）为 `6f81d619c08b74458e7284fb8c05de36d1018b2cf5645fcd0256ba160378cc8d`；Candidate 前 Current 未变。见 `real-provider-251-summary.json` 与 `real-provider-251-candidate.xlsx`。生命周期 Accept / Finalize 由上述 148 行场景覆盖。
- **旧 Provider timeout 分析：** 两次失败在 37.855s / 48.326s，均低于配置的 120s；无 response / request / tool / file ID，`cleanup_state=unknown`，adapter 的 `response_received` 为 false，且错误为 `provider_connection_or_timeout`，因此停在首次 Responses 请求得到响应对象之前（最可能是 `responses.create` 网络请求；诊断未暴露更低层根因），不是 Hosted CI 文件下载阶段。随后两次真实请求分别在 24.660s / 28.000s 成功；此前 70.855s 的响应也小于 120s。没有证据表明增大 timeout 能修复早期连接失败，故保留 120 秒。4096 输出 token 的早期 `provider_response_incomplete` 由进程级 8192 测试上限规避，未写回 `odoo.conf`。
- **数据库清理：** 所有 Provider 场景在 `odoo18e_llm` 事务回滚；通过 ORM 检查 148/251 场景的合成首行联系人残留数均为 0。仅此开发库；未建数据库、未访问生产、未提交 Git。
- **收尾静态核验：** 本轮受影响的 M2 / M3 Python 文件全部通过 `venv/bin/python -m py_compile`；`git diff --check` 通过。模块版本与安装状态按只读 ORM 证据为 `office_engine_m3 18.0.2.0.0`；本次未因纯 Python 逻辑补充重复升级模块或重跑未改动的 M2 / Retriever 测试。

## 整体状态

CC-M3-02 技术与测试范围已完成，现**提交关闭评审，尚未由负责人正式关闭**。148 / 251 行真实 Provider XLSX、严格字段 / identity 核验、资源 / 并发 freshness、故障注入、M2 Candidate 生命周期及既有定向回归均有证据。真实 Provider 文件仍保留 M2 `PARTIALLY_VERIFIED` 的业务语义审阅等级；Final Agent UI HVR 仍属于 CC-M3-03，未作为本 CC 关闭证据。
