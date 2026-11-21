# CC-M4-03 验收测试报告（ATR）

## 1. 验收摘要

本 CC 的组件实现、受影响回归以及 CC-TEST-006 / 007 强制分支已有实际验证证据。真实 Provider 在受控 Retriever 错误后成功纠正并通过 Oracle；重复错误时停止并如实报告。Thread 1995 远端 Hosted Code Interpreter 状态仍 UNKNOWN，但没有盲目重发；现有执行层确定性测试证明同一未知操作不会重复调用 Provider。

**当前状态：CLOSED — 项目负责人于 2026-11-21 批准关闭。** Thread 1995 的远端未知状态和 Thread 866 的历史根因 UNKNOWN 均保留，按冻结 CC 不通过重发或清理来消除。

## 2. 测试结果

| ID | 状态 | 实际结论与范围 | 证据 |
|---|---|---|---|
| CC-TEST-001 | PASS | 当前 handoff 故障注入已通过真实 Provider 及确定性组件路径验证：完整数据收集后中断、无 Candidate、最终失败消息持久化且重读可见。Thread 866 根因仍 UNKNOWN，按 CC 允许保留；新测试没有替代历史因果证明。 | `run_20261121T030004Z_result.json`；`handoff_20261121T043051Z_0facf053_{result,evaluation}.json`；`handoff_message_component_e2e.log` |
| CC-TEST-002 | PASS | 提交后可见、事务回滚不广播/不持久、postcommit 通知失败不丢消息；不在产品代码显式提交事务。 | `message_transaction_and_silent_retrieval_tests.log`；`m3_full_regression_final.log` |
| CC-TEST-003 | PASS | 成功纯 Retriever 内部消息静默；错误及 Tool Call/结果保留在上下文与审计，Office/最终消息不被过滤。 | 同上；`m3_full_regression_final.log` 中 `TestSilentRetrieval` 用例 |
| CC-TEST-004 | PASS（组件边界） | 中间 Retriever 错误内部保留，最终失败、权限拒绝、澄清及混合/Office 消息保持可见。真实 Provider 权限拒绝线程给出可见停止说明。 | `message_transaction_and_silent_retrieval_tests.log`；`run_20261121T030004Z_result.json` 中 Thread 1994；M3 回归日志 |
| CC-TEST-005 | PASS | 已验证非流式正式路径和可安全覆盖的事件分类中最终/错误/混合消息不被误隐藏。流式 generator 续接不属于修复目标；其余未覆盖流式分支记为 NOT RUN。 | `m3_full_regression_final.log`；`test_silent_retrieval.py` |
| CC-TEST-006 | PASS | 三个独立真实 Provider Thread 分别覆盖单次 `INVALID_QUERY` 纠正、单次 `FIELD_NOT_FOUND` 纠正、重复 `INVALID_QUERY` 后失败停止。两条恢复路径均保留用户的直属关系/启用/邮箱条件，最终数据与隐藏 Oracle 一致；停止场景在初次搜索及一次纠正重试都收到相同错误、没有新证据后提前停止，符合最多两次纠正重试的上限和提前停止条款，不误报零结果。原始失败和 Provider 暂时超时/断连记录均保留，并由后续完整响应 Thread 补测。 | `evidence/CC-M4-03/CC-TEST-006_007_补充验收记录_20261121.md`；`retriever_20261121T074630Z_*`；`retriever_20261121T081335Z_*` |
| CC-TEST-007 | PASS（安全停止；远端 UNKNOWN） | Thread 1995 只存在一次 Office 调用；Hosted CI 子结果 `indeterminate`，没有输出附件/Candidate SHA，Version 556 保持 `verifying`，Session 566 保持 `analyzing`，Current 未推进。SDK 最终失败说明未持久化为 Thread assistant 消息（该次测试清理回滚），不宣称用户可见。定向执行层测试同一请求二次进入时 Adapter 只调用一次，且 Session/Current 不前进。Thread、Version、Session 未重发、未清理。 | `thread1995_readonly_audit.json`；`thread1995_execution_receipt_evaluation.json`；`cc_m403_unknown_side_effect.log`；补充验收记录 |
| CC-TEST-008 | PASS（已覆盖边界） | 普通用户 ACL 拒绝进入 Agent，Provider 给出最终失败且未切换身份；确定性测试区分成功零结果与错误。Thread 1993 的错误选模零结果另记为 M4-02 失败，不是 ACL 或错误码被误报为零。 | `run_20261121T030004Z_result.json`；`m3_full_regression_final.log`；Retriever 定向测试历史证据 |
| CC-TEST-009 | PASS（定向） | 最终 M3 全模块 67 项无失败/错误；M2 Candidate/Finalize/Edit 关键生命周期 4 项无失败/错误。未运行 M2 全量套件，不宣称 M2 全量通过。 | `m3_full_regression_final.log`；`m2_lifecycle_regression.log` |

