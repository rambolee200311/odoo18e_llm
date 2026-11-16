# ATR-M3-02 — 前置最小可行性 Spikes

| 项目 | 结果 |
|---|---|
| 关联 CC | CC-M3-02 v0.2（FROZEN；本记录不授予实施权限） |
| 设计基线 | TDD v0.4、Implementation Plan v0.3 |
| 执行日期 | 2026-11-15 |
| ATR 状态 | **PASS — 四项前置最小可行性 Spike** |
| 代码 / DB 写入 | 无代码修改；无 Odoo 业务记录写入；未创建数据库 |
| 结果报告 | [CC-M3-02 前置 Spike 报告](../verification/TV_CC_M3_02_Preimplementation_Spikes_20261115.md) |
| 证据目录 | [TV_CC_M3_02_Preimplementation_Spikes_20261115](../verification/evidence/TV_CC_M3_02_Preimplementation_Spikes_20261115/) |

## 验收记录

| OPEN | 前置 Spike 结论 | 后续仍强制的实施验收 |
|---|---|---|
| OPEN-01b | PASS：真实 Hosted CI 读取 synthetic XLSX sentinel，返回回读文件 | Office Tool / Agent orchestration、新建与编辑 handoff、148 条和更大有界完整性 HVR / 自动化验收未运行 |
| OPEN-02 | PASS：小样例收集到 byte / token / duration 指标，证明有限样例可行 | 生产有限 cap、基准、边界及超限测试未运行；不得把本次测量当容量上限 |
| OPEN-03 | PASS：现有 Odoo ORM 调用中同一 cursor / connection 保持 `REPEATABLE READ` | Collector root / relation 查询一致性、并发变更与 freshness 验收未运行 |
| OPEN-04 | PASS：XLSX 文件可结构验证，合成 identity 集合可客观比较 | M3 projection manifest、实际 Candidate 生命周期及最终文件 identity 对照未运行 |

本 ATR 只关闭四项设计可行性前置 Spike，不关闭上述 CC-M3-02 实施验收，也不代表 TDD 的完整数据交付要求已实现。冻结授权登记中的缺项状态按冻结时点保留；本 ATR 是后续执行证据。CC-M3-02 仍需单独 Coding Authorization 才能实施。

## 证据摘要

- 真实 provider/model：`OpenAI GPT-5.6 Luna` / `gpt-5.6-luna`；未记录或输出凭据。
- 仅向 Hosted CI 提供 synthetic sentinel；输入 XLSX 4,880 bytes，SHA-256 `8158bac93711e0a61ceacbd0fbc0e9d0c3df98b960894f163372862600c3899a`。
- Hosted CI 读取 sentinel 后返回 `Readback.xlsx`，4,863 bytes；输入 / 输出值核对通过，临时 container cleanup 完成。
- Provider usage：2,462 input tokens、683 output tokens、246 reasoning tokens、25,076 ms。该小样例不能用于推算生产容量。
- Odoo ORM 只读探测数据库 `odoo18e_llm` 的 `ir.model` 分页；0 次写入。
- 输出核验合成文件：4,918 bytes；既有 verifier 返回 `PARTIALLY_VERIFIED`，文件结构检查通过；identity 3/3、无重复。既有 verifier 尚无预期 identity manifest 比对接口。

## 审查结论

四个 Spike 满足 TDD v0.4 §20 所定义的最小可行性门槛。结果不授权编码、Provider 大数据测试或 UI HVR；不改变 CC 范围、设计、数据库限制或最终验收标准。下一步须由负责人单独批准 CC-M3-02 Coding Authorization。
