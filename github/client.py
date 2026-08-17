import logging
from datetime import datetime, timedelta

import aiohttp

from core.config import (
    GITHUB_REQUEST_TIMEOUT,
    GITHUB_USER_AGENT,
    TIMEZONE_BEIJING,
)
from utils.markdown import safe_md


async def _fetch_commits(repo_path: str, per_page: int):
    url = f"https://api.github.com/repos/{repo_path}/commits?per_page={per_page}"
    headers = {"User-Agent": GITHUB_USER_AGENT}
    timeout = aiohttp.ClientTimeout(total=GITHUB_REQUEST_TIMEOUT)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return None
            return await response.json()


async def fetch_repo_today_commits(repo_path: str):
    try:
        commits_raw = await _fetch_commits(repo_path, per_page=30)
        if commits_raw is None:
            return None

        now = datetime.now(TIMEZONE_BEIJING)
        today_str = now.strftime("%Y-%m-%d")
        today_commits = []

        for commit in commits_raw:
            date_str = commit["commit"]["committer"]["date"]
            commit_time = datetime.fromisoformat(
                date_str.replace("Z", "+00:00")
            ).astimezone(TIMEZONE_BEIJING)

            if commit_time.strftime("%Y-%m-%d") != today_str:
                continue

            message = commit["commit"]["message"].split("\n")[0]
            author = commit["commit"]["author"].get("name") or "Unknown"
            today_commits.append(
                {
                    "sha": commit["sha"][:7],
                    "msg": safe_md(message),
                    "author": safe_md(author),
                    "time": commit_time.strftime("%H:%M"),
                }
            )

        return {
            "repo_path": repo_path,
            "today_commits": today_commits,
            "today_count": len(today_commits),
            "today_str": today_str,
        }
    except Exception as exc:
        logging.exception("GitHub Fetch Error for %s: %s", repo_path, exc)
        return None


async def fetch_repo_weekly_commits(repo_path: str):
    try:
        commits_raw = await _fetch_commits(repo_path, per_page=100)
        if commits_raw is None:
            return None

        now = datetime.now(TIMEZONE_BEIJING)
        seven_days_ago = now - timedelta(days=7)
        weekly_commits = []

        for commit in commits_raw:
            date_str = commit["commit"]["committer"]["date"]
            commit_time = datetime.fromisoformat(
                date_str.replace("Z", "+00:00")
            ).astimezone(TIMEZONE_BEIJING)

            if commit_time < seven_days_ago:
                continue

            message = commit["commit"]["message"].split("\n")[0]
            author = commit["commit"]["author"].get("name") or "Unknown"
            weekly_commits.append(
                {
                    "sha": commit["sha"][:7],
                    "msg": safe_md(message),
                    "author": safe_md(author),
                    "date": commit_time.strftime("%m-%d %H:%M"),
                }
            )

        return {
            "repo_path": repo_path,
            "count": len(weekly_commits),
            "commits": weekly_commits,
        }
    except Exception as exc:
        logging.exception("Weekly Fetch Error for %s: %s", repo_path, exc)
        return None