## 3. 执行证据

### 3.1 新增提示契约定向测试

- 初次日志 `prompt_contract_initial.log`：1 项失败，原因仅为测试断言仍寻找修订前的英文短语；实际新指引已加载。
- 修正断言后 `prompt_contract_final.log`：`0 failed, 0 error(s) of 1 tests`。
- `py_compile` 覆盖修改的模型、测试和 Provider 运行器，退出码 0。

### 3.2 最新 M3 回归

升级后的 M3 模块版本为 `18.0.7.0.7`，独立 ORM 会话确认模块状态为 installed 且版本一致。命令：

```text
./venv/bin/python ./odoo-bin -c odoo.conf -d odoo18e_llm -u office_engine_m3 --test-enable --test-tags /office_engine_m3 --stop-after-init --http-interface=127.0.0.1 --http-port=0 --gevent-port=0 --workers=0 --max-cron-threads=0 --log-level=test --logfile=/private/tmp/cc_m4_03_m3_final_regression.log
```

结果：67 项，`0 failed, 0 error(s)`。日志另记录既有 Registry 模型 `column.filter.field.info` 无表错误及多个既有字段参数警告；它们不是本次测试失败。测试日志保存在 `evidence/CC-M4-03/m3_full_regression_final.log`。

### 3.3 真实 Provider Handoff 复测

运行 `handoff_20261121T043051Z_0facf053`：现有开发库、OpenAI GPT-5.6 Luna、7 个请求/7 个响应，使用普通测试用户和两条合成直接联系人及一个 decoy。Provider 实际 Tool Calling 顺序为 `discover → describe → search → search → office`；Office 请求根表 `source="root"`。Collector Oracle 核对两条联系人身份、姓名、邮箱均匹配，decoy 排除。

受控故障确实在 `after_complete_collection_before_hosted_ci` 触发。Office 返回未执行失败；没有 Candidate/Version，最终答复明确说明没有可下载文件，并包含 Oracle 对应的两条联系人。重新读取 Thread 后最终 assistant 消息仍可见。此为**失败路径验证通过**，不代表 Excel 成功交付。

原始 Provider SDK 审计与故障事件日志均为 `0600`；不含 API Key 或 Authorization Header。Provider payload 包含合成数据和 Registry 元数据，不含隐藏 Oracle 答案。

### 3.4 回归日志

- `message_transaction_and_silent_retrieval_tests.log`：9 项，0 failed / 0 error。
- `handoff_message_component_e2e.log`：1 项，0 failed / 0 error。
- `m3_full_regression_final.log`：67 项，0 failed / 0 error。
- `m2_lifecycle_regression.log`：4 项，0 failed / 0 error。
- 另有上轮 `m3_regression_final2.log`：26 项，`0 failed, 0 error(s)`。

### 3.5 CC-TEST-006 / 007 补充验证

