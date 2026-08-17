import logging
from datetime import datetime, timedelta

from telegram.ext import ContextTypes

from core.config import TIMEZONE_BEIJING
from database.repo_repository import get_user_repos
from database.user_repository import add_favorability, get_all_users
from github.client import fetch_repo_weekly_commits


async def send_weekly_report_job(context: ContextTypes.DEFAULT_TYPE):
    logging.info("开始生成并发送周日项目周报...")

    for user_id, chat_id, fav in get_all_users():
        repos = get_user_repos(user_id)
        if not repos:
            continue

        report_body = ""
        total_weekly_commits = 0

        for repo_path, _, _ in repos:
            result = await fetch_repo_weekly_commits(repo_path)
            if not result:
                continue

            count = result["count"]
            total_weekly_commits += count
            report_body += f"📁 **[{repo_path}](https://github.com/{repo_path})**\n"
            report_body += f"• 本周提交：`{count}` 次\n"

            for commit in result["commits"][:3]:
                report_body += (
                    f"    - `{commit['date']}` {commit['msg']} "
                    f"(by {commit['author']})\n"
                )
            report_body += "\n"

        if total_weekly_commits > 0:
            add_fav = 20
            add_favorability(user_id, add_fav)
            fav_reward_text = (
                "✨ 本周有产出！结算奖励好感度 **+20** 喵！"
                f"(当前好感: `{fav + add_fav}`)"
            )
            comment = "本周主人超级勤奋！喵喵太崇拜你了，要继续保持哦喵！ฅ(≧∇≦)ฅ"
        else:
            fav_reward_text = f"⚡ 本周没有提交代码，好感度无变化喵！(当前好感: `{fav}`)"
            comment = "这周居然一个 Commit 都没有喵... 笨蛋主人是不是偷懒了一整周！下周要努力啦！(=｀ω´=)"

        text = (
            "📅 **【喵喵 Weekly】项目每周进展汇报** 📅\n\n"
            f"💬 **喵喵寄语**：{comment}\n\n"
            f"📊 **本周代码提交汇总** (共 `{total_weekly_commits}` 次):\n"
            f"{report_body}"
            f"🎁 **周报好感结算**：\n{fav_reward_text}"
        )

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        except Exception as exc:
            logging.exception("Failed to send weekly report to %s: %s", chat_id, exc)

    schedule_next_weekly_report(context.job_queue)


def schedule_next_weekly_report(job_queue) -> None:
    now = datetime.now(TIMEZONE_BEIJING)
    days_until_sunday = (6 - now.weekday()) % 7
    target = now.replace(hour=20, minute=0, second=0, microsecond=0) + timedelta(
        days=days_until_sunday
    )
    if target <= now:
        target += timedelta(days=7)

    seconds_until_sunday = int((target - now).total_seconds())
    logging.info(
        "Next weekly report scheduled in %.2f hours (Sunday 20:00).",
        seconds_until_sunday / 3600,
    )
    job_queue.run_once(send_weekly_report_job, when=seconds_until_sunday)
