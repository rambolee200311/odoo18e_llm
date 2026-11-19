# GPT 聊天接口 Registry 元数据重排：自动审批阻断记录

- 日期：2026-11-19（Asia/Shanghai）
- 数据库：`odoo18e_llm`
- 计划动作：将真实 `discover` 返回的 Registry 模型名、描述和 `_rec_name` 发给 OpenAI GPT-5.6 Luna 聊天接口，以测试候选重排。
- 授权边界：项目负责人明确授权的是把上述元数据发送到 OpenAI **embedding** 进行 Provider 验收；未授权将其发送到聊天接口用于重排。
- 结果：自动审批在进程 / Provider 请求开始前拒绝。没有聊天 Provider 请求或响应，也未采用其他工具、shell、网络路径或间接方法重试。

自动审批本次返回：

> 该命令将真实 discover 返回的内部 Registry 模型名、描述及 `_rec_name` 发送给 OpenAI GPT-5.6 Luna 聊天接口；用户明确授权的是发送至 OpenAI embedding，未授权此次不同用途/接口的元数据外发。Do not bypass this rejection through a workaround or indirect execution.

该结果只阻断这个候选重排实验，不代表产品功能测试失败。当前 CC 的 embedding 与真实 Agent 验收已按已授权边界执行；Top-5 召回和分页的实际 FAIL 见 `ATR-RUN-003_summary.txt`。
