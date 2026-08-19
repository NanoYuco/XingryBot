# 项目上下文

> 这是长期项目事实。由开发者维护。Agent 不得自行修改，除非开发者明确要求更新项目上下文。

## 1. 项目基本信息

- 项目名称：`XingryBot`（开发者已确认）
- 项目目标：`可以完成各项功能的TG机器人，形态为猫娘`（开发者已确认；当前仓库已实现 GitHub 仓库绑定、Commit 进度检查、好感度互动、随机巡逻和每周周报）
- 最终用户：`telegram的中文用户`（开发者已确认）
- 当前阶段：`development`（开发者已确认）
- 部署形态：`cloud`（开发者已确认）

## 2. 技术栈

- 前端：`不适用：没有独立 Web、桌面或移动前端；最终用户界面是 Telegram 聊天与 Bot 命令菜单`
- 后端：`已验证：Python Telegram Bot；python-telegram-bot[job-queue]>=20.0、aiohttp>=3.9、python-dotenv>=1.0，依赖版本均未精确锁定`
- 数据库：`已验证：SQLite，通过 Python 标准库 sqlite3 直接访问；启动时创建 users、repos 表；文件位置由 DB_FILE 指定，默认是仓库根目录 cat_xingry.db`
- 包管理器：`已验证：pip + requirements.txt；README 使用 pip install -r requirements.txt，未发现 Poetry、uv 或 Pipenv 配置及锁文件`
- 运行环境：`Python 3.12.10`（开发者已确认；仓库尚未通过 `.python-version`、`requires-python` 或其他机器可读配置固定该版本）
- 外部服务：`已验证：Telegram Bot API；GitHub 公共 REST API。GitHub 请求未配置认证，使用 aiohttp、固定 User-Agent 和 10 秒总超时`
- 运行方式：`已验证：main.py 以 long polling 运行 Bot 进程，并使用 python-telegram-bot JobQueue 调度后台任务；生产部署为单实例后台进程`（生产拓扑与托管方式由开发者确认）
- 部署环境：`云服务器`（开发者已确认；当前以后台进程运行，仓库未配置 Docker、Compose、systemd、CI/CD 或其他启动与保活文件）

## 3. 主要目录与职责

| 路径 | 职责 |
|---|---|
| `main.py` | 已验证：配置标准日志、初始化 SQLite Schema、构建 Telegram Application 并启动 long polling。 |
| `bot/` | 已验证：组装 Telegram Application、注册命令菜单与处理器，并保存 `/check` 的进程内重复检查状态。 |
| `bot/commands/` | 已验证：实现 `/start`、`/bind`、`/unbind`、`/list`、`/check`、`/pat`、`/status` 命令。 |
| `core/config.py` | 已验证：从仓库根目录 `.env` 加载 `BOT_TOKEN`、`DB_FILE`，并定义固定 UTC+08:00 时区和 GitHub 请求参数。 |
| `database/` | 已验证：管理 SQLite 连接、启动建表、用户数据和绑定仓库数据的参数化 SQL 访问。 |
| `github/` | 已验证：解析 GitHub 仓库 URL，并异步读取 GitHub Commits API 的当日与近七日提交。 |
| `services/` | 已验证：聚合仓库进度、计算新增 Commit、管理好感度等级并生成检查回复。 |
| `jobs/` | 已验证：注册和重排随机巡逻任务及每周日 20:00 的周报任务。 |
| `utils/markdown.py` | 已验证：转义来自 GitHub 的外部文本，供 Telegram Markdown 消息使用。 |
| `.env.example` | 已验证：仅列出 `BOT_TOKEN`、`DB_FILE` 配置项名称和非秘密示例值。 |
| `requirements.txt` | 已验证：声明三个直接 Python 依赖及其最低版本。 |

## 4. 常用命令

