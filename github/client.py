import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Mapping
from urllib.parse import parse_qs, quote, urlparse

import aiohttp

from core.config import (
    GITHUB_API_BASE_URL,
    GITHUB_API_VERSION,
    GITHUB_REQUEST_TIMEOUT,
    GITHUB_TOKEN,
    GITHUB_USER_AGENT,
    TIMEZONE_BEIJING,
)
from utils.markdown import safe_md


@dataclass(frozen=True)
class GitHubResponse:
    status: int
    data: Any
    headers: Mapping[str, str]


_rate_limited_until = 0.0


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": GITHUB_USER_AGENT,
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _header(headers: Mapping[str, str], name: str) -> str | None:
    wanted = name.casefold()
    for key, value in headers.items():
        if key.casefold() == wanted:
            return value
    return None


def _record_rate_limit(headers: Mapping[str, str]) -> None:
    global _rate_limited_until

    now = time.time()
    candidates = []
    retry_after = _header(headers, "Retry-After")
    if retry_after:
        try:
            candidates.append(now + max(0, int(retry_after)))
        except ValueError:
            try:
                retry_time = parsedate_to_datetime(retry_after)
                candidates.append(retry_time.timestamp())
            except (TypeError, ValueError, OverflowError):
                pass

    reset_at = _header(headers, "X-RateLimit-Reset")
    if reset_at:
        try:
            candidates.append(float(reset_at))
        except ValueError:
            pass

    candidates = [candidate for candidate in candidates if candidate > now]
    if not candidates:
        candidates.append(now + 60)
    _rate_limited_until = max(_rate_limited_until, *candidates)


def _make_session() -> aiohttp.ClientSession:
    timeout = aiohttp.ClientTimeout(total=GITHUB_REQUEST_TIMEOUT)
    return aiohttp.ClientSession(timeout=timeout)


async def _request_json(
    session: aiohttp.ClientSession,
    path: str,
    *,
    params: Mapping[str, str | int] | None = None,
) -> GitHubResponse:
    if time.time() < _rate_limited_until:
        return GitHubResponse(status=429, data=None, headers={})

    url = f"{GITHUB_API_BASE_URL}{path}"
    try:
        async with session.get(
            url,
            headers=_github_headers(),
            params=params,
        ) as response:
            headers = dict(response.headers)
            if response.status in {403, 429}:
                _record_rate_limit(headers)
                logging.warning("GitHub rate limit active; requests paused temporarily.")

            try:
                data = await response.json(content_type=None)
            except (aiohttp.ContentTypeError, ValueError):
                data = None
            return GitHubResponse(
                status=response.status,
                data=data,
                headers=headers,
            )
    except (aiohttp.ClientError, TimeoutError):
        logging.warning("GitHub request failed due to a network error.")
        return GitHubResponse(status=0, data=None, headers={})


def _repo_api_path(repo_path: str) -> str:
    normalized = repo_path.strip().strip("/")
    return f"/repos/{quote(normalized, safe='/')}"


async def _fetch_public_repo_metadata_with_session(
    session: aiohttp.ClientSession,
    repo_path: str,
) -> dict | None:
    response = await _request_json(session, _repo_api_path(repo_path))
    if response.status != 200 or not isinstance(response.data, dict):
        return None

    metadata = response.data
    visibility = metadata.get("visibility", "public")
    if metadata.get("private") is not False or visibility != "public":
        logging.warning("GitHub repository access rejected because it is not public.")
        return None
    return metadata


async def fetch_public_repo_metadata(repo_path: str) -> dict | None:
    async with _make_session() as session:
        return await _fetch_public_repo_metadata_with_session(session, repo_path)


def _github_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_commit_time(commit: dict) -> datetime:
    date_str = commit["commit"]["committer"]["date"]
    parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("GitHub commit time is not timezone-aware")
    return parsed


def _format_commit(commit: dict, commit_time: datetime) -> dict:
    commit_data = commit["commit"]
    author_data = commit_data.get("author") or {}
    message = str(commit_data["message"]).split("\n")[0]
    author = author_data.get("name") or "Unknown"
    return {
        "sha": str(commit["sha"])[:7],
        "msg": safe_md(message),
        "author": safe_md(author),
        "time": commit_time.astimezone(TIMEZONE_BEIJING).strftime("%m-%d %H:%M"),
    }


def _is_empty_repository_response(response: GitHubResponse) -> bool:
    if response.status != 409 or not isinstance(response.data, dict):
        return False
    message = response.data.get("message")
    if not isinstance(message, str):
        return False
    normalized_message = message.strip().rstrip(".").strip().casefold()
    return normalized_message == "git repository is empty"


async def _fetch_repo_commits_between_with_session(
    session: aiohttp.ClientSession,
    repo_path: str,
    window_start: datetime,
    window_end: datetime,
) -> dict | None:
    metadata = await _fetch_public_repo_metadata_with_session(session, repo_path)
    if metadata is None:
        return None

    page = 1
    commits_raw = []
    while True:
        response = await _request_json(
            session,
            f"{_repo_api_path(repo_path)}/commits",
            params={
                "per_page": 100,
                "page": page,
                "since": _github_timestamp(window_start),
                "until": _github_timestamp(window_end),
            },
        )
        if page == 1 and _is_empty_repository_response(response):
            break
        if response.status != 200 or not isinstance(response.data, list):
            return None

        commits_raw.extend(response.data)
        if len(response.data) < 100:
            break
        page += 1

    commits = []
    try:
        for commit in commits_raw:
            commit_time = _parse_commit_time(commit)
            if window_start <= commit_time <= window_end:
                commits.append(_format_commit(commit, commit_time))
    except (KeyError, TypeError, ValueError):
        logging.warning("GitHub commit response could not be parsed completely.")
        return None

    canonical_path = metadata.get("full_name") or repo_path
    return {
        "repo_path": str(canonical_path),
        "commits": commits,
        "count": len(commits),
        "window_start": window_start.astimezone(timezone.utc).isoformat(),
        "window_end": window_end.astimezone(timezone.utc).isoformat(),
    }


