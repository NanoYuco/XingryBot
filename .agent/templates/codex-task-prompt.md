# Codex 任务：<task-title>

请实现任务 `<task-id>`。

开始前完整读取：

1. 根目录 `AGENTS.md`；
2. `.agent/project-context.md`；
3. `.agent-work/tasks/<task-id>/task-contract.md`；
4. 与任务直接相关的代码、测试和配置。

以任务契约为本次工作的唯一任务级事实来源。先核实其中的仓库假设；如果仓库现状只影响实现细节，可以采用更合适的实现并在交付报告中记录。如果冲突会改变用户行为、公开接口、数据兼容、安全、费用、非目标或验收标准，暂停并说明冲突，不要静默改写任务。

在授权范围内完成实现和相关测试，运行任务契约要求及项目中最相关的验证。不要修改受保护文档、`AGENTS.md` 或 `.agent/`，不要提交、推送或部署，除非当前请求另有明确授权。

完成后根据 `.agent/templates/delivery-report.md` 创建：

```text
.agent-work/tasks/<task-id>/delivery-report.md
```

最终回复只需概括实现结果、关键验证、偏离、未验证内容和阻塞项；不要用总结代替报告中的证据。

