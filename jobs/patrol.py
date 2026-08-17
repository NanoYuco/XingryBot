import logging
import random
from datetime import datetime, timedelta

from telegram.ext import ContextTypes

from core.config import TIMEZONE_BEIJING
from database.repo_repository import get_user_repos
from database.user_repository import add_favorability, get_all_users
from services.messages import generate_check_text
from services.progress import collect_today_progress


async def scheduled_check_job(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TIMEZONE_BEIJING)

    if 8 <= now.hour < 22:
        for user_id, chat_id, fav in get_all_users():
            if not get_user_repos(user_id):
                continue

            results, total_commit_diff = await collect_today_progress(user_id)

            if total_commit_diff > 0:
                add_fav = total_commit_diff * 5
                add_favorability(user_id, add_fav)
                fav += add_fav

            text = generate_check_text(results, fav, mode="passive")
            if total_commit_diff > 0:
                text += (
                    f"\n\n✨ **巡逻发现新项目进度！好感度 +{total_commit_diff * 5} 喵！**"
                )

            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
            except Exception as exc:
                logging.exception("Failed passive push to %s: %s", chat_id, exc)

        next_delay = random.randint(15 * 3600, 24 * 3600)
    else:
        target_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if now.hour >= 22:
            target_8am += timedelta(days=1)

        seconds_until_8am = int((target_8am - now).total_seconds())
        next_delay = seconds_until_8am + random.randint(0, 7200)

    logging.info("Next check scheduled in %.2f hours.", next_delay / 3600)
    context.job_queue.run_once(scheduled_check_job, when=next_delay)
