import logging

from telegram import BotCommand


async def post_init(application):
    commands = [
        BotCommand("start", "认识喵喵与 Git 监督说明"),
        BotCommand("bind", "绑定 Git 仓库 (.git)"),
        BotCommand("unbind", "解绑指定的 Git 仓库"),
        BotCommand("list", "查看已绑定的全部仓库"),
        BotCommand("check", "检查已绑定仓库今日进度"),
        BotCommand("pat", "摸摸喵喵的头（增加好感度）"),
        BotCommand("status", "查看喵喵对你的好感度与等级"),
    ]
    await application.bot.set_my_commands(commands)
    logging.info("已成功向 Telegram 注册喵喵的最新指令菜单！")
