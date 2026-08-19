import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

from bot.commands.check import check_command
from bot.commands.interaction import status_command
from bot.commands.repositories import bind_command, list_command
from bot.commands.start import start_command
from bot.menu import post_init
from core.config import TIMEZONE_BEIJING
from database import connection
from database.patrol_repository import save_next_patrol_at
from database.repo_repository import add_repo, update_repo_stats
from database.schema import init_db
from database.user_repository import add_favorability, register_user
from services.messages import (
    TELEGRAM_MAX_TEXT_LENGTH,
    generate_overview_text,
    generate_patrol_messages,
    generate_patrol_text,
)
from services.overview import RepoOverviewResult
from tests.helpers import FakeContext, FakeUpdate, make_overview
from utils.markdown import safe_md


class MessageTests(unittest.TestCase):
    def test_overview_contains_totals_metadata_stale_and_partial_states_only(self):
        fetched_at = datetime(2026, 8, 18, 8, tzinfo=timezone.utc)
        first = make_overview(
            "Owner/re_po",
            stars=10,
            forks=3,
            subscribers=2,
            open_prs=4,
            closed_prs=5,
            open_issues=6,
            closed_issues=7,
            archived=True,
            title="must-not-appear",
            body="must-not-appear",
            commit_message="must-not-appear",
        )
        second = make_overview(
            "Other/Repo",
            stars=1,
            forks=2,
            subscribers=3,
            open_prs=1,
            closed_prs=2,
            issues_enabled=False,
            open_issues=None,
            closed_issues=None,
            disabled=True,
        )
        results = [
            RepoOverviewResult("Owner/re_po", first, fetched_at, True),
            RepoOverviewResult("Other/Repo", second, fetched_at, False),
            RepoOverviewResult("Missing/Repo", None, None, False),
        ]

        text = generate_overview_text(results)

        self.assertIn("Star `11`", text)
        self.assertIn("Fork `5`", text)
        self.assertIn("关注者 `5`", text)
        self.assertIn("PR：待处理 `5` ｜ 已处理 `7`", text)
        self.assertIn("Issue：待处理 `6` ｜ 已处理 `7`", text)
        self.assertIn("默认分支：main", text)
        self.assertIn("主要语言：Python", text)
        self.assertIn("许可证：MIT", text)
        self.assertIn("2026-08-18 12:00", text)
        self.assertIn("已归档", text)
        self.assertIn("已禁用", text)
        self.assertIn("未启用 Issue", text)
        self.assertIn("陈旧快照", text)
        self.assertIn("暂时无法获取", text)
        self.assertIn("Owner/re\\_po", text)
        self.assertNotIn("must-not-appear", text)
        self.assertNotIn("Commit", text)

    def test_patrol_message_keeps_at_most_three_commit_details(self):
        commits = [
            {
                "time": f"08-18 1{index}:00",
                "sha": f"abc000{index}",
                "msg": f"message {index}",
                "author": "author",
            }
            for index in range(5)
        ]
        text = generate_patrol_text(
            [
                {
                    "repo_path": "Owner/Repo",
                    "count": 5,
                    "commits": commits,
                },
                {"repo_path": "Other/Repo", "unavailable": True},
            ],
            fav=20,
        )

        self.assertIn("message 0", text)
        self.assertIn("message 2", text)
        self.assertNotIn("message 3", text)
        self.assertIn("等共 5 条 Commit", text)
        self.assertIn("已跳过统计与奖励", text)
        self.assertIn("过去 24 小时", text)

    def test_single_oversized_commit_detail_is_markdown_safely_truncated(self):
        long_message = safe_md("long_*[message]\\" * 1200)
        messages = generate_patrol_messages(
            [
                {
                    "repo_path": "Owner/Oversized",
                    "count": 1,
                    "commits": [
                        {
                            "time": "08-18 10:00",
                            "sha": "abc0001",
                            "msg": long_message,
                            "author": "author",
                        }
                    ],
                }
            ],
            fav=15,
            reward=5,
        )

        self.assertGreater(len(messages), 1)
        self.assertTrue(
            all(len(message) <= TELEGRAM_MAX_TEXT_LENGTH for message in messages)
        )
        combined = "\n\n".join(messages)
        self.assertIn("完整检查到 **1** 个 Commit", combined)
        self.assertEqual(combined.count("过去 24 小时巡逻结算"), 1)
        self.assertEqual(combined.count("**当前状态**"), 1)
        self.assertEqual(
            combined.count("https://github.com/Owner/Oversized"),
            1,
        )
        self.assertIn("…", combined)
        self.assertTrue(
            all(not line.endswith("\\") for line in combined.splitlines())
        )


class CheckSideEffectTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db_patch = patch.object(connection, "DB_FILE", self.db_path)
        self.db_patch.start()
        init_db()
        register_user(1, 10)
        add_favorability(1, 25)
        add_repo(1, "Owner/Repo")
        update_repo_stats(1, "Owner/Repo", 9, "2026-08-18")
        save_next_patrol_at(datetime(2026, 8, 20, 4, tzinfo=timezone.utc))

    async def asyncTearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def protected_state(self):
        with sqlite3.connect(self.db_path) as conn:
            user_state = conn.execute(
                "SELECT favorability, pats_today, last_pat_date FROM users WHERE user_id = 1"
            ).fetchone()
            repo_state = conn.execute(
                """
                SELECT last_commit_count, last_check_date
                FROM repos WHERE user_id = 1 AND repo_path = 'Owner/Repo'
                """
            ).fetchone()
            patrol_state = conn.execute(
                "SELECT next_run_at FROM patrol_schedule WHERE id = 1"
            ).fetchone()
        return user_state, repo_state, patrol_state

    async def test_all_check_result_paths_leave_reward_and_schedule_state_unchanged(self):
        data = make_overview()
        paths = {
            "success": [RepoOverviewResult("Owner/Repo", data, None, False)],
            "cache-hit": [RepoOverviewResult("Owner/Repo", data, None, False)],
            "partial": [
                RepoOverviewResult("Owner/Repo", data, None, False),
                RepoOverviewResult("Other/Repo", None, None, False),
            ],
            "no-cache-failure": [
                RepoOverviewResult("Owner/Repo", None, None, False)
            ],
        }

        for name, overview_results in paths.items():
            with self.subTest(path=name):
                before = self.protected_state()
                update = FakeUpdate()
                with patch(
                    "bot.commands.check.get_project_overviews",
                    new=AsyncMock(return_value=overview_results),
                ):
                    await check_command(update, FakeContext())
                self.assertEqual(self.protected_state(), before)
                self.assertEqual(len(update.message.replies), 1)

    async def test_no_bound_repo_keeps_existing_guidance_and_skips_overview(self):
        update = FakeUpdate(user_id=2, chat_id=20)
        fetch_overviews = AsyncMock()
        with patch(
            "bot.commands.check.get_project_overviews",
            new=fetch_overviews,
        ):
            await check_command(update, FakeContext())

        fetch_overviews.assert_not_awaited()
        self.assertIn("请先发送 `/bind", update.message.replies[0]["text"])


class LargeOverviewCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_large_overview_is_sent_in_complete_repository_chunks(self):
        fetched_at = datetime(2026, 8, 18, 8, tzinfo=timezone.utc)
        repo_rows = []
        overview_results = []
        repo_paths = []

        for index in range(35):
            owner = f"owner{index:02d}" + "o" * 32
            repo_name = f"repo{index:02d}-" + "r" * 92
            repo_path = f"{owner}/{repo_name}"
            repo_paths.append(repo_path)
            repo_rows.append((repo_path, 0, ""))
            overview_results.append(
                RepoOverviewResult(
                    repo_path,
                    make_overview(
                        repo_path,
                        default_branch=f"branch-{index:02d}-" + "b" * 240,
                        language="Language" + "g" * 40,
                        license=f"License-{index:02d}-" + "l" * 240,
                        archived=index % 2 == 0,
                        disabled=index % 3 == 0,
                    ),
                    fetched_at,
                    True,
                )
            )

        update = FakeUpdate()
        with (
            patch("bot.commands.check.register_user"),
            patch("bot.commands.check.get_user_repos", return_value=repo_rows),
            patch(
                "bot.commands.check.get_project_overviews",
                new=AsyncMock(return_value=overview_results),
            ),
        ):
            await check_command(update, FakeContext())

        messages = [reply["text"] for reply in update.message.replies]
        self.assertGreater(len(messages), 1)
        self.assertTrue(
            all(len(message) <= TELEGRAM_MAX_TEXT_LENGTH for message in messages)
        )
        self.assertIn("**合计**", messages[0])
        self.assertTrue(all("**合计**" not in message for message in messages[1:]))

        combined = "\n\n".join(messages)
        for repo_path in repo_paths:
            self.assertEqual(
                combined.count(f"https://github.com/{repo_path}"),
                1,
            )
        self.assertTrue(
            all(reply["parse_mode"] == "Markdown" for reply in update.message.replies)
        )


class CommandBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def test_private_repo_validation_never_reaches_persistence(self):
        update = FakeUpdate()
        context = FakeContext(args=["Owner/Private"])
        add_repo_mock = Mock()
        with (
            patch("bot.commands.repositories.register_user"),
            patch(
                "bot.commands.repositories.fetch_public_repo_metadata",
                new=AsyncMock(return_value=None),
            ),
            patch("bot.commands.repositories.add_repo", add_repo_mock),
        ):
            await bind_command(update, context)

        add_repo_mock.assert_not_called()
        self.assertIn("找不到 GitHub 仓库", update.message.replies[-1]["text"])

    async def test_start_list_and_menu_describe_new_behavior(self):
        start_update = FakeUpdate()
        with patch("bot.commands.start.register_user"):
            await start_command(start_update, FakeContext())
        start_text = start_update.message.replies[0]["text"]
        self.assertIn("项目总览", start_text)
        self.assertIn("法定工作日 10:00–17:00", start_text)
        self.assertIn("遗漏的 Commit 不会补算", start_text)
        self.assertNotIn("检查所有已绑定仓库的今日 Commit", start_text)

        list_update = FakeUpdate()
        with (
            patch("bot.commands.repositories.register_user"),
            patch(
                "bot.commands.repositories.get_user_repos",
                return_value=[("Owner/Repo", 0, "")],
            ),
        ):
            await list_command(list_update, FakeContext())
        list_text = list_update.message.replies[0]["text"]
        self.assertIn("Star、PR、Issue", list_text)
        self.assertIn("法定工作日 10:00–17:00", list_text)

        bot = SimpleNamespace(set_my_commands=AsyncMock())
        application = SimpleNamespace(bot=bot)
        await post_init(application)
        commands = bot.set_my_commands.await_args.args[0]
        check_description = next(
            command.description for command in commands if command.command == "check"
        )
        self.assertEqual(check_description, "查看已绑定仓库项目总览")

        status_update = FakeUpdate()
        with (
            patch("bot.commands.interaction.register_user"),
            patch(
                "bot.commands.interaction.get_user",
                return_value=(10, 0, ""),
            ),
            patch(
                "bot.commands.interaction.get_user_repos",
                return_value=[("Owner/Repo", 0, "")],
            ),
        ):
            await status_command(status_update, FakeContext())
        status_text = status_update.message.replies[0]["text"]
        self.assertIn("随机巡逻会抽查过去 24 小时 Commit", status_text)
        self.assertNotIn("每次产生新 Commit 均会增加", status_text)


class ConfigurationTests(unittest.TestCase):
    def test_iana_timezone_and_optional_configuration_are_declared(self):
        self.assertEqual(TIMEZONE_BEIJING.key, "Asia/Shanghai")
        env_example = Path(".env.example").read_text(encoding="utf-8")
        requirements = Path("requirements.txt").read_text(encoding="utf-8")
        self.assertIn("GITHUB_TOKEN=", env_example)
        self.assertIn("chinesecalendar>=1.11.0", requirements)


if __name__ == "__main__":
    unittest.main()
