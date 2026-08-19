from datetime import datetime
from urllib.parse import quote

from telegram.constants import MessageLimit

from core.config import TIMEZONE_BEIJING
from services.favorability import get_fav_info
from utils.markdown import safe_md


TELEGRAM_MAX_TEXT_LENGTH = int(MessageLimit.MAX_TEXT_LENGTH)


def _repo_link(repo_path: str) -> str:
    label = safe_md(repo_path)
    url_path = quote(repo_path.strip().strip("/"), safe="/")
    return f"[{label}](https://github.com/{url_path})"


def _truncate_markdown_line(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    if max_length <= 0:
        raise ValueError("Markdown line length limit must be positive")

    marker = "…"
    truncated = text[: max_length - len(marker)]
    trailing_backslashes = len(truncated) - len(truncated.rstrip("\\"))
    if trailing_backslashes % 2:
        truncated = truncated[:-1]
    return f"{truncated}{marker}"


def _generate_patrol_repo_section(
    result: dict,
    *,
    max_length: int | None = None,
) -> str:
    repo_path = result["repo_path"]
    header = f"📁 **{_repo_link(repo_path)}**："
    detail_lines = []
    tail_lines = []

    if result.get("unavailable"):
        tail_lines.append("  • 本次未能完整获取，已跳过统计与奖励")
    elif result["count"]:
        for commit in result["commits"][:3]:
            detail_lines.append(
                f"  • `{commit['time']}` [{commit['sha']}] "
                f"{commit['msg']} (by {commit['author']})"
            )
        if result["count"] > 3:
            tail_lines.append(f"  ...等共 {result['count']} 条 Commit")
    else:
        tail_lines.append("  • 过去 24 小时暂无 Commit 提交")

    lines = [header, *detail_lines, *tail_lines]
    section = "\n".join(lines)
    if max_length is None or len(section) <= max_length:
        return section

    fixed_length = len(header) + sum(len(line) for line in tail_lines)
    newline_count = len(lines) - 1
    detail_budget = max_length - fixed_length - newline_count
    if not detail_lines or detail_budget < len(detail_lines):
        raise ValueError("repository patrol section exceeds the message length limit")

    detail_limit = detail_budget // len(detail_lines)
    truncated_lines = [
        _truncate_markdown_line(line, detail_limit) for line in detail_lines
    ]
    section = "\n".join([header, *truncated_lines, *tail_lines])
    if len(section) > max_length:
        raise ValueError("repository patrol section exceeds the message length limit")
    return section


def _generate_patrol_parts(
    results: list,
    fav: int,
    *,
    section_max_length: int | None = None,
) -> tuple[str, str, list[str], str, int]:
    lvl, title, _ = get_fav_info(fav)
    successful = [result for result in results if not result.get("unavailable")]
    unavailable_count = len(results) - len(successful)
    total_commits = sum(result["count"] for result in successful)

    repo_sections = [
        _generate_patrol_repo_section(
            result,
            max_length=section_max_length,
        )
        for result in results
    ]

    if total_commits == 0:
        if unavailable_count:
            header = "🐾 喵~ 随机巡逻完成，但有项目暂时看不清喵！"
            comment = "能完整检查到的仓库在过去 24 小时没有 Commit；获取失败的仓库没有参与结算，稍后再看看喵。"
        elif lvl == 1:
            header = "ฅ(>ω<)ฅ 喵呜！突查！喵喵悄悄摸过来巡逻喵！"
            comment = "过去 24 小时居然 **0 提交** 喵？！主人是不是又在摸鱼！快去写代码！⚡"
        elif lvl <= 3:
            header = "🐾 喵~ 随机巡逻时间到！"
            comment = "过去 24 小时还没有新进度喵，主人是不是遇到讨厌的 Bug 了？要休息一下吗喵~ ☕"
        else:
            header = "ฅ(≧∇≦)ฅ 主人~ 喵喵悄悄摸过来看看你啦！"
            comment = "过去 24 小时虽然没有 Commit，但喵喵会一直陪在主人身边的喵！要按时休息哦~ ✨"
    else:
        header = "ฅ(≧∇≦)ฅ 喵嗷！巡逻发现 Git 项目有新进度啦！"
        comment = (
            f"过去 24 小时完整检查到 **{total_commits}** 个 Commit 喵！"
            "主人敲代码的样子真的超级帅气！(ฅ'ω'ฅ)"
        )

    intro = f"{header}\n\n💬 **喵喵评价**：{comment}"
    section_heading = "🛠️ **过去 24 小时项目巡逻**："
    status = f"💖 **当前状态**：{title} (好感度: `{fav}`)"
    return intro, section_heading, repo_sections, status, total_commits


def generate_patrol_text(results: list, fav: int) -> str:
    intro, section_heading, repo_sections, status, _ = _generate_patrol_parts(
        results,
        fav,
    )
    body = "\n\n".join(repo_sections)
    return f"{intro}\n\n{section_heading}\n{body}\n\n{status}"


def generate_patrol_messages(
    results: list,
    fav: int,
    *,
    reward: int = 0,
    max_length: int = TELEGRAM_MAX_TEXT_LENGTH,
) -> list[str]:
    """Split a patrol at repository boundaries within Telegram's text limit."""
    if max_length <= 0:
        raise ValueError("message length limit must be positive")

    intro, section_heading, repo_sections, status, _ = _generate_patrol_parts(
        results,
        fav,
        section_max_length=max_length,
    )
    summary_parts = [intro, status]
    if reward > 0:
        summary_parts.append(
            f"✨ **过去 24 小时巡逻结算：好感度 +{reward} 喵！**"
        )
    summary_parts.append(section_heading)
    summary = "\n\n".join(summary_parts)
    if len(summary) > max_length:
        raise ValueError("patrol summary exceeds the message length limit")

    messages = []
    current = summary
    for section in repo_sections:
        candidate = f"{current}\n\n{section}" if current else section
        if len(candidate) <= max_length:
            current = candidate
            continue

        messages.append(current)
        current = section

    if current:
        messages.append(current)
    return messages


def _format_github_time(value: object) -> str:
    if not value:
        return "未知"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return "未知"
        return parsed.astimezone(TIMEZONE_BEIJING).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return "未知"


def _display_value(value: object, fallback: str = "未提供") -> str:
    if value is None or value == "":
        return fallback
    return safe_md(str(value))


def _generate_overview_parts(results: list) -> tuple[str, list[str]]:
    available = [result for result in results if result.data is not None]
    stale_count = sum(1 for result in available if result.stale)
    unavailable_count = len(results) - len(available)

    totals = {
        "stars": sum(result.data["stars"] for result in available),
        "forks": sum(result.data["forks"] for result in available),
        "subscribers": sum(result.data["subscribers"] for result in available),
        "open_prs": sum(result.data["open_prs"] for result in available),
        "closed_prs": sum(result.data["closed_prs"] for result in available),
        "open_issues": sum(
            result.data["open_issues"]
            for result in available
            if result.data["issues_enabled"]
        ),
        "closed_issues": sum(
            result.data["closed_issues"]
            for result in available
            if result.data["issues_enabled"]
        ),
    }
    issues_disabled = sum(
        1 for result in available if not result.data["issues_enabled"]
    )

    summary_lines = [
        "ฅ'ω'ฅ **主人绑定项目总览**",
        "",
        f"📊 **合计**（可用 `{len(available)}/{len(results)}` 个仓库）：",
        f"• Star `{totals['stars']}` ｜ Fork `{totals['forks']}` ｜ 关注者 `{totals['subscribers']}`",
        f"• PR：待处理 `{totals['open_prs']}` ｜ 已处理 `{totals['closed_prs']}`",
        f"• Issue：待处理 `{totals['open_issues']}` ｜ 已处理 `{totals['closed_issues']}`",
    ]
    notes = []
    if issues_disabled:
        notes.append(f"`{issues_disabled}` 个仓库未启用 Issue")
    if stale_count:
        notes.append(f"`{stale_count}` 个仓库使用陈旧快照")
    if unavailable_count:
        notes.append(f"`{unavailable_count}` 个仓库暂时不可用")
    if notes:
        summary_lines.append("• 说明：" + "；".join(notes))

    repo_sections = []
    for result in results:
        if result.data is None:
            repo_sections.append(
                f"📁 **{_repo_link(result.requested_repo)}**\n"
                "• ⚠️ 项目总览暂时无法获取，请稍后再试喵"
            )
            continue

        data = result.data
        states = []
        if data["archived"]:
            states.append("已归档")
        if data["disabled"]:
            states.append("已禁用")
        if not data["issues_enabled"]:
            states.append("未启用 Issue")
        state_text = "、".join(states) if states else "正常"

        if data["issues_enabled"]:
            issue_line = (
                f"• Issue：待处理 `{data['open_issues']}` ｜ "
                f"已处理 `{data['closed_issues']}`"
            )
        else:
            issue_line = "• Issue：未启用"

        freshness = ""
        if result.stale and result.fetched_at:
            fetched_at = result.fetched_at.astimezone(TIMEZONE_BEIJING).strftime(
                "%Y-%m-%d %H:%M"
            )
            freshness = f"\n• ⚠️ 陈旧快照，获取于 `{fetched_at}`"

        repo_sections.append(
            f"📁 **{_repo_link(data['repo_path'])}**\n"
            f"• Star `{data['stars']}` ｜ Fork `{data['forks']}` ｜ 关注者 `{data['subscribers']}`\n"
            f"• PR：待处理 `{data['open_prs']}` ｜ 已处理 `{data['closed_prs']}`\n"
            f"{issue_line}\n"
            f"• 默认分支：{_display_value(data['default_branch'])} ｜ 主要语言：{_display_value(data['language'])}\n"
            f"• 许可证：{_display_value(data['license'])} ｜ 最后推送：`{_format_github_time(data['pushed_at'])}`\n"
            f"• 仓库状态：{state_text}{freshness}"
        )

    return "\n".join(summary_lines), repo_sections


def generate_overview_text(results: list) -> str:
    summary, repo_sections = _generate_overview_parts(results)
    return "\n\n".join([summary, *repo_sections])


def generate_overview_messages(
    results: list,
    *,
    max_length: int = TELEGRAM_MAX_TEXT_LENGTH,
) -> list[str]:
    """Split an overview at complete repository-section boundaries."""
    if max_length <= 0:
        raise ValueError("message length limit must be positive")

    summary, repo_sections = _generate_overview_parts(results)
    if len(summary) > max_length:
        raise ValueError("overview summary exceeds the message length limit")

    messages = []
    current = summary
    for section in repo_sections:
        if len(section) > max_length:
            raise ValueError("repository overview exceeds the message length limit")

        candidate = f"{current}\n\n{section}" if current else section
        if len(candidate) <= max_length:
            current = candidate
            continue

        messages.append(current)
        current = section

    if current:
        messages.append(current)
    return messages
