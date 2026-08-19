import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

from database import connection
from database.overview_repository import (
    get_repo_overview_snapshot,
    save_repo_overview_snapshot,
)
from database.schema import init_db
from services.overview import get_project_overviews, get_repo_overview
from tests.helpers import make_overview


class OverviewCacheTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db_patch = patch.object(connection, "DB_FILE", self.db_path)
        self.db_patch.start()
        init_db()
        self.now = datetime(2026, 8, 18, 8, 0, tzinfo=timezone.utc)

    async def asyncTearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    async def test_cache_miss_fetches_and_persists_complete_snapshot(self):
        snapshot = make_overview()
        fetcher = AsyncMock(return_value=snapshot)

        result = await get_repo_overview(
            "Owner/Repo",
            now=self.now,
            fetcher=fetcher,
        )

        self.assertEqual(result.data, snapshot)
        self.assertFalse(result.stale)
        fetcher.assert_awaited_once_with("Owner/Repo")
        self.assertEqual(
            get_repo_overview_snapshot("owner/repo"),
            (snapshot, self.now),
        )

    async def test_fresh_cache_is_reused_across_repo_case_and_users(self):
        snapshot = make_overview()
        first_fetcher = AsyncMock(return_value=snapshot)
        second_fetcher = AsyncMock(return_value=None)
        await get_repo_overview(
            "Owner/Repo",
            now=self.now,
            fetcher=first_fetcher,
        )

        result = await get_repo_overview(
            "owner/repo",
            now=self.now + timedelta(minutes=9, seconds=59),
            fetcher=second_fetcher,
        )

        self.assertEqual(result.data, snapshot)
        self.assertFalse(result.stale)
        second_fetcher.assert_not_awaited()

    async def test_ten_minute_boundary_refreshes_and_replaces_whole_snapshot(self):
        old_snapshot = make_overview(stars=1, closed_prs=2)
        new_snapshot = make_overview(stars=99, closed_prs=20)
        save_repo_overview_snapshot("Owner/Repo", old_snapshot, self.now)
        fetcher = AsyncMock(return_value=new_snapshot)

        result = await get_repo_overview(
            "Owner/Repo",
            now=self.now + timedelta(minutes=10),
            fetcher=fetcher,
        )

        self.assertEqual(result.data, new_snapshot)
        self.assertFalse(result.stale)
        persisted, persisted_at = get_repo_overview_snapshot("Owner/Repo")
        self.assertEqual(persisted, new_snapshot)
        self.assertEqual(persisted_at, self.now + timedelta(minutes=10))

    async def test_failed_refresh_returns_timestamped_stale_snapshot_unchanged(self):
        old_snapshot = make_overview(stars=8)
        save_repo_overview_snapshot("Owner/Repo", old_snapshot, self.now)
        fetcher = AsyncMock(return_value=None)

        result = await get_repo_overview(
            "Owner/Repo",
            now=self.now + timedelta(minutes=11),
            fetcher=fetcher,
        )

        self.assertEqual(result.data, old_snapshot)
        self.assertTrue(result.stale)
        self.assertEqual(result.fetched_at, self.now)
        self.assertEqual(
            get_repo_overview_snapshot("Owner/Repo"),
            (old_snapshot, self.now),
        )

    async def test_failed_refresh_without_cache_is_repo_level_unavailable(self):
        result = await get_repo_overview(
            "Owner/Missing",
            now=self.now,
            fetcher=AsyncMock(return_value=None),
        )
        self.assertIsNone(result.data)
        self.assertIsNone(result.fetched_at)
        self.assertFalse(result.stale)

    async def test_incomplete_refresh_never_replaces_last_complete_snapshot(self):
        old_snapshot = make_overview(stars=8)
        save_repo_overview_snapshot("Owner/Repo", old_snapshot, self.now)

        result = await get_repo_overview(
            "Owner/Repo",
            now=self.now + timedelta(minutes=11),
            fetcher=AsyncMock(return_value={"repo_path": "Owner/Repo"}),
        )

        self.assertTrue(result.stale)
        self.assertEqual(result.data, old_snapshot)
        self.assertEqual(
            get_repo_overview_snapshot("Owner/Repo"),
            (old_snapshot, self.now),
        )

    async def test_one_repo_failure_does_not_block_other_repositories(self):
        async def fetch(repo_path):
            if repo_path == "Owner/Good":
                return make_overview(repo_path)
            raise RuntimeError("simulated fetch failure")

        results = await get_project_overviews(
            [("Owner/Good", 0, ""), ("Owner/Bad", 0, "")],
            now=self.now,
            fetcher=fetch,
        )

        self.assertEqual(len(results), 2)
        self.assertIsNotNone(results[0].data)
        self.assertIsNone(results[1].data)


if __name__ == "__main__":
    unittest.main()
