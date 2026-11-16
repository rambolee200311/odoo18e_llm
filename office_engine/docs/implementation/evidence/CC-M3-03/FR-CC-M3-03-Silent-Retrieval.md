# CC-M3-03 Final Report — 静默检索与最终 HVR

## 状态

**核心实施完成，已提交关闭评审，CC 尚未关闭。** 非流式 Silent Retrieval 核心路径和 148 单真实 Agent 导出已完成；浏览器下载文件 SHA 已补齐；附件上下文缺口已通过自动化回归修复。确定性的 `TEST-SILENT-002`–`005` 可见边界已由自动化及实际非流式路径证据验证。`TEST-REG-001` 建议范围化 PASS：M2 定向 12 项、M3 42 项和真实 HVR 通过，本轮未发现回归。M2 全量原始运行仍有 13 failures / 69 errors，其中 worker 错误原因未明；不声称全量回归通过，也不将原因不明错误归类为环境问题。第二家公司依赖测试为本 CC 不适用项。

## 已完成工作

- 在支持的非流式 Office 路径实现下游 Silent Retrieval。成功纯 Retriever 消息在通知前标记，不显示在 Discuss 历史和 SSE 消息事件中；查询失败时恢复错误消息可见。原消息、参数、结果和上下文继续保存。
- 增加通用 Agent 模型发现、关系表规划和 `export_records` Candidate 流程指引。
- 更新 OpenAI Tool Calling 对现有 Office 工具的有效 Schema 格式化。
- 增加 Hosted CI 源单元格精确复制指引和按日期字段核验 XLSX 的实现。
- 增加自动化测试，覆盖静默分类、Discuss / SSE 边界、错误恢复、混合工具可见性及流式安全边界。
- 修复 M3 附件上下文缺口：完整扫描 Thread 附件关系，不受 25 条 LLM 历史上限影响；每次 Provider 参数准备加入纯文本附件引用，不传二进制；用户明确文件名时优先选择历史附件。增加“整理成 Excel”新建 Odoo 导出路由及无需上传源文件指引。

## 验证结果

- `office_engine_m3`：当前 42 项测试，0 failures，0 errors；包含 100+ 消息附件上下文、历史文件优先和静默消息保留回归。
- M2 定向回归：12 项，0 failures，0 errors；覆盖 `TestWorkbookVersionState` 全类及 fileless Route B 导出工具绑定。
- 真实 Odoo UI + OpenAI GPT-5.6 Luna：Agent 自主发现模型、字段和关联，生成 Candidate 395；在页面收到用户明确回复“接受”后执行 Accept 和 Finalize。最终附件已发布。
- 最终附件 ORM 回读独立核验：148 / 148 个订单、185 / 185 条明细、185 / 185 组父子关联；请求字段和值均匹配，没有重复或错配；浏览器实际下载文件、最终附件、Candidate / receipt 的 SHA 相同：`92d6c0ac972bf406eb220701a637d7b36668c3950821b6c61e2276f5b948a5ee`。下载验证见 `browser_download_verification_v395.json`。
- 合成数据清理：按唯一标记通过 ORM 清理，清理后计数均为 0。
- Odoo 平台校验状态仍为 `PARTIALLY_VERIFIED`；该状态在 Accept 前对用户可见，Finalize 后仍保留。独立的 CC 数据核验通过，但没有替换或修改平台状态。

## TEST-REG-001 范围化结论及全量运行记录

**范围化结论：PASS（本轮未发现回归），已提交负责人关闭评审。** M2 定向 12 项、M3 42 项和真实 Agent HVR 覆盖本 CC 的 Candidate 生命周期、Route B 工具绑定、导出、Accept / Finalize 与文件结果。变更范围只涉及 M3 下游，没有修改 M2 或 OfficeCore 源码。

M2 全量运行仍保留为非通过原始结果：常规发现流程因缺少 `SETATTR_SOURCES` 中止；兼容 shim 运行 208 项有 13 failures / 69 errors，其中 67 个 OfficeCore worker pipe EOF 的具体原因未明，另有一次 failed-create 后的 `current` 读取错误。没有把这些错误归类为环境问题，也没有证据证明它们由本轮 M3 变更引入。依赖第二家公司的 1 项失败和 1 项 setup error 列为本 CC 不适用；不要求创建第二家公司。原始日志（包括 EOFError trace）已原样归档在本 CC evidence 目录。该全量运行未能证明 M2 整体 PASS，也未显示本轮 M3 范围内的明确回归。

确定性 Silent Retrieval 边界 `TEST-SILENT-002`–`005` 已依据自动化及本轮实际非流式路径证据验收 PASS。Provider 未在 HVR 中生成的随机场景明确记录为未实际观察，不作为额外待执行验收项。

## 附加 HVR 问题调查

失败线程 264 的原始用户消息 `461912` 没有附件，Thread 当时 `tool_ids=[]`；“整理成一个 Excel”未匹配 fileless 路由，因此 Provider 没有 Retriever / Office 工具。这不是 Silent Retrieval 丢失上下文，也不是 Office Schema 要求上传。另确认 M2 附件定位代码限制最近 25 条用户消息，M3 已下游修复并为 106 条后续消息及历史附件优先选择增加回归。原始 OpenAI HTTP 请求体未由当前系统持久化；证据依据为 ORM 消息、Thread 工具绑定状态和实际上下文构建逻辑。本次修复后没有再次调用真实 Provider，压力场景证据属于自动化回归。

## 治理状态

未修改冻结 TDD、Plan 或 CC；未修改上游 `odoo-llm`、M2 addon、OfficeCore 或本次合成数据之外的业务记录。没有提交、推送、合并、部署或发布；已提交范围化验收与 CC-M3-03 关闭建议供负责人评审。

详细记录见 `ATR-CC-M3-03-Silent-Retrieval.md`、`IHR-CC-M3-03-Silent-Retrieval.md`、`HVR-M3-03-001.md` 及本目录中的证据 JSON / 日志。
