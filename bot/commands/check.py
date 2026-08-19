from telegram import Update
from telegram.ext import ContextTypes

from database.repo_repository import get_user_repos
from database.user_repository import register_user
from services.messages import generate_overview_messages
from services.overview import get_project_overviews


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    register_user(user_id, chat_id)

    repos = get_user_repos(user_id)
    if not repos:
        await update.message.reply_text(
            "(=; ｪ ;=) 主人还没有绑定任何 Git 仓库喵！请先发送 `/bind <Git链接>` 喵！",
            parse_mode="Markdown",
        )
        return

    results = await get_project_overviews(repos)
    texts = generate_overview_messages(results)

    for text in texts:
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
