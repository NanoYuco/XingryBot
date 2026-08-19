import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

from database import connection
from database.repo_repository import add_repo, update_repo_stats
from database.schema import init_db
from database.user_repository import register_user
from jobs.weekly_report import send_weekly_report_job
from services.messages import generate_patrol_text
from services.progress import collect_patrol_progress
from tests.helpers import FakeContext


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)


class PatrolProgressTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db_patch = patch.object(connection, "DB_FILE", self.db_path)
        self.db_patch.start()
        init_db()
        register_user(1, 10)
        add_repo(1, "Owner/Repo")
        update_repo_stats(1, "Owner/Repo", 12, "2026-08-17")
        self.baseline = datetime(2026, 8, 18, 8, tzinfo=timezone.utc)

    async def asyncTearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def repo_checkpoint(self):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(
                """
                SELECT last_commit_count, last_check_date
                FROM repos WHERE user_id = 1 AND repo_path = 'Owner/Repo'
                """
            ).fetchone()

    async def test_patrol_uses_window_total_without_touching_daily_checkpoint(self):
        complete_result = {
            "repo_path": "Owner/Repo",
            "count": 3,
            "commits": [],
        }
        before = self.repo_checkpoint()
        with patch(
            "services.progress.fetch_repo_commits_window",
            new=AsyncMock(return_value=complete_result),
        ) as fetch:
            results, total = await collect_patrol_progress(1, self.baseline)

        self.assertEqual(results, [complete_result])
        self.assertEqual(total, 3)
        fetch.assert_awaited_once_with("Owner/Repo", self.baseline)
        self.assertEqual(self.repo_checkpoint(), before)

    async def test_incomplete_patrol_repo_never_contributes_partial_reward_count(self):
        with patch(
            "services.progress.fetch_repo_commits_window",
            new=AsyncMock(return_value=None),
        ):
            results, total = await collect_patrol_progress(1, self.baseline)

        self.assertEqual(total, 0)
        self.assertTrue(results[0]["unavailable"])

    async def test_complete_empty_repo_is_reported_as_zero_without_reward_count(self):
        complete_result = {
            "repo_path": "Owner/Repo",
            "count": 0,
            "commits": [],
        }
        with patch(
            "services.progress.fetch_repo_commits_window",
            new=AsyncMock(return_value=complete_result),
        ):
            results, total = await collect_patrol_progress(1, self.baseline)

        self.assertEqual(results, [complete_result])
        self.assertEqual(total, 0)
        text = generate_patrol_text(results, fav=10)
        self.assertIn("过去 24 小时暂无 Commit 提交", text)
        self.assertNotIn("已跳过统计与奖励", text)

    async def test_one_repo_exception_does_not_block_later_patrol_repositories(self):
        add_repo(1, "Other/Repo")
        complete_result = {
            "repo_path": "Other/Repo",
            "count": 2,
            "commits": [],
        }
        with patch(
            "services.progress.fetch_repo_commits_window",
            new=AsyncMock(
                side_effect=[
                    RuntimeError("simulated fetch failure"),
                    complete_result,
                ]
            ),
        ):
            results, total = await collect_patrol_progress(1, self.baseline)

        self.assertTrue(results[0]["unavailable"])
        self.assertEqual(results[1], complete_result)
        self.assertEqual(total, 2)


class WeeklyRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_weekly_report_keeps_plus_twenty_rule_and_reschedules(self):
        bot = FakeBot()
        context = FakeContext(bot=bot, job_queue=object())
        weekly_result = {
            "repo_path": "Owner/Repo",
            "count": 2,
            "commits": [
                {
                    "date": "08-18 10:00",
                    "msg": "safe message",
                    "author": "author",
                }
            ],
        }

        with (
            patch(
                "jobs.weekly_report.get_all_users",
                return_value=[(1, 10, 30)],
            ),
            patch(
                "jobs.weekly_report.get_user_repos",
                return_value=[("Owner/Repo", 0, "")],
            ),
            patch(
                "jobs.weekly_report.fetch_repo_weekly_commits",
                new=AsyncMock(return_value=weekly_result),
            ),
            patch("jobs.weekly_report.add_favorability") as add_favorability,
            patch("jobs.weekly_report.schedule_next_weekly_report") as schedule_next,
        ):
            await send_weekly_report_job(context)

        add_favorability.assert_called_once_with(1, 20)
        schedule_next.assert_called_once_with(context.job_queue)
        self.assertEqual(len(bot.messages), 1)
        self.assertIn("好感度 **+20**", bot.messages[0]["text"])

    async def test_weekly_empty_repo_is_included_as_zero_without_reward(self):
        bot = FakeBot()
        context = FakeContext(bot=bot, job_queue=object())
        weekly_result = {
            "repo_path": "Owner/Repo",
            "count": 0,
            "commits": [],
        }

        with (
            patch(
                "jobs.weekly_report.get_all_users",
                return_value=[(1, 10, 30)],
            ),
            patch(
                "jobs.weekly_report.get_user_repos",
                return_value=[("Owner/Repo", 0, "")],
            ),
            patch(
                "jobs.weekly_report.fetch_repo_weekly_commits",
                new=AsyncMock(return_value=weekly_result),
            ),
            patch("jobs.weekly_report.add_favorability") as add_favorability,
            patch("jobs.weekly_report.schedule_next_weekly_report") as schedule_next,
        ):
            await send_weekly_report_job(context)

        add_favorability.assert_not_called()
        schedule_next.assert_called_once_with(context.job_queue)
        self.assertEqual(len(bot.messages), 1)
        self.assertIn("Owner/Repo", bot.messages[0]["text"])
        self.assertIn("本周提交：`0` 次", bot.messages[0]["text"])


if __name__ == "__main__":
    unittest.main()
