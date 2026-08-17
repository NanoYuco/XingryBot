from services.favorability import get_fav_info


def generate_check_text(
    results: list,
    fav: int,
    mode: str = "active",
    check_count: int = 1,
) -> str:
    lvl, title, _ = get_fav_info(fav)
    total_today_commits = sum(result["today_count"] for result in results if result)

    body = ""
    for result in results:
        if not result:
            continue

        repo = result["repo_path"]
        count = result["today_count"]
        commits = result["today_commits"]

        body += f"📁 **[{repo}](https://github.com/{repo})**：\n"
        if count > 0:
            for commit in commits[:3]:
                body += (
                    f"  • `{commit['time']}` [{commit['sha']}] "
                    f"{commit['msg']} (by {commit['author']})\n"
                )
            if count > 3:
                body += f"  ...等共 {count} 条 Commit\n"
        else:
            body += "  • 今日暂无 Commit 提交\n"
        body += "\n"

    if mode == "passive":
        if total_today_commits == 0:
            if lvl == 1:
                header = "ฅ(>ω<)ฅ 喵呜！突查！喵喵悄悄摸过来巡逻喵！"
                comment = "看了一下你绑定的项目，今天居然 **0 提交** 喵？！主人是不是又在摸鱼！快去写代码！⚡"
            elif lvl <= 3:
                header = "🐾 喵~ 随机巡逻时间到！"
                comment = "今天绑定的项目还没有新进度喵，主人是不是遇到讨厌的 Bug 了？要休息一下吗喵~ ☕"
            else:
                header = "ฅ(≧∇≦)ฅ 主人~ 喵喵悄悄摸过来看看你啦！"
                comment = "虽然今天项目还没有 Commit，但喵喵会一直陪在主人身边的喵！要按时休息哦~ ✨"
        else:
            header = "ฅ(≧∇≦)ฅ 喵嗷！检测到你的 Git 项目有新进度啦！"
            comment = (
                f"今天已经累计提交了 **{total_today_commits}** 个 Commit 喵！"
                "主人敲代码的样子真的超级帅气！(ฅ'ω'ฅ)"
            )
    else:
        if total_today_commits == 0:
            if check_count == 1:
                if lvl == 1:
                    header = "(=｀ω´=) 哼！笨蛋主人！今天连 1 个 Commit 都没有还敢来点喵喵！"
                    comment = "项目目前还是 **0 进度** 喵！快去打开编辑器写代码！"
                elif lvl <= 3:
                    header = "ฅ'ω'ฅ 收到主人的召唤喵！"
                    comment = "今天绑定的仓库还没有新提交呢，主人是不是累啦？喵喵趴在腿上陪你写代码好不好喵~"
                else:
                    header = "(⁠ •̀⁠ ω⁠ •̀⁠ )⁠✧ 主人召唤喵喵啦！"
                    comment = "今天项目还没有新进度，不过没关系！无论主人写不写代码，喵喵最喜欢你了喵！"
            elif check_count == 2:
                header = "ฅ(◣_◢)ฅ 喵？！怎么又点 /check 了喵！"
                comment = "明明今天还是 **0 提交** 喵！就算你把按钮按烂，代码也不会自己写完的！笨蛋主人快去写项目！"
            elif check_count == 3:
                header = "(=; ｪ ;=) 等等... 主人你该不会是在故意戏弄喵喵吧？！"
                comment = "不写项目只知道连续戳喵喵，反复玩弄喵喵很好玩吗喵？！喵喵要咬你的猫爪肉垫了喵！嗷呜！ฅ"
            else:
                header = "😤 喵喵已进入【罢工装睡模式】！"
                comment = "哼！(背过身去把尾巴盖在脸上) 喵喵现在听不懂你在说什么喵！除非你现在去 Commit 一次项目，否则不理你了喵！⚡"
        else:
            if check_count > 2:
                header = "ฅ(≧∇≦)ฅ 知道啦知道啦！主人今天超棒的！"
                comment = (
                    f"今天已经累计提交了 **{total_today_commits}** 次代码喵！"
                    "不用反复确认，喵喵都记在小本本上了喵~ ☕"
                )
            else:
                header = "(⁠ •̀⁠ ω⁠ •̀⁠ )⁠✧ 收到！报告已绑定项目的最新进度喵："
                comment = (
                    f"今天一共推进了 **{total_today_commits}** 个 Commit 喵！"
                    "好感度正在上升中，主人加油冲冲冲！✨"
                )

    return (
        f"{header}\n\n"
        f"💬 **喵喵评价**：{comment}\n\n"
        f"🛠️ **项目最新进度列表**：\n{body}"
        f"💖 **当前状态**：{title} (好感度: `{fav}`)"
    )
