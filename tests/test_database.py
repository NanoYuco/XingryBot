import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

from database import connection
from database.overview_repository import (
    get_repo_overview_snapshot,
    save_repo_overview_snapshot,
)
from database.patrol_repository import (
    clear_next_patrol_at,
    get_next_patrol_at,
    save_next_patrol_at,
)
from database.schema import init_db
from jobs.patrol import schedule_new_patrol
from jobs.patrol_time import is_patrol_time
from tests.helpers import make_overview


class FakeJobQueue:
    def __init__(self):
        self.calls = []

    def run_once(self, callback, *, when):
        self.calls.append((callback, when))


class DatabaseCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db_patch = patch.object(connection, "DB_FILE", self.db_path)
        self.db_patch.start()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def create_legacy_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    favorability INTEGER DEFAULT 0,
                    pats_today INTEGER DEFAULT 0,
                    last_pat_date TEXT DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE repos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    repo_path TEXT NOT NULL,
                    last_commit_count INTEGER DEFAULT 0,
                    last_check_date TEXT DEFAULT '',
                    UNIQUE(user_id, repo_path)
                )
                """
            )
            conn.execute(
                "INSERT INTO users VALUES (1, 10, 23, 2, '2026-08-18')"
            )
            conn.execute(
                """
                INSERT INTO repos (
                    user_id, repo_path, last_commit_count, last_check_date
                ) VALUES (1, 'Owner/Repo', 9, '2026-08-18')
                """
            )

    def test_init_is_idempotent_and_preserves_legacy_rows_and_columns(self):
        self.create_legacy_database()
        init_db()
        init_db()

        with sqlite3.connect(self.db_path) as conn:
            user = conn.execute("SELECT * FROM users WHERE user_id = 1").fetchone()
            repo = conn.execute(
                """
                SELECT repo_path, last_commit_count, last_check_date
                FROM repos WHERE user_id = 1
                """
            ).fetchone()
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

        self.assertEqual(user, (1, 10, 23, 2, "2026-08-18"))
        self.assertEqual(repo, ("Owner/Repo", 9, "2026-08-18"))
        self.assertIn("patrol_schedule", tables)
        self.assertIn("repo_overview_snapshots", tables)

    def test_patrol_target_round_trips_as_aware_utc_and_can_be_cleared(self):
        init_db()
        target = datetime(2026, 8, 20, 4, 30, tzinfo=timezone.utc)
        save_next_patrol_at(target)
        self.assertEqual(get_next_patrol_at(), target)

        clear_next_patrol_at()
        self.assertIsNone(get_next_patrol_at())

    def test_overview_snapshot_is_shared_by_normalized_repo_path(self):
        init_db()
        fetched_at = datetime(2026, 8, 18, 8, 0, tzinfo=timezone.utc)
        snapshot = make_overview("Owner/Repo")
        save_repo_overview_snapshot("Owner/Repo", snapshot, fetched_at)

        loaded = get_repo_overview_snapshot("owner/repo")
        self.assertEqual(loaded, (snapshot, fetched_at))

    def test_persistence_rejects_naive_times(self):
        init_db()
        with self.assertRaises(ValueError):
            save_next_patrol_at(datetime(2026, 8, 18, 10))
        with self.assertRaises(ValueError):
            save_repo_overview_snapshot(
                "Owner/Repo",
                make_overview(),
                datetime(2026, 8, 18, 10),
            )

    def test_real_scheduler_persists_a_legal_future_target(self):
        init_db()
        now = datetime(2026, 8, 18, 2, 0, tzinfo=timezone.utc)
        queue = FakeJobQueue()

        target = schedule_new_patrol(
            queue,
            now=now,
            randint=lambda _low, _high: 15 * 3600,
        )

        self.assertEqual(get_next_patrol_at(), target.astimezone(timezone.utc))
        self.assertTrue(is_patrol_time(target))
        self.assertGreater(queue.calls[0][1], 10)


if __name__ == "__main__":
    unittest.main()
