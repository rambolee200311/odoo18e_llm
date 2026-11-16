# CC-M3-02 前置最小可行性 Spike 报告

| 项目 | 内容 |
|---|---|
| 日期 | 2026-11-15 |
| 基线 | 冻结的 M3 TDD v0.4、Implementation Plan v0.3、CC-M3-02 v0.2 |
| 范围 | OPEN-01b / OPEN-02 / OPEN-03 / OPEN-04 的前置最小可行性验证 |
| 结论 | **四项最小可行性 Spike 均通过；实施验收仍未执行** |
| 代码变更 | 无；未启动 CC-M3-02 实施 |
| 数据库 | 仅现有开发库 `odoo18e_llm`；未建库、未写入 Odoo 业务数据 |

本报告是冻结后新增的执行证据，不修改或取代冻结设计。冻结时授权记录中的 `Missing` 表示冻结时尚未执行；本报告记录后续 Spike 结果。四项 Spike 通过不等于取得 Coding Authorization，开始实施仍需单独授权。

## 1. OPEN-01b：Hosted Code Interpreter handoff 可行性

**方法。** 从 `odoo-bin shell -c odoo.conf -d odoo18e_llm` 通过 ORM 取得已配置的 `OpenAI GPT-5.6 Luna` provider / model，并调用真实 `ResponsesAdapter.execute()`。只发送一份约 4.8 KB 的合成 XLSX，包含随机化 sentinel `M3SPIKE01B-20261115-7f3a` 与数值 `1`。Hosted Code Interpreter 被要求读 `SentinelData!A1`、`B2` 并生成独立 `Readback.xlsx`。没有发送 Odoo 业务数据或 Provider 密钥。

**结果：PASS（仅限最小可行性）。** Adapter 返回 `candidate_received`，Hosted Code Interpreter 确实执行并回读两个值；输出工作表为 `Readback`，检查值匹配，候选 XLSX 存在，容器清理为 `completed`。调用、响应与下载 request ID、输入输出 SHA-256、token 和耗时见 [Provider 证据](evidence/TV_CC_M3_02_Preimplementation_Spikes_20261115/provider_hosted_ci_sentinel.json)。

**边界。** 这是实际 Provider / Hosted CI 和现有 Responses Adapter 的调用，不是 Agent UI 或 `office` Tool 完整编排 HVR。实际执行的 XLSX `input_file` 路径处于 `edit` 模式；当前 Adapter 对 `create` 模式拒绝 `input_xlsx`（见 `odoo-llm/llm_openai/services/responses_adapter.py:381-384`）。因此它证明一种现有载体可抵达 Hosted CI 并可读，但不证明 M3 新建工作簿导出已具备 Collector 到 Hosted CI 的生产 handoff。新建与编辑两种 Route B 集成、148 条及更大数据集仍是 CC-M3-02 强制验收。

## 2. OPEN-02：有限执行与测量信号

**方法与结果：PASS（只证明一个有界样例可测量）。** 上述 4,880-byte 输入和 4,863-byte 输出完成真实 Hosted CI 执行；记录到输入 2,462 tokens、输出 683 tokens、reasoning 246 tokens、合计 3,145 tokens，耗时 25,076 ms。文件字节、token 使用量、候选大小、完成状态和耗时均有实测值，证明存在可执行且可观察的有限样例。

单个小样例不能确定 root / relation 行数上限、生产 handoff 上限、wall-time 配置或服务容量。本 Spike 不冻结任何生产 cap。有限上限、资源边界、临界值及超限 fail-closed 测试仍须在 CC-M3-02 实施验收完成。

## 3. OPEN-03：同一 ORM cursor / transaction 的可行性

**方法。** 在现有 `odoo18e_llm` 的 Odoo shell 中，仅用 ORM 对 `ir.model` 以 page size 10、offset 0 / 10 / 20 连续读取三页；观察 cursor 和底层 connection 对象身份，以及当前隔离级别。未执行 commit、写入或 SQL。

