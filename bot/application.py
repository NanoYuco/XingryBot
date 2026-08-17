from telegram.ext import ApplicationBuilder, CommandHandler

from bot.commands.check import check_command
from bot.commands.interaction import pat_command, status_command
from bot.commands.repositories import bind_command, list_command, unbind_command
from bot.commands.start import start_command
from bot.menu import post_init
from core.config import BOT_TOKEN
from jobs.scheduler import register_jobs


def build_application():
    if not BOT_TOKEN:
        raise RuntimeError(
            "未检测到 BOT_TOKEN。请复制 .env.example 为 .env，然后填写新的 Telegram Bot Token。"
        )

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("bind", bind_command))
    app.add_handler(CommandHandler("unbind", unbind_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("pat", pat_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("check", check_command))

    if app.job_queue:
        register_jobs(app.job_queue)

    return app
