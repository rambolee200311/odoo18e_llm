# GPT 聊天候选重排隔离实验 — 授权与结果

- 日期：2026-11-19（Asia/Shanghai）
- 数据库：`odoo18e_llm`
- Provider / 模型：OpenAI GPT-5.6 Luna / `gpt-5.6-luna`
- 状态：实验已执行；不构成 CC 验收通过或产品实现

## 授权与隔离边界

项目负责人在本会话中单独授权“仅限隔离测试”，允许将真实 Retriever 返回的候选模型名、描述和 `_rec_name` 连同合成盲测查询发送到 GPT-5.6 Luna 聊天接口做候选重排。

Provider runner 只读取 `blind_queries_v0.1.json`，通过现有 Retriever `discover` 得到每条查询最多 50 个候选，再把该候选列表交给聊天接口。Runner 不读取 `oracle_v0.1.json`，不执行业务记录 `search`，不调用 Office Tool，不写入业务文件，也不读取 API 凭据。独立离线 evaluator 在 Provider 调用完成后才读取 Oracle。

## 实际请求证据

- 40 条合成盲测查询；39 条返回非空候选并提交聊天请求，1 条候选池为空而未调用聊天接口。
- Provider SDK 审计记录 39 个请求、39 个响应、0 个 Provider 错误；模型均为 `gpt-5.6-luna`。
- 每个请求的用户消息只含业务描述和 Retriever 实际返回的候选；候选项仅含候选编号、模型名、描述、`_rec_name`。离线核验确认 39 个请求载荷与结果文件中的候选池逐条一致，39 个响应与 Runner 记录一致。请求未附 Tool Schema 或工具调用。
- 审计事件中没有凭据字段。
- Chat API 往返 p50 为 1.656 秒、p95 为 3.830 秒；不包含 Retriever embedding 时间。

## 离线结果

| 指标 | 结果 |
|---|---:|
| Retriever 返回前 50 个候选的目标覆盖 | 34/40（85%） |
| 同一轮 Retriever 原始前 5 命中 | 18/40（45%） |
| GPT 返回列表含目标 | 34/40（85%） |
| GPT 首选命中 | 30/40（75%）；在目标进入候选池时为 30/34（88.2%） |
| 完整返回 5 个候选的响应 | 12/40（30%） |
| Runner 状态 | 38 success、1 empty candidate pool（V03）、1 invalid response（PR03） |

Provider 请求要求“最多 5 个”候选，因此实际排名长度不固定。完整五项排序只有 12 条；故本实验不能作为 Retriever/GPT **Top-5** 门槛的通过证据。Retriever 的 50 项候选池本身漏掉 6 条目标，也无法由重排弥补。结果表明该隔离方案在部分已召回候选上能把正确模型提到首位，但整体尚未达到冻结 40/40 要求。

## 清理与结论

Odoo ORM 按临时 Thread 1050 复核：Thread 不存在、关联消息 0、Provider usage 关联 0、审计 allowlist 参数不存在。没有业务数据修改或 Office 产物。

这是候选方案的方向性可行性证据，不是 Agent E2E、不是产品行为、不是 M4/CC 冻结验收，也不改变原始 Retriever Top-5 18/40 与分页不稳定 FAIL。先前的 `provider_chat_metadata_rerank_block.md` 记录的是单独授权发出前被阻止的历史调用；本报告记录负责人随后授权后的隔离实验。

## 证据文件

- `run_provider_chat_rerank_blind_v0.1.py`：Provider runner；不加载 Oracle。
- `provider_chat_rerank_blind_v0.1.jsonl`：40 条逐项候选池与响应。
- `provider_chat_rerank_sdk_audit_v0.1.jsonl`：SDK 边界原始请求及响应。
- `evaluate_provider_chat_rerank_blind_v0.1.py`：本地 Oracle 离线评估器。
- `provider_chat_rerank_evaluation_v0.1.json`：逐项及汇总评分。
- `provider_chat_rerank_cleanup_v0.1.json`：ORM 清理复核。