**结果：PASS（仅限调用边界可行性）。** 三页均复用同一个 cursor 和 connection；当前 psycopg connection isolation level 为 `REPEATABLE READ`。三页各返回 10 项，IDs 范围分别为 1–10、11–20、21–30。可复核结果及探测脚本见 [ORM 证据](evidence/TV_CC_M3_02_Preimplementation_Spikes_20261115/orm_read_view_probe.json) 与同目录 `orm_read_view_probe.py`。

本 Spike 没有验证未来 Collector 的 root 与 relation 多页组合、并发 insert / update / delete 可见性、实际请求生命周期是否换 cursor、commit 边界或 freshness / refresh 语义；这些保持为实施验收。

## 4. OPEN-04：输出文件与记录身份核验可行性

**方法。** 用 3 条合成、唯一记录身份生成一份 4,918-byte XLSX。调用现有 `office_verify.verify_created_output_with_metrics()` 检查 XLSX package 与工作表结构，再以受限只读 XLSX 回读检查记录身份集合、条数和唯一性。

**结果：PASS（客观核验路径可行；M3 集成未实现）。** 现有 verifier 对 package integrity 和 worksheet structure 均报告 `SUPPORTED`，worker 正常退出；它按契约返回 `PARTIALLY_VERIFIED`，不声称能证明业务语义。单独的身份回读得到 3/3 条、集合相同、无重复。证据见 [身份核验证据](evidence/TV_CC_M3_02_Preimplementation_Spikes_20261115/output_identity_probe.json)。

需要准确区分：M2 的 `_bound_candidate()` 已核验附件绑定、输入输出字节、SHA、MIME、大小及版本关系（`office_engine/office_engine_m2/services/candidate_validator.py:29-84`）；新建 XLSX verifier 会验证文件完整性和结构（`office_engine/office_verify/verify.py:881-937`）。当前 verifier 不接收预期 identity manifest，因此本 Spike 的 identity 比对是单独的通用只读探测，不代表已有 M2 Candidate 生命周期会自动核对 M3 导出记录身份。M3 必须实现 TDD 约定的 projection identity / selected-field 对照并测试；复杂聚合和语义仍按 M2 `PARTIALLY_VERIFIED` / 用户审阅语义处理。

## 5. 门禁与后续验收

| TDD OPEN | 前置最小 Spike | CC-M3-02 最终实施验收 |
|---|---|---|
| OPEN-01b | **PASS**：已证明现有 Responses Adapter 的 XLSX 输入载体可被真实 Hosted CI 读取 | **NOT RUN**：新建 / 编辑 Route B handoff 集成、148 条（100+48）、更大有界集、count / identity / digest 与最终 XLSX 一致性 |
| OPEN-02 | **PASS**：小样例有有限执行及可采集资源信号 | **NOT RUN**：root / relation / payload / tokens / wall time 有界值、边界和超限失败门禁 |
| OPEN-03 | **PASS**：Odoo ORM 调用边界可复用同一 `REPEATABLE READ` cursor / connection | **NOT RUN**：Collector root / relation 全链路 read view、并发变化、freshness 与显式刷新 |
| OPEN-04 | **PASS**：现有 XLSX verifier 可检查文件结构；客观身份集合可由通用回读核对 | **NOT RUN**：Collector projection manifest 与真实 Hosted CI 输出身份对照、Candidate / SHA / 版本生命周期及已知 fixture 检查 |

实施验收还必须覆盖 M2 Route B 的新建与现有文件编辑、Candidate / Current / Accept / Reject / Finalize、失败时不生成完整 Candidate、M2 回归。Provider 的大数据测试仍须按冻结 CC 取得适用授权。OPEN-06 属于 CC-M3-03，不在本 Spike 范围。

### 未覆盖事项

- 未进行 148 条或更大数据集的真实 Provider 请求；本次结果不能推导生产容量。
- 未经浏览器执行真实 Agent UI → Retriever → Office → Excel → Accept → Finalize HVR。
- 未进行并发数据变更、关系数据全链路、候选版本登记或用户确认测试。
- OPEN-01b 最小测试从 Odoo shell 调用现有 Adapter，未覆盖 Agent / `office` Tool 的端到端编排。
- OPEN-04 的身份集合比对在 Spike 探测中完成，尚未接入运行时 Collector / Candidate 验证流程。

