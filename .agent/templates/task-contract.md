# 任务契约：<task-title>

## 0. 元信息

- 任务 ID：`<task-id>`
- 规模：`S | M | L`
- 状态：`draft | confirmed | implementing | delivered | accepted`
- 创建日期：`<YYYY-MM-DD>`
- 确认人：`<developer>`

## 1. 目标

<用一段话说明要解决的问题、最终用户和可观察结果。>

## 2. 当前行为

<基于已读取证据描述当前状态，不确定内容不要写成事实。>

## 3. 期望行为

<按用户操作或系统事件描述完成后的行为。>

## 4. 非目标

- <明确本次不做什么。>

## 5. 已验证事实

| ID | 事实 | 证据位置 |
|---|---|---|
| F-01 | <fact> | `<file/command/source>` |

## 6. 假设与待确认项

| ID | 类型 | 内容 | 处理方式 |
|---|---|---|---|
| A-01 | 可逆假设/阻塞问题 | <content> | <assume/ask/stop> |

## 7. 功能要求

- FR-01：<requirement>

## 8. 工程与业务约束

- 保持行为：<invariants>
- 兼容性：<compatibility>
- 数据与迁移：<data-and-migration>
- 安全与隐私：<security-and-privacy>
- 语言与时区：<localization-and-time>
- 性能与容量：<performance>
- 文件保护：<protected-files>

## 9. 数据流或状态变化

<说明输入、处理、持久化、输出和失败路径。简单任务可写“不适用”。>

## 10. 建议实现范围

> 除非标注“必须”，以下路径和方案只是基于当前证据的建议。Codex 应先核实仓库实际情况。

- 可能涉及：`<path-or-component>`
- 必须复用：`<existing-abstraction>`
- 禁止改动：`<path-or-behavior>`
- 允许 Codex 自主决定：`<implementation-details>`

## 11. 边界与失败行为

| 场景 | 期望行为 |
|---|---|
| <edge/failure case> | <expected behavior> |

## 12. 验收标准

| ID | 可验证标准 | 预期证据 | 必需 |
|---|---|---|---|
| AC-01 | <observable criterion> | <test/command/diff/render> | 是 |

## 13. 验证计划

- 针对性测试：`<command-or-test>`
- 回归测试：`<command-or-test>`
- Lint/类型检查：`<command>`
- 构建：`<command>`
- 运行或 UI 验证：`<method>`

## 14. 里程碑（仅 L 级任务）

| 里程碑 | 完成条件 | 验证 | 状态 |
|---|---|---|---|
| M1 | <condition> | <evidence> | pending |

## 15. 必须暂停并请求裁决的情况

- <material conflict or irreversible decision>

## 16. 完成定义

所有必需 `AC-*` 获得真实证据；没有未披露的范围偏离；未验证内容、已知限制和风险已记录在交付报告中。