| 目的 | 命令 |
|---|---|
| 创建虚拟环境（macOS / Linux） | `python3 -m venv .venv`（已验证：README 声明；本次审计未执行） |
| 激活虚拟环境（macOS / Linux） | `source .venv/bin/activate`（已验证：README 声明；本次审计未执行） |
| 安装依赖 | `pip install -r requirements.txt`（已验证：README 声明；本次审计按授权未安装依赖） |
| 初始化本地配置 | `cp .env.example .env`，随后填写 `BOT_TOKEN`（已验证：README 声明；不得提交或输出实际 Token） |
| 本地启动 | `python main.py`（已验证：README 与程序入口一致；本次审计按授权未启动服务） |
| 单元测试 | `未配置单元测试` |
| 集成测试 | `未配置集成测试` |
| Lint | `未配置 Lint` |
| 类型检查 | `未配置类型检查` |
| 构建 | `不需要独立构建步骤；当前为直接运行的 Python 服务` |
| 格式化 | `未配置自动格式化工具` |

## 5. 架构与约定

- 核心架构：`已验证：单体、分层的异步 Telegram Bot。main.py 依次初始化日志和数据库、构建 Application、注册命令处理器及 JobQueue 任务，然后进入 long polling。命令处理器和后台任务复用 services、database、github 模块。`
- 启动与调度：`已验证：启动后约 10 秒执行首次随机巡逻；巡逻在固定 UTC+08:00 的 08:00 至 22:00 窗口内运行并自行安排下一次执行；周报自行计算并安排下一次周日 20:00 执行。`
- 依赖方向：`已验证：main.py 依赖 bot 与 database；bot/commands 和 jobs 依赖 services、database、github、core；services 依赖 database 与 github；github 依赖 core 与 utils。当前通过直接导入函数和模块级配置连接，没有依赖注入层。`
- 状态管理：`已验证：持久状态位于 SQLite；/check 的重复调用计数位于 bot/state.py 的进程内字典，进程重启后清空，也不在多进程之间共享；生产部署当前为单实例。`
- 数据访问：`已验证：每次仓库操作创建一个同步 sqlite3 连接，并使用上下文管理器提交事务；SQL 参数使用占位参数；当前没有迁移框架或 Schema 版本。`
- API 约定：`已验证：项目不提供自有 HTTP API。Telegram 入口采用异步命令处理器；GitHub 集成只调用 repos/{owner}/{repo}/commits，并将结果转换为内部字典；用户消息使用 Telegram Markdown。`
- 错误处理：`已验证：缺少 BOT_TOKEN 时抛出 RuntimeError；重复绑定通过捕获 sqlite3.IntegrityError 返回布尔值；GitHub 拉取和定时推送捕获宽泛 Exception 并记录异常。当前尚未形成统一错误协议，GitHub 的非 200、网络错误和解析错误最终都可能表现为 None。`
- 日志约定：`已验证：main.py 使用 Python logging.basicConfig，级别为 INFO，格式包含时间、logger、级别和消息；部分异常日志包含仓库路径或 Telegram chat_id；尚未配置结构化日志、轮转或日志脱敏策略。`
- 测试约定：`未配置：未发现测试目录、测试文件或测试框架配置。`
- 命名与格式：`基于证据推断：模块、函数和变量以 snake_case 为主，常量使用 UPPER_SNAKE_CASE，Telegram 处理器与网络调用使用 async def；类型标注仅覆盖部分接口，未配置自动格式化、Lint 或类型检查来强制统一风格。`

## 6. 用户上下文与本地化

- 默认语言：`基于证据推断：当前产品内容为简体中文，但没有正式 Locale 配置或语言回退链。`
- 默认时区：`已验证：当前代码使用固定 UTC+08:00 偏移，尚未采用 IANA 时区；开发者已确认固定 UTC+08:00 不是长期规则，长期时区策略尚未决定。`
- 用户语言来源：`未配置：没有读取 Telegram effective_user.language_code，也没有在数据库存储用户语言。`
- 用户时区来源：`未配置：Telegram 请求和数据库均未提供用户时区；所有用户共用固定 UTC+08:00。`
- 翻译资源位置：`未配置：没有语言包、消息目录或翻译键。`
- 时间存储策略：`已验证：last_pat_date 与 last_check_date 以固定 UTC+08:00 计算后的 YYYY-MM-DD 文本存入 SQLite；GitHub 的 UTC 时间在比较前转换为固定 UTC+08:00；/check 的进程内重复状态使用 Unix 时间戳。当前没有统一的 UTC 持久化时间字段。`
- 时间展示策略：`已验证：Commit 时间和日期按固定 UTC+08:00 格式化为 HH:MM 或 MM-DD HH:MM；未按用户时区或 Locale 转换。`

