# ChatGPT Work：验收会话启动语

将下面内容复制到一个新的 Work 本地会话：

```text
请先完整读取：

1. `.agent/prompts/shared-engineering-rules.md`
2. `.agent/prompts/planning-controller.md`
3. `.agent/project-context.md`
4. `.agent-work/tasks/<task-id>/task-contract.md`
5. `.agent-work/tasks/<task-id>/delivery-report.md`
6. `.agent-work/tasks/<task-id>/technical-review-report.md`
7. 当前工作树的实际 Diff、测试结果和运行/渲染证据

当前模式：交付验收。
任务 ID：`<task-id>`。

不要依据实现者的“已完成”声明直接通过，也不要修改应用代码。逐项核对任务契约中的 `AC-*`、非目标、范围边界和共享工程准则。证据不足与实现失败必须区分。

使用 `.agent/templates/acceptance-report.md` 创建：

`.agent-work/tasks/<task-id>/acceptance-report.md`

最终结论只能是：通过、附条件通过、不通过或阻塞。若不通过，给出只修复失败项的最小修复任务，不要重新设计已经正确的部分。
```

