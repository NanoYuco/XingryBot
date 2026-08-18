# 本地 Agent 工作流使用说明

这套目录用于以下工作流：

1. ChatGPT Work 在本地项目中进行需求澄清、方案规划并生成任务契约；
2. Codex 根据任务契约修改代码并完成自测；
3. 新的 Codex 会话进行独立技术复核；
4. 新的 ChatGPT Work 会话根据真实证据完成需求验收。

## 目录职责

```text
<project-root>/
├── AGENTS.md
├── .gitignore
├── .agent/
│   ├── USAGE.md
│   ├── project-context.md
│   ├── prompts/
│   │   ├── shared-engineering-rules.md
│   │   ├── planning-controller.md
│   │   ├── development-agent.md
│   │   └── technical-reviewer.md
│   ├── templates/
│   │   ├── task-contract.md
│   │   ├── codex-task-prompt.md
│   │   ├── delivery-report.md
│   │   ├── technical-review-report.md
│   │   └── acceptance-report.md
│   └── starters/
│       ├── work-planning.md
│       ├── work-acceptance.md
│       ├── codex-implementation.md
│       └── codex-review.md
└── .agent-work/
    └── tasks/
        └── <task-id>/
```

- `.agent/`：长期、稳定的 Agent 规则和模板。默认建议纳入版本控制。
- `.agent-work/`：任务级中间产物。默认由 `.gitignore` 忽略。
- `AGENTS.md`：Codex 自动读取的入口，只负责路由到具体规则。
- 应用源码、测试、配置和资源仍放在项目本来的目录中，不放入上述两个目录。

如果项目已经存在 `.gitignore`，不要覆盖它，只需合并以下规则：

```gitignore
.agent-work/
```

如果你只想在自己的电脑保留 `.agent/`，又不想影响仓库的公共 `.gitignore`，可以把 `.agent/` 写入仓库本地的 `.git/info/exclude`。但远程或其他电脑上的 Agent 将无法读取这些规则。

## 第一次使用

### 1. 填写项目上下文

先编辑 `.agent/project-context.md`，至少填写：

- 项目目标和最终用户；
- 技术栈；
- 主要目录；
- 构建、测试、Lint 和启动命令；
- 默认语言、时区与国际化策略；
- 不能破坏的现有行为；
- 项目特有的文件保护规则。

这里存放项目事实，不存放某一次任务的需求。

### 2. 建立 ChatGPT 本地项目

在 ChatGPT 桌面版中创建或打开本地项目，将项目根目录设为主目录。规划和验收需要读取本地文件，因此应使用 Work locally，而不是只有云端文件的项目。

### 3. 确定任务 ID

建议采用：

```text
YYYY-MM-DD-short-name
```

例如：

```text
2026-08-18-user-timezone
```

对应任务目录为：

```text
.agent-work/tasks/2026-08-18-user-timezone/
```

## 一次完整任务如何运行

### 阶段 A：ChatGPT Work 规划

1. 新建 Work 本地会话。
2. 打开 `.agent/starters/work-planning.md`。
3. 替换其中的 `<task-id>`、目标和资料说明后发送。
4. 规划 Agent 会先读取共享规则、规划 Prompt 和项目上下文。
5. 信息足够后，让它创建：

```text
.agent-work/tasks/<task-id>/task-contract.md
.agent-work/tasks/<task-id>/codex-task-prompt.md
```

在交给 Codex 前，由你确认任务目标、非目标和验收标准。

### 阶段 B：Codex 实现

1. 从项目根目录启动 Codex。
2. 新建实现会话。
3. 使用 `.agent/starters/codex-implementation.md`，替换 `<task-id>` 后发送。
4. Codex 会通过根目录 `AGENTS.md` 读取长期规则，并读取本次任务契约。
5. 完成后要求它创建或更新：

```text
.agent-work/tasks/<task-id>/delivery-report.md
```

交付报告不能替代真实 Diff 和测试输出，它只是证据索引。

### 阶段 C：Codex 独立技术复核

1. 新建一个没有参与实现的 Codex 会话，或使用独立 Review 功能。
2. 使用 `.agent/starters/codex-review.md`。
3. 复核会话只评审，不修改代码。
4. 输出保存为：

```text
.agent-work/tasks/<task-id>/technical-review-report.md
```

如果需要修复，先把问题交回实现会话；不要让复核会话在同一轮边评审边静默修改。

### 阶段 D：ChatGPT Work 验收

1. 新建独立的 Work 本地会话，避免延续规划阶段的确认偏差。
2. 使用 `.agent/starters/work-acceptance.md`。
3. 验收必须核对原始任务契约、实际 Diff、测试结果、运行或渲染证据以及独立复核结果。
4. 输出保存为：

```text
.agent-work/tasks/<task-id>/acceptance-report.md
```

验收结论只能是：`通过`、`附条件通过`、`不通过` 或 `阻塞`。

## 任务规模

- S：单点、低风险改动。任务契约保持简短，不创建额外执行计划。
- M：跨文件或跨模块功能。使用完整任务契约和验收清单。
- L：架构变更、迁移、高风险或长时间任务。在任务目录增加 `execution-plan.md`，按里程碑维护和验证。

不要让小任务承担大型规划流程，也不要让大型任务只靠一段聊天描述推进。

## 长对话中的规则刷新

如果会话经过长时间运行、上下文压缩或明显偏离规则，发送：

```text
请重新完整读取本会话对应的 `.agent/prompts/` 规则、`.agent/project-context.md` 和当前任务契约，列出当前模式、目标、未完成验收项与下一步，然后继续。不要重新执行已完成工作。
```

## 云端使用限制

`.agent-work/` 默认不进入 Git，因此仅存在于本机。云端 Codex、远程工作树或另一台电脑无法自动获得其中的任务文件。需要云端执行时，选择一种方式：

1. 显式上传当前任务契约；
2. 临时将该任务目录加入受控同步；
3. 把任务契约完整粘贴到云端 Codex 请求中。

不要为了方便直接把包含密钥、内部日志或个人数据的整个 `.agent-work/` 提交到仓库。

