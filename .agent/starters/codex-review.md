# Codex：独立技术复核会话启动语

在新的 Codex 会话或独立 Review 会话中发送：

```text
请对任务 `<task-id>` 进行独立技术复核，默认只读，不修改代码。

读取根目录 `AGENTS.md`、`.agent-work/tasks/<task-id>/task-contract.md`、`.agent-work/tasks/<task-id>/delivery-report.md`，并检查实际 Diff、相关源码和测试。实现者的交付报告只能作为线索，不能替代独立证据。

按照 `.agent/prompts/technical-reviewer.md` 复核每个 `AC-*`、错误路径、回归风险、测试充分性、范围偏离和共享工程准则。必要时独立运行关键验证。

使用 `.agent/templates/technical-review-report.md` 创建：

`.agent-work/tasks/<task-id>/technical-review-report.md`

只报告具体、可复现、可操作的问题。结论只能是：建议通过、修复后通过、阻断交付或无法复核。
```

