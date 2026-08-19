import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

from database.overview_repository import (
    get_repo_overview_snapshot,
    save_repo_overview_snapshot,
)
from github.client import fetch_repo_overview


OVERVIEW_CACHE_TTL = timedelta(minutes=10)
_REQUIRED_SNAPSHOT_KEYS = {
    "repo_path",
    "stars",
    "forks",
    "subscribers",
    "open_prs",
    "closed_prs",
    "issues_enabled",
    "open_issues",
    "closed_issues",
    "default_branch",
    "language",
    "license",
    "pushed_at",
    "archived",
    "disabled",
}


@dataclass(frozen=True)
class RepoOverviewResult:
    requested_repo: str
    data: dict | None
    fetched_at: datetime | None
    stale: bool


OverviewFetcher = Callable[[str], Awaitable[dict | None]]


def _is_complete_snapshot(snapshot: object) -> bool:
    return isinstance(snapshot, dict) and _REQUIRED_SNAPSHOT_KEYS <= snapshot.keys()


async def get_repo_overview(
    repo_path: str,
    *,
    now: datetime | None = None,
    fetcher: OverviewFetcher | None = None,
) -> RepoOverviewResult:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("overview time must be timezone-aware")
    current_time = current_time.astimezone(timezone.utc)

    cached = get_repo_overview_snapshot(repo_path)
    if cached:
        snapshot, fetched_at = cached
        age = current_time - fetched_at.astimezone(timezone.utc)
        if timedelta(0) <= age < OVERVIEW_CACHE_TTL:
            return RepoOverviewResult(repo_path, snapshot, fetched_at, False)

    fetch = fetcher or fetch_repo_overview
    try:
        refreshed = await fetch(repo_path)
    except Exception:
        logging.error("Failed to refresh one repository overview.")
        refreshed = None
    if _is_complete_snapshot(refreshed):
        save_repo_overview_snapshot(repo_path, refreshed, current_time)
        return RepoOverviewResult(repo_path, refreshed, current_time, False)

    if cached:
        snapshot, fetched_at = cached
        return RepoOverviewResult(repo_path, snapshot, fetched_at, True)
    return RepoOverviewResult(repo_path, None, None, False)


async def get_project_overviews(
    repo_rows: list | tuple,
    *,
    now: datetime | None = None,
    fetcher: OverviewFetcher | None = None,
) -> list[RepoOverviewResult]:
    results = []
    for repo_path, *_ in repo_rows:
        results.append(
            await get_repo_overview(
                repo_path,
                now=now,
                fetcher=fetcher,
            )
        )
    return results
