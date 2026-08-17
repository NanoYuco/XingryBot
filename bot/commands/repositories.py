from telegram import Update
from telegram.ext import ContextTypes

from database.repo_repository import add_repo, get_user_repos, remove_repo
from database.user_repository import register_user
from github.client import fetch_repo_today_commits
from github.parser import parse_git_url


async def bind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    register_user(user_id, chat_id)

    if not context.args:
        await update.message.reply_text(
            "(=｀ω´=) 格式错啦喵！正确格式：\n"
            "`/bind https://github.com/NanoYuco/RougleLikeTest.git` 喵！",
            parse_mode="Markdown",
        )
        return

    repo_path = parse_git_url(context.args[0])
    if not repo_path:
        await update.message.reply_text(
            "(=; ｪ ;=) 喵呜... 无法解析这个 Git 链接，请检查格式喵！"
        )
        return

    await update.message.reply_text(
        f"🐾 正在连接 GitHub 验证仓库 `{repo_path}` 喵...",
        parse_mode="Markdown",
    )

    result = await fetch_repo_today_commits(repo_path)
    if result is None:
        await update.message.reply_text(
            f"(=; ｪ ;=) 找不到 GitHub 仓库 `{repo_path}`，请检查仓库名或权限喵！",
            parse_mode="Markdown",
        )
        return

    if add_repo(user_id, repo_path):
        await update.message.reply_text(
            f"ฅ(≧∇≦)ฅ 成功绑定 Git 仓库：\n`{repo_path}` 喵！\n"
            "以后喵喵会帮你盯着这个项目的进度啦！",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"ฅ'ω'ฅ 主人，你已经绑定过 `{repo_path}` 这个仓库啦，不用重复绑定喵！",
            parse_mode="Markdown",
        )


async def unbind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    register_user(user_id, chat_id)

    repos = get_user_repos(user_id)
    if not repos:
        await update.message.reply_text("(=; ｪ ;=) 主人当前还没有绑定任何仓库喵！")
        return

    if not context.args:
        await update.message.reply_text(
            "(=｀ω´=) 请输入要解绑的仓库名、链接或序号喵！例如："
            "`/unbind 1` 或 `/unbind NanoYuco/RougleLikeTest`",
            parse_mode="Markdown",
        )
        return

    arg = context.args[0].strip()
    target_repo = None

    if arg.isdigit():
        index = int(arg) - 1
        if 0 <= index < len(repos):
            target_repo = repos[index][0]
    else:
        target_repo = parse_git_url(arg) or arg

    if not target_repo:
        await update.message.reply_text("(=; ｪ ;=) 无法识别要解绑的目标喵！")
        return

    if remove_repo(user_id, target_repo):
        await update.message.reply_text(
            f"(=; ｪ ;=) 已成功解绑 Git 仓库：`{target_repo}` 喵！",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"(=｀ω´=) 解绑失败，找不到已绑定的仓库 `{target_repo}` 喵！",
            parse_mode="Markdown",
        )


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    register_user(user_id, chat_id)

    repos = get_user_repos(user_id)
    if not repos:
        await update.message.reply_text(
            "🐾 主人当前还没有绑定任何 Git 仓库喵！快捷绑定命令：\n"
            "`/bind https://github.com/NanoYuco/RougleLikeTest.git`",
            parse_mode="Markdown",
        )
        return

    repo_list_text = "\n".join(
        f"{index + 1}. `{repo[0]}`" for index, repo in enumerate(repos)
    )
    msg = (
        f"📋 **主人已绑定的 Git 仓库列表** ({len(repos)} 个)：\n\n"
        f"{repo_list_text}\n\n"
        "💡 使用 `/check` 可快速查看所有仓库的今日更新！"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
