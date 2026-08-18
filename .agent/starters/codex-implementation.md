# Codex：实现会话启动语

从项目根目录启动 Codex，新建实现会话后发送：

```text
请执行任务 `<task-id>`。

读取根目录 `AGENTS.md` 以及 `.agent-work/tasks/<task-id>/task-contract.md`，然后按照 `.agent-work/tasks/<task-id>/codex-task-prompt.md` 完成实现、测试和交付报告。

先检查任务契约中的仓库假设。只影响实现细节的差异可以自行调整并记录；会改变用户行为、公开接口、数据兼容、安全、费用、非目标或验收标准的冲突必须暂停并报告。

不要提交、推送或部署。完成后创建 `.agent-work/tasks/<task-id>/delivery-report.md`，并在最终回复中给出关键验证、偏离、未验证内容和阻塞项。
```

