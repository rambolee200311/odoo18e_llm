# CC-M3-01 — 实施历史记录（IHR）

## 0. 文档治理

本 IHR 记录冻结 CC-M3-01 的实际变更事实，供 ATR 与 FR 追溯。Implementation entry 的时间取已推送 Git commit 时间；不推断该提交之前未被记录的编辑 / 测试顺序。§4 历史条目仅追加；§1、§3、§5、§7、§8 为当前摘要。

## 1. 执行元数据

| 项目 | 记录 |
|---|---|
| IHR 文档 | `IHR-CC-M3-01-Retriever.md` |
| CC | [`CC-M3-01_Retriever_Enhancement_v0.2.md`](../../CC-M3-01_Retriever_Enhancement_v0.2.md)，v0.2，Frozen |
| 模块 | `office_engine_m3` |
| 工作类型 | 下游 addon 功能实现 |
| 实施记录来源 | 已推送 Git 提交及对应 ATR；本记录不推断提交中未记录的编码时间线 |
| Git 分支 | `codex/cc-m3-01-provider-acceptance` |
| 基础提交 | `a83b5b7` |
| 实施提交 | `c921ff05fde2c0f3288f07377536c07983678c40` — `feat(office-engine): complete M3 retriever acceptance` |
| 当前实施状态 | Implementation Complete |

## 2. Coding Contract 基线

| 项目 | 引用 |
|---|---|
| 实施范围 | CC §4.1 #1–8 |
| 范围外 | CC §4.2 |
| 必须保留 | CC §7 |
| 权限与安全 | CC §8–9 |
| 验收 | CC §10、§13 |
| TDD | M3 TDD v0.3：`API-RET-001`、`T-M3-SEC-001`、`T-M3-RET-001/002` |

## 3. 当前实施状态摘要

| 项目 | 状态 |
|---|---|
| CC §4.1 实施范围 | 8 项均由提交中的下游 addon 与测试覆盖 |
| Preservation Impact | Potential Impact；Retriever 工具执行、错误消息分发有扩展，验证见 ATR |
| 代码偏离 | 未发现超出 CC 的代码文件或上游模块变更 |
| Stop Condition | ATR 记录的环境观察未触发 CC §12 停止条件；Provider 调用依据后续明确测试指令执行 |
| 遗留问题 | CC-M3-01 范围内无未关闭实现问题；最终真实 Agent UI HVR 属于 CC-M3-03 |
| Revert | 未发生 |
| 当前状态 | Implementation Complete |

## 4. 实施历史条目

### IHR-001

| 字段 | 记录 |
|---|---|
| 时间 | 2026-11-13 16:54:24 +08:00（Git 提交时间） |
| 阶段 | Implementation |
| Action | 新增 `office_engine_m3` 下游 addon，扩展既有 Retriever 的 Registry 操作、搜索分页 / 排序、Domain 数组与错误分类；增加对应测试及 Provider 验证材料 |
| Reason | 落实冻结 CC-M3-01 v0.2 的 §4.1 与 §10 |
| Files / Components | `office_engine/office_engine_m3/**`；`office_engine/docs/implementation/evidence/CC-M3-01/**` |
| Contract Reference | CC §4.1 #1–8、§7、§10 |
| Upstream Reference | TDD v0.3 `API-RET-001`、`T-M3-SEC-001`、`T-M3-RET-001/002` |
| Result | Completed；提交 `c921ff05fde2c0f3288f07377536c07983678c40` 已推送 |
| Deviation | 未发现代码范围偏离。真实 Provider 验证按负责人随后明确要求使用配置的 `OpenAI GPT-5.6 Luna` 执行；详细调用证据在 ATR / Provider JSON |
| Follow-up | 正式关闭结论由 FR 评估；CC-M3-03 的真实 Agent UI HVR 不属于本 CC |

## 5. 实际变更清单

| 文件 / 路径 | 动作 | 实际变更 | CC 来源 |
|---|---|---|---|
| `office_engine/office_engine_m3/__manifest__.py` | Added | 声明下游 addon 及依赖 | CC §4.1 #8 |
| `office_engine/office_engine_m3/models/llm_tool.py` | Added | 同一 `odoo_record_retriever` 的 Schema / 操作分发、Registry 描述、分页搜索、Domain 和权限边界 | CC §4.1 #1–8 |
| `office_engine/office_engine_m3/models/retriever_errors.py` | Added | 稳定错误类别及诊断标识 | CC §4.1 #7 |
| `office_engine/office_engine_m3/models/mail_message.py` | Added | 将 Retriever 工具执行错误码与诊断标识写入既有工具结果消息 | CC §4.1 #7 |
| `office_engine/office_engine_m3/tests/**` | Added | Retriever、权限、分页、Domain、错误与兼容测试 | CC §10 |
| `office_engine/docs/implementation/evidence/CC-M3-01/**` | Added | ATR、Provider 请求证据及复现 runner | CC §10 验收证据 |

## 6. 偏离与停止条件记录

- **Deviation：** 未发现修改上游 `odoo-llm`、M2 addon、业务 ACL 或超出 CC 的业务模型逻辑。
- **Provider：** CC 冻结授权要求 Provider 单独授权。实施后负责人提供 `OpenAI GPT-5.6 Luna` 配置并要求继续测试；三次成功调用及两次诊断失败均按 ATR 原样保留。
- **Stop Conditions：** 未发现尚未解决的 CC §12 停止条件。
- **数据库事实：** ATR 保留了测试启动期间 Odoo CLI 对 PostgreSQL `postgres` 系统目录的查询观察；未执行 `CREATE DATABASE`，未连接其他 Odoo 业务数据库或生产库。该历史事实不在本 IHR 中改写，后续测试仍严格使用现有 `odoo18e_llm`。

## 7. 遗留问题与后续

| 项目 | 状态 | 责任阶段 |
|---|---|---|
| CC-M3-01 实现问题 | None | — |
| Odoo UI / 真实 Agent E2E | Deferred by CC boundary | CC-M3-03 |

## 8. 移交摘要

```text
Implemented：CC §4.1 #1–8
Actual Files：见 §5；实现与测试基线为 c921ff05fde2c0f3288f07377536c07983678c40
Open Issues：CC-M3-01 范围内 None；真实 Agent UI HVR 属于 CC-M3-03
Deviation：未发现未批准的代码偏离；Provider 测试按单独负责人指令执行
Stop Conditions Triggered：None unresolved
ATR：evidence/CC-M3-01/ATR-CC-M3-01-retriever.md
```
