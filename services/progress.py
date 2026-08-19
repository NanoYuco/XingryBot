import logging

from database.repo_repository import get_user_repos, update_repo_stats
from github.client import fetch_repo_commits_window, fetch_repo_today_commits


async def collect_today_progress(user_id: int):
    """
    Fetch today's commits for every bound repository, calculate newly observed
    commits, and persist the latest repository counters.

    Returns: (results, total_new_commits)
    """
    repos = get_user_repos(user_id)
    results = []
    total_new_commits = 0

    for repo_path, last_commit_count, last_check_date in repos:
        result = await fetch_repo_today_commits(repo_path)
        if not result:
            continue

        results.append(result)
        today_count = result["today_count"]
        today_str = result["today_str"]

        if last_check_date == today_str:
            diff = today_count - last_commit_count
        else:
            diff = today_count

        if diff > 0:
            total_new_commits += diff

        update_repo_stats(user_id, repo_path, today_count, today_str)

    return results, total_new_commits


async def collect_patrol_progress(user_id: int, baseline):
    """Collect complete commit results for the 24 hours before one patrol."""
    results = []
    total_commits = 0

    for repo_path, _, _ in get_user_repos(user_id):
        try:
            result = await fetch_repo_commits_window(repo_path, baseline)
        except Exception:
            logging.error("Failed to collect one patrol repository.")
            result = None
        if result is None:
            results.append({"repo_path": repo_path, "unavailable": True})
            continue

        results.append(result)
        total_commits += result["count"]

    return results, total_commits
