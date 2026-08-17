from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from core.config import TIMEZONE_BEIJING
from database.repo_repository import get_user_repos
from database.user_repository import (
    add_favorability,
    get_user,
    register_user,
    update_pat,
)
from services.favorability import get_fav_info


async def pat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    register_user(user_id, chat_id)

    fav, pats_today, last_pat_date = get_user(user_id)
    now_date = datetime.now(TIMEZONE_BEIJING).strftime("%Y-%m-%d")

    if last_pat_date != now_date:
        pats_today = 0

    if pats_today >= 5:
        await update.message.reply_text(
            "ฅ(＞﹏＜)ฅ 喵呜~ 今天已经被摸够了喵！头上的毛都要被摸秃啦！明天再来摸摸吧喵~ 🐾"
        )
        return

    pats_today += 1
    add_fav = 2
    add_favorability(user_id, add_fav)
    update_pat(user_id, pats_today, now_date)

    new_fav = fav + add_fav
    lvl, title, _ = get_fav_info(new_fav)

    if lvl == 1:
        reply = "ฅ(º ℕ º)ฅ 喵？！干...干嘛突然摸别人的头啦！别以为摸摸头就能不上班写项目了喵！（好感度 +2）"
    elif lvl == 2:
        reply = "ฅ'ω'ฅ 喵呜~ 主人的手好暖和喵！呼噜呼噜... 舒服得尾巴都竖起来了喵~（好感度 +2）"
    elif lvl == 3:
        reply = "ฅ(≧∇≦)ฅ 喵嗷~ 蹭蹭主人的手手！要多摸两下喵！喵喵最喜欢被主人摸摸头了！（好感度 +2）"
    else:
        reply = "(ฅ'ω'ฅ)♡ 喵呜... 主人摸得好舒服喵~ 喵喵一整天都要贴在主人身上不下来了喵！（好感度 +2）"

    reply += (
        f"\n\n💖 **当前好感度**：`{new_fav}` ({title}) "
        f"[今日摸摸: {pats_today}/5]"
    )
    await update.message.reply_text(reply, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    register_user(user_id, chat_id)

    fav, pats_today, last_pat_date = get_user(user_id)
    _, title, desc = get_fav_info(fav)

    now_date = datetime.now(TIMEZONE_BEIJING).strftime("%Y-%m-%d")
    today_pats = pats_today if last_pat_date == now_date else 0
    repos = get_user_repos(user_id)

    msg = (
        "📊 **喵喵的好感度面板** 📊\n\n"
        f"• **关系等级**：{title}\n"
        f"• **好感数值**：`{fav}` 点\n"
        f"• **状态描述**：{desc}\n"
        f"• **已绑仓库**：`{len(repos)}` 个\n"
        f"• **今日摸摸**：`{today_pats} / 5` 次\n\n"
        "💡 **好感度获取途径**：\n"
        "1. 每日使用 `/pat` 摸摸喵喵的头 (+2/次)\n"
        "2. 提交代码推进项目，每次产生新 Commit 均会增加好感度喵！\n"
        "3. 周日推送周报结算时，有项目提交可获得额外好感奖励！"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
