from telegram import Update
from telegram.ext import ContextTypes

from database.user_repository import register_user


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    register_user(user_id, chat_id)

    msg = (
        "ฅ'ω'ฅ 喵呜~ 我是你的猫娘助手·喵喵** 喵！\n\n"
        "喵喵可以盯紧你的 Git 仓库 Commit 动态，观察主人敲代码项目，并根据你的项目开发进度与日常互动提升好感度哦！\n\n"
        "🎮 **指令菜单说明**：\n"
        "• `/bind <Git链接>` - 绑定要观察的 Git 仓库 (支持 `.git` 结尾)喵\n"
        "• `/unbind <序号/仓库名/链接>` - 解绑已绑定的 Git 仓库喵\n"
        "• `/list` - 查看当前绑定的全部 Git 仓库清单喵\n"
        "• `/check` - 查看所有已绑定仓库的 Star、PR、Issue 等项目总览喵\n"
        "• `/pat` - 摸摸喵喵的头（增加好感度）喵\n"
        "• `/status` - 查看喵喵对你的好感度与互动等级喵\n\n"
        "✨ **喵喵的核心机制**：\n"
        "1. **巡逻 Commit 加好感**：随机巡逻会抽查此前 24 小时的 Commit，每个 Commit 增加 5 点好感度；抽查之间遗漏的 Commit 不会补算喵！\n"
        "2. **周日晚 8 点周报**：每周日晚上 20:00 喵喵会自动推送全项目【周报汇总】，本周有产出会奖励额外好感度！\n"
        "3. **随机不定期巡逻**：法定工作日 10:00–17:00 期间，喵喵会按可巡视时间随机跳出来抽查项目进度喵~\n"
        "4. **日常摸摸**：每天可以使用 `/pat` 摸头 5 次增加好感喵！"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
