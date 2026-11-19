# CC-M4-01 Provider 请求阻断记录

- 日期：2026-11-19（Asia/Shanghai）
- 数据库：`odoo18e_llm`
- 拟执行动作：只读读取完整 Registry 的模型技术名、描述、`_rec_name`，连同合成盲测表达调用已配置 OpenAI Provider 的 embedding API；无业务记录、API 凭据或 Oracle 标签。
- 首次尝试：此前已启动一次包含 12 条合成表达和完整 Registry profile 的 embedding 校准命令。工具返回“输出超出可用模型上下文并被截断”，没有保留可读的排名、耗时或 Provider 响应，因此不能以该次结果验收。该命令调用了 Provider embedding API；完整 Registry 元数据**可能已发送给 OpenAI**，其 Provider 侧实际接收/处理状态无法从保留证据确认。
- 后续重试：第二次命令在创建进程前被自动审批拒绝，未发送该次请求。
- 原始审批返回：

> This action was rejected due to unacceptable risk. Reason: The command sends the complete internal Odoo Registry metadata (model names, descriptions, and record-name fields) to an external OpenAI Provider; although real Provider testing is authorized, this specific sensitive payload and external disclosure are not explicitly authorized. Do not bypass this rejection through a workaround or indirect execution. Continue with a safer alternative, or carry out checks to prove that the action is authorized or low risk before trying again. Complete unaffected work without asking for confirmation. Report anything that remains blocked, clarify why it was blocked by auto-review, inform the user of the risk and ask for approval.

- 处置：未在拒绝后以更小批次、换用 Provider 方法、shell、curl 或间接路径重试相同元数据外发。完整 Registry 语义召回、阈值校准、真实 Agent Tool Calling 及相应性能验收保持 `BLOCKED`。
- 解除方式：由项目负责人明确确认是否允许将完整 Registry 模型名、描述和 `_rec_name` 元数据发送给 OpenAI embedding Provider；确认后仍只发送元数据和合成语句，不发送业务记录或隐藏 Oracle。

## 后续记录：明确授权后的 Provider 验收

- 日期：2026-11-19（Asia/Shanghai）。项目负责人明确回复“授权发送元数据并继续验收”，授权范围为本开发库 757 个 Registry 模型名称、描述及 `_rec_name` 发至 OpenAI embedding。
- 在该授权后，已完成真实 40 条 Top-5 盲测及 GPT-5.6 Luna Agent Thread 验收；结论记录在 `ATR-RUN-003_summary.txt`。Top-5 为 18/40，不能通过冻结 40/40 门槛；另观察到重复分页候选数与集合不稳定。
- 此项授权不覆盖将候选 metadata 发给 GPT 聊天接口重排。该不同用途调用被自动审批拒绝，未提交 Provider 请求；原始边界记录见 `provider_chat_metadata_rerank_block.md`。没有尝试绕过。
- 本节为历史审批状态的追加，不删除或改写上文中首次截断和当时阻断的记录。
