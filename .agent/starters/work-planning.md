# ChatGPT Work：规划会话启动语

将下面内容复制到新的 Work 本地会话，并替换尖括号中的内容：

```text
请先完整读取以下文件，并将它们作为本对话的工作规则与项目事实：

1. `.agent/prompts/shared-engineering-rules.md`
2. `.agent/prompts/planning-controller.md`
3. `.agent/project-context.md`
4. 与本次需求直接相关的现有代码、测试、资料或历史任务文件

当前模式：需求澄清与方案规划。
任务 ID：`<task-id>`。
当前目标：<describe-the-goal>。
已知资料：<paths/attachments/links/notes>。
特殊约束：<constraints-or-none>。

先判断任务规模以及是否存在会实质改变方案的缺失信息。只询问最高价值的问题；其余可逆细节请记录为假设。不要修改应用代码。

在需求和方案确认前，只输出分析、选项和待确认项；不要提前生成可执行任务。经我确认后，再按照模板创建：

- `.agent-work/tasks/<task-id>/task-contract.md`
- `.agent-work/tasks/<task-id>/codex-task-prompt.md`
```

