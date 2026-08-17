import time

from telegram import Update
from telegram.ext import ContextTypes

from bot.state import USER_CHECK_STATE
from database.repo_repository import get_user_repos
from database.user_repository import add_favorability, get_user, register_user
from services.messages import generate_check_text
from services.progress import collect_today_progress


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    register_user(user_id, chat_id)

    fav, _, _ = get_user(user_id)
    if not get_user_repos(user_id):
        await update.message.reply_text(
            "(=; ｪ ;=) 主人还没有绑定任何 Git 仓库喵！请先发送 `/bind <Git链接>` 喵！",
            parse_mode="Markdown",
        )
        return

    results, total_commit_diff = await collect_today_progress(user_id)

    if total_commit_diff > 0:
        add_fav = total_commit_diff * 5
        add_favorability(user_id, add_fav)
        fav += add_fav

    total_today_commits = sum(result["today_count"] for result in results if result)
    now_time = time.time()

    state = USER_CHECK_STATE.get(
        user_id,
        {"count": 0, "last_commits": -1, "last_time": 0},
    )
    if now_time - state["last_time"] > 3600 or total_today_commits > state["last_commits"]:
        check_count = 1
    else:
        check_count = int(state["count"]) + 1

    USER_CHECK_STATE[user_id] = {
        "count": check_count,
        "last_commits": total_today_commits,
        "last_time": now_time,
    }

    text = generate_check_text(results, fav, mode="active", check_count=check_count)
    if total_commit_diff > 0:
        text += f"\n\n✨ **检测到新项目进度！好感度 +{total_commit_diff * 5} 喵！**"

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