- 真实 Provider 最终通过 Thread：`2119`（`INVALID_QUERY`）、`2122`（`FIELD_NOT_FOUND`）、`2123`（重复 `INVALID_QUERY` 停止）；分别完成 8/8、7/7、6/6 Provider 请求/响应。具体 Tool Call、参数、执行回执、原始条件与 Oracle 对照见补充验收记录及各自 `retriever_*` 审计文件。
- 保留未通过的首轮 `retriever_20261121T074310Z`；保留 Thread 2120 `APITimeoutError` 和 Thread 2121 `APIConnectionError` 的运行结果（均无 Provider 响应），后续独立 Thread 补测通过。
- 对 Thread 1995 执行只读 ORM 回核：本地附件集合为空，无输出/最终/Candidate SHA；已有 handoff 与 Provider input SHA 不能当作 Candidate 文件 SHA。远端状态 UNKNOWN。
- 最终只读复核 `final_orm_recheck_20261121.json` 确认本轮测试 Thread、合成联系人已清理，测试用户已停用，测试故障参数及 Provider 审计临时开关已关闭；Thread 1995 仍仅有一次 Office 调用，版本与 Session 未推进。
- 定向测试 `TestM3Export.test_indeterminate_provider_attempt_is_not_silently_replayed` 为 1/1 PASS；`TestSilentRetrieval` 为 17/17 PASS。测试启动日志包含既有 `column.filter.field.info has no table` 错误，但各测试结果为 0 failed / 0 error；Silent Retrieval 测试中 `ACCESS_DENIED: synthetic denial` 是预期故障注入。

## 4. 真实 Provider 运行历史与缺陷复测

| Thread | 调用结果 | 判断 |
|---|---|---|
| 1993 | 注入一次 `QUERY_FAILED` 后重复同一查询；Agent 选择 `res.company`，重试得到零结果，而隐藏 Oracle 的公司记录实际位于 `res.partner`。 | FAIL，选模/规划问题；不归因于 Retriever ACL/ORM。 |
| 1994 | 注入 ACL 拒绝，Agent 最终告知用户无法完成，没有改身份或走其它读取路径。 | 权限停止行为 PASS。 |
| 1995 | 故障 hook 未触发；Hosted CI 回执为 `indeterminate`，留下 `verifying` 版本及 Session。当前 ORM 中只有一次 Office 调用与工具回执，没有输出/最终附件或 Candidate SHA。Provider SDK 中有最终失败说明，但该次测试清理回滚导致 Thread 没有最终 assistant 消息。 | 远端状态保持 UNKNOWN；本地无 Candidate、Current 未变、没有重复 Office 调用。按冻结契约保留 Thread/Version/Session，不重试、不清理；不宣称该次最终答复已对用户可见。 |
| 2002 | Agent 两次把根表 source 设为 `res.partner`，Office 两次拒绝且未执行；最终失败答复可读。 | FAIL 已定位：指引未明确根 source 值。修订后由 Thread 2049 复测。 |
| 2049 | 7/7 Provider 请求响应；根 source 首次正确。完整收集后由明确故障注入中断，最终失败答复重读可见，无 Candidate。 | 当前 handoff 失败路径 PASS；未触发 Retriever 参数错误纠正分支。 |

所有 Provider 测试用户/业务夹具均为合成数据。无版本的测试 Thread 和业务联系人已删除；相关测试用户及其联系人已停用，usage 审计外键记录保留。Thread 1995/version 556/session 566 因状态不确定而保留；最终新会话 ORM 结果确认该版本仍为 `verifying`、Session 为 `analyzing`，因此不重试不清理。`final_orm_recheck.json` 同时证明临时故障参数与 Provider 审计 allowlist 已关闭、Thread 2049 与 Candidate 不存在。

## 5. 关闭评审状态

CC-TEST-001～009 均已有冻结标准允许范围内的状态和证据：CC-TEST-006、007 的补充验收完成；Thread 1995 的远端结果和 Thread 866 的历史根因仍标记 UNKNOWN，未被误报为 PASS 的事实结论。项目负责人已于 2026-11-21 批准关闭 CC-M4-03。