async def fetch_repo_commits_window(
    repo_path: str,
    window_end: datetime,
) -> dict | None:
    if window_end.tzinfo is None or window_end.utcoffset() is None:
        raise ValueError("commit window end must be timezone-aware")
    window_start = window_end - timedelta(hours=24)

    async with _make_session() as session:
        return await _fetch_repo_commits_between_with_session(
            session,
            repo_path,
            window_start,
            window_end,
        )


async def fetch_repo_today_commits(repo_path: str):
    now = datetime.now(TIMEZONE_BEIJING)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    async with _make_session() as session:
        result = await _fetch_repo_commits_between_with_session(
            session,
            repo_path,
            day_start,
            now,
        )
    if result is None:
        return None

    today_commits = []
    for commit in result["commits"]:
        item = dict(commit)
        item["time"] = item["time"].split(" ", 1)[-1]
        today_commits.append(item)
    return {
        "repo_path": result["repo_path"],
        "today_commits": today_commits,
        "today_count": result["count"],
        "today_str": now.strftime("%Y-%m-%d"),
    }


def _last_page_count(response: GitHubResponse) -> int | None:
    if response.status != 200 or not isinstance(response.data, list):
        return None
    if not response.data:
        return 0

    link_header = _header(response.headers, "Link")
    if not link_header:
        return len(response.data)

    for part in link_header.split(","):
        if 'rel="last"' not in part:
            continue
        url_part = part.split(";", 1)[0].strip().strip("<>")
        page_values = parse_qs(urlparse(url_part).query).get("page")
        if page_values:
            try:
                return int(page_values[0])
            except ValueError:
                return None
    return len(response.data)


async def _count_collection(
    session: aiohttp.ClientSession,
    path: str,
    state: str,
) -> int | None:
    response = await _request_json(
        session,
        path,
        params={"state": state, "per_page": 1},
    )
    return _last_page_count(response)


def _license_name(metadata: dict) -> str | None:
    license_data = metadata.get("license")
    if not isinstance(license_data, dict):
        return None
    spdx_id = license_data.get("spdx_id")
    if spdx_id and spdx_id != "NOASSERTION":
        return str(spdx_id)
    name = license_data.get("name")
    return str(name) if name else None


async def fetch_repo_overview(repo_path: str) -> dict | None:
    async with _make_session() as session:
        metadata = await _fetch_public_repo_metadata_with_session(session, repo_path)
        if metadata is None:
            return None

        pulls_path = f"{_repo_api_path(repo_path)}/pulls"
        issues_path = f"{_repo_api_path(repo_path)}/issues"
        open_prs = await _count_collection(session, pulls_path, "open")
        if open_prs is None:
            return None
        closed_prs = await _count_collection(session, pulls_path, "closed")
        if closed_prs is None:
            return None

        issues_enabled = bool(metadata.get("has_issues", False))
        open_issues = None
        closed_issues = None
        if issues_enabled:
            open_items = await _count_collection(session, issues_path, "open")
            if open_items is None:
                return None
            closed_items = await _count_collection(session, issues_path, "closed")
            if closed_items is None:
                return None
            open_issues = max(0, open_items - open_prs)
            closed_issues = max(0, closed_items - closed_prs)

        try:
            return {
                "repo_path": str(metadata.get("full_name") or repo_path),
                "stars": int(metadata["stargazers_count"]),
                "forks": int(metadata["forks_count"]),
                "subscribers": int(metadata["subscribers_count"]),
                "open_prs": open_prs,
                "closed_prs": closed_prs,
                "issues_enabled": issues_enabled,
                "open_issues": open_issues,
                "closed_issues": closed_issues,
                "default_branch": str(metadata.get("default_branch") or "未知"),
                "language": metadata.get("language"),
                "license": _license_name(metadata),
                "pushed_at": metadata.get("pushed_at"),
                "archived": bool(metadata.get("archived", False)),
                "disabled": bool(metadata.get("disabled", False)),
            }
        except (KeyError, TypeError, ValueError):
            logging.warning("GitHub repository metadata could not be parsed completely.")
            return None


async def fetch_repo_weekly_commits(repo_path: str):
    now = datetime.now(TIMEZONE_BEIJING)
    seven_days_ago = now - timedelta(days=7)
    async with _make_session() as session:
        metadata = await _fetch_public_repo_metadata_with_session(session, repo_path)
        if metadata is None:
            return None
        response = await _request_json(
            session,
            f"{_repo_api_path(repo_path)}/commits",
            params={"per_page": 100},
        )
    if _is_empty_repository_response(response):
        commits_raw = []
    elif response.status == 200 and isinstance(response.data, list):
        commits_raw = response.data
    else:
        return None

    commits = []
    try:
        for commit in commits_raw:
            commit_time = _parse_commit_time(commit)
            if commit_time < seven_days_ago:
                continue
            item = _format_commit(commit, commit_time)
            item["date"] = item.pop("time")
            commits.append(item)
    except (KeyError, TypeError, ValueError):
        logging.warning("GitHub weekly commit response could not be parsed completely.")
        return None

    return {
        "repo_path": str(metadata.get("full_name") or repo_path),
        "count": len(commits),
        "commits": commits,
    }