## 7. 内容与 Prompt 管理

- 用户文案位置：`已验证：中文猫娘文案主要硬编码在 bot/commands/*.py、services/messages.py、jobs/weekly_report.py 和 bot/menu.py。`
- 模板位置：`未配置独立模板资源：消息当前通过处理函数中的字符串和 f-string 直接拼装。`
- 产品 Prompt 位置：`不适用：当前未集成生成式模型，仓库中没有产品 Prompt。`
- 运行时可编辑内容来源：`未配置：SQLite 只保存用户、好感度、摸头日期、仓库绑定和检查计数，不保存可编辑文案或模板；没有 CMS 或内容配置服务。`
- 人格边界：`已验证：最终用户回复采用猫娘语气；大多数后台异常日志保持技术性表达，但菜单注册日志和部分调度日志仍含中文或角色化措辞。`

## 8. 保护范围

- 未经明确要求不得修改：`README*`、`CHANGELOG*`、`LICENSE*`、公共 `docs/`、`AGENTS.md`、`.agent/` 中非任务明确授权的文件、生产配置和部署文件。`
- 凭据与本地配置：`不得读取、输出或提交 .env 的值；BOT_TOKEN 必须通过环境配置提供。.gitignore 已忽略 .env 及其变体，只保留示例文件。`
- 用户数据：`SQLite 数据库及其 WAL、SHM、journal 文件属于受保护的运行时数据，包含 Telegram user_id、chat_id、仓库绑定、好感度和互动日期；不得在审计、日志或测试产物中复制真实数据。`
- 不得破坏的行为：`现有 Telegram 命令 /start、/bind、/unbind、/list、/check、/pat、/status 的名称与基本语义；GitHub owner/repo 绑定格式；随机巡逻、周日 20:00 周报和好感度累计行为；现有 SQLite 表、字段、唯一约束及已有数据兼容性。`
- 禁止引入的依赖或技术：`未配置明确禁用清单；新增生产依赖或技术选型必须符合任务授权和当前 pip/requirements.txt 依赖策略。`
- 安全与隐私要求：`Token、凭据、私人数据不得进入源码、Prompt、日志、测试快照或交付报告；外部 GitHub 文本进入 Telegram Markdown 前须保持转义；异常信息不得向最终用户泄漏内部路径或堆栈。`

## 9. 已知问题与风险

1. `生产 Python 已确认为 3.12.10，但仓库没有机器可读的版本约束；依赖也只设置最低版本且没有锁文件，不同安装时间仍可能得到不同运行组合。`
2. `未配置自动化测试、Lint、格式化、类型检查和 CI，当前变更缺少仓库内自动回归保障。`
3. `生产环境当前以单实例后台进程运行，但仓库没有启动、保活或自动重启配置；部分 /check 状态仅存于进程内，进程重启后会丢失。`
4. `GitHub 请求未认证且当日最多读取 30 条、周报最多读取 100 条 Commit；API 限流或高提交量可能导致绑定验证失败或进度少计。`
5. `当前所有用户共用固定 UTC+08:00，未读取用户语言和时区；开发者已确认该偏移不是长期规则，但长期时区来源、默认值和迁移策略尚未决定。`
6. `用户文案分散并硬编码在多个处理器和任务中，没有翻译资源或运行时内容管理，统一修改与新增语言容易遗漏。`
7. `GitHub 集成以 None 合并非 200、网络异常和解析异常，错误分类不足；部分异常日志还会写入仓库路径或 Telegram chat_id，缺少明确的脱敏策略。`
8. `同步 sqlite3 操作直接运行在异步处理器和后台任务调用链中，且没有迁移版本、busy timeout 或并发访问策略；并发增加时存在事件循环阻塞和数据库锁竞争风险。`
