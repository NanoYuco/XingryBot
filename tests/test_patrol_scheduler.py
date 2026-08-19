import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, call, patch

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

from core.config import TIMEZONE_BEIJING
from jobs import patrol
from jobs.scheduler import register_jobs
from jobs.patrol_time import CalendarUnavailableError
from services.messages import TELEGRAM_MAX_TEXT_LENGTH
from tests.helpers import FakeContext


class FakeJobQueue:
    def __init__(self):
        self.calls = []

    def run_once(self, callback, *, when):
        self.calls.append((callback, when))


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)


class LengthCheckingBot(FakeBot):
    def __init__(self, *, fail_chat_id=None, fail_attempt=None):
        super().__init__()
        self.attempts = {}
        self.fail_chat_id = fail_chat_id
        self.fail_attempt = fail_attempt

    async def send_message(self, **kwargs):
        if len(kwargs["text"]) > TELEGRAM_MAX_TEXT_LENGTH:
            raise ValueError("Telegram message is too long")

        chat_id = kwargs["chat_id"]
        attempt = self.attempts.get(chat_id, 0) + 1
        self.attempts[chat_id] = attempt
        if chat_id == self.fail_chat_id and attempt == self.fail_attempt:
            raise RuntimeError("simulated chunk delivery failure")
        self.messages.append(kwargs)


def make_large_patrol_results(repo_count=24, message_length=120):
    results = []
    repo_paths = []
    for repo_index in range(repo_count):
        repo_path = f"Owner/Repo-{repo_index:02d}"
        repo_paths.append(repo_path)
        commits = [
            {
                "time": f"08-18 1{commit_index}:00",
                "sha": f"{repo_index:04d}{commit_index:03d}",
                "msg": (
                    f"message-{repo_index:02d}-{commit_index}-"
                    + "m" * message_length
                ),
                "author": f"author-{repo_index:02d}",
            }
            for commit_index in range(3)
        ]
        results.append(
            {
                "repo_path": repo_path,
                "count": len(commits),
                "commits": commits,
            }
        )
    return results, repo_paths, repo_count * 3


class PatrolSchedulingTests(unittest.TestCase):
    def local(self, day=18, hour=10):
        return datetime(2026, 8, day, hour, tzinfo=TIMEZONE_BEIJING)

    @patch("jobs.patrol.save_next_patrol_at")
    @patch("jobs.patrol.add_patrol_seconds")
    def test_new_schedule_draws_inclusive_integer_bounds_and_persists(
        self,
        add_seconds,
        save_target,
    ):
        now = self.local()
        target = self.local(day=20, hour=11)
        add_seconds.return_value = target
        observed_bounds = []

        def fake_randint(low, high):
            observed_bounds.append((low, high))
            return high

        queue = FakeJobQueue()
        result = patrol.schedule_new_patrol(
            queue,
            now=now,
            randint=fake_randint,
        )

        self.assertEqual(
            observed_bounds,
            [(15 * 3600, 60 * 3600)],
        )
        add_seconds.assert_called_once_with(now, 60 * 3600)
        save_target.assert_called_once_with(target)
        self.assertEqual(result, target)
        self.assertIs(queue.calls[0][0], patrol.scheduled_check_job)
        self.assertEqual(queue.calls[0][1], (target - now).total_seconds())

    @patch("jobs.scheduler.schedule_next_weekly_report")
    @patch("jobs.scheduler.schedule_initial_patrol")
    def test_job_registration_has_no_immediate_ten_second_patrol(
        self,
        schedule_initial,
        schedule_weekly,
    ):
        queue = FakeJobQueue()
        register_jobs(queue)
        schedule_initial.assert_called_once_with(queue)
        schedule_weekly.assert_called_once_with(queue)
        self.assertEqual(queue.calls, [])

    @patch("jobs.patrol.schedule_new_patrol")
    @patch("jobs.patrol.get_next_patrol_at", return_value=None)
    def test_first_start_schedules_full_interval_instead_of_immediate_patrol(
        self,
        _get_target,
        schedule_new,
    ):
        queue = FakeJobQueue()
        now = self.local()
        patrol.schedule_initial_patrol(queue, now=now, randint=Mock())
        schedule_new.assert_called_once()
        self.assertEqual(schedule_new.call_args.kwargs["now"], now)

    @patch("jobs.patrol.save_next_patrol_at")
    @patch("jobs.patrol.is_patrol_time", return_value=True)
    @patch("jobs.patrol.get_next_patrol_at")
    def test_future_persisted_target_is_restored_without_rerandomizing(
        self,
        get_target,
        _is_valid,
        save_target,
    ):
        now = self.local()
        target = now + timedelta(days=2)
        get_target.return_value = target
        randint = Mock()
        queue = FakeJobQueue()

        result = patrol.schedule_initial_patrol(
            queue,
            now=now,
            randint=randint,
        )

        self.assertEqual(result, target)
        randint.assert_not_called()
        save_target.assert_not_called()
        self.assertEqual(queue.calls[0][1], 2 * 24 * 3600)

    @patch("jobs.patrol.schedule_new_patrol")
    @patch("jobs.patrol.get_next_patrol_at")
    def test_expired_target_is_not_replayed(self, get_target, schedule_new):
        now = self.local()
        get_target.return_value = now - timedelta(seconds=1)
        queue = FakeJobQueue()

        patrol.schedule_initial_patrol(queue, now=now)

        schedule_new.assert_called_once_with(queue, now=now, randint=None)
        self.assertEqual(queue.calls, [])

    @patch("jobs.patrol.schedule_new_patrol")
    @patch("jobs.patrol.is_patrol_time", return_value=False)
    @patch("jobs.patrol.get_next_patrol_at")
    def test_invalid_future_target_is_replaced(
        self,
        get_target,
        _is_valid,
        schedule_new,
    ):
        now = self.local()
        get_target.return_value = now + timedelta(days=1)
        queue = FakeJobQueue()
        patrol.schedule_initial_patrol(queue, now=now)
        schedule_new.assert_called_once_with(queue, now=now, randint=None)

    @patch("jobs.patrol.clear_next_patrol_at")
    @patch(
        "jobs.patrol.add_patrol_seconds",
        side_effect=CalendarUnavailableError("unsupported"),
    )
    def test_calendar_failure_stops_patrol_and_uses_low_frequency_retry(
        self,
        _add_seconds,
        clear_target,
    ):
        queue = FakeJobQueue()
        result = patrol.schedule_new_patrol(
            queue,
            now=self.local(),
            randint=lambda _low, _high: 15 * 3600,
        )

        self.assertIsNone(result)
        clear_target.assert_called_once_with()
        self.assertEqual(len(queue.calls), 1)
        self.assertIs(queue.calls[0][0], patrol.retry_patrol_scheduling_job)
        self.assertEqual(queue.calls[0][1], 24 * 3600)


class PatrolCallbackTests(unittest.IsolatedAsyncioTestCase):
    def local(self, hour=10):
        return datetime(2026, 8, 18, hour, tzinfo=TIMEZONE_BEIJING)

    @patch("jobs.patrol.schedule_new_patrol")
    @patch("jobs.patrol._run_patrol_for_users", new_callable=AsyncMock)
    @patch("jobs.patrol.is_patrol_time", return_value=False)
    @patch("jobs.patrol._current_time")
    async def test_illegal_callback_does_not_send_and_reschedules(
        self,
        current_time,
        _is_valid,
        run_users,
        schedule_new,
    ):
        baseline = self.local(hour=18)
        after = self.local(hour=18) + timedelta(seconds=1)
        current_time.side_effect = [baseline, after]
        context = FakeContext(job_queue=FakeJobQueue())

        await patrol.scheduled_check_job(context)

        run_users.assert_not_awaited()
        schedule_new.assert_called_once_with(context.job_queue, now=after)

    @patch("jobs.patrol.schedule_new_patrol")
    @patch("jobs.patrol._schedule_calendar_retry")
    @patch(
        "jobs.patrol.is_patrol_time",
        side_effect=CalendarUnavailableError("unsupported"),
    )
    @patch("jobs.patrol._current_time")
    async def test_calendar_error_callback_never_sends_or_random_retries(
        self,
        current_time,
        _is_valid,
        schedule_retry,
        schedule_new,
    ):
        current_time.return_value = self.local()
        context = FakeContext(job_queue=FakeJobQueue())

        await patrol.scheduled_check_job(context)

        schedule_retry.assert_called_once_with(context.job_queue)
        schedule_new.assert_not_called()

    async def test_calendar_retry_restores_same_future_persisted_target(self):
        now = self.local()
        retry_now = now + timedelta(hours=24)
        target = now + timedelta(days=3)
        queue = FakeJobQueue()
        calendar_check = Mock(
            side_effect=[
                CalendarUnavailableError("temporary calendar failure"),
                True,
            ]
        )

        with (
            patch("jobs.patrol.get_next_patrol_at", return_value=target),
            patch("jobs.patrol.is_patrol_time", calendar_check),
            patch("jobs.patrol.clear_next_patrol_at") as clear_target,
            patch("jobs.patrol.random.randint") as randint,
            patch("jobs.patrol.add_patrol_seconds") as add_seconds,
            patch("jobs.patrol.save_next_patrol_at") as save_target,
            patch("jobs.patrol._current_time", return_value=retry_now),
        ):
            first_result = patrol.schedule_initial_patrol(queue, now=now)
            await patrol.retry_patrol_scheduling_job(
                FakeContext(job_queue=queue)
            )

        self.assertIsNone(first_result)
        clear_target.assert_not_called()
        randint.assert_not_called()
        add_seconds.assert_not_called()
        save_target.assert_not_called()
        self.assertEqual(calendar_check.call_count, 2)
        self.assertIs(queue.calls[0][0], patrol.retry_patrol_scheduling_job)
        self.assertEqual(queue.calls[0][1], 24 * 3600)
        self.assertIs(queue.calls[1][0], patrol.scheduled_check_job)
        self.assertEqual(queue.calls[1][1], (target - retry_now).total_seconds())

    async def test_calendar_retry_draws_full_interval_only_after_target_expires(self):
        now = self.local()
        persisted_target = now + timedelta(hours=12)
        retry_now = now + timedelta(hours=24)
        new_target = retry_now + timedelta(days=3)
        queue = FakeJobQueue()
        calendar_check = Mock(
            side_effect=CalendarUnavailableError("temporary calendar failure")
        )

        with (
            patch(
                "jobs.patrol.get_next_patrol_at",
                return_value=persisted_target,
            ),
            patch("jobs.patrol.is_patrol_time", calendar_check),
            patch("jobs.patrol.clear_next_patrol_at") as clear_target,
            patch(
                "jobs.patrol.random.randint",
                return_value=patrol.MIN_PATROL_SECONDS,
            ) as randint,
            patch(
                "jobs.patrol.add_patrol_seconds",
                return_value=new_target,
            ) as add_seconds,
            patch("jobs.patrol.save_next_patrol_at") as save_target,
            patch("jobs.patrol._current_time", return_value=retry_now),
        ):
            first_result = patrol.schedule_initial_patrol(queue, now=now)
            await patrol.retry_patrol_scheduling_job(
                FakeContext(job_queue=queue)
            )

        self.assertIsNone(first_result)
        clear_target.assert_not_called()
        calendar_check.assert_called_once_with(persisted_target)
        randint.assert_called_once_with(
            patrol.MIN_PATROL_SECONDS,
            patrol.MAX_PATROL_SECONDS,
        )
        add_seconds.assert_called_once_with(retry_now, patrol.MIN_PATROL_SECONDS)
        save_target.assert_called_once_with(new_target)
        self.assertIs(queue.calls[0][0], patrol.retry_patrol_scheduling_job)
        self.assertIs(queue.calls[1][0], patrol.scheduled_check_job)

    @patch("jobs.patrol.add_favorability")
    @patch("jobs.patrol.collect_patrol_progress", new_callable=AsyncMock)
    @patch("jobs.patrol.get_user_repos")
    @patch("jobs.patrol.get_all_users")
    async def test_one_baseline_is_shared_and_only_complete_counts_are_rewarded(
        self,
        get_users,
        get_repos,
        collect_progress,
        add_favorability,
    ):
        baseline = self.local()
        get_users.return_value = [(1, 10, 0), (2, 20, 5)]
        get_repos.return_value = [("Owner/Repo", 0, "")]
        collect_progress.side_effect = [
            (
                [
                    {
                        "repo_path": "Owner/Repo",
                        "count": 2,
                        "commits": [],
                    }
                ],
                2,
            ),
            ([{"repo_path": "Other/Repo", "unavailable": True}], 0),
        ]
        bot = FakeBot()
        context = FakeContext(bot=bot)

        await patrol._run_patrol_for_users(context, baseline)

        self.assertEqual(
            collect_progress.await_args_list,
            [call(1, baseline), call(2, baseline)],
        )
        add_favorability.assert_called_once_with(1, 10)
        self.assertEqual(len(bot.messages), 2)
        self.assertIn("好感度 +10", bot.messages[0]["text"])
        self.assertNotIn("好感度 +", bot.messages[1]["text"])

    async def test_large_patrol_is_split_with_complete_results_and_one_reward(self):
        results, repo_paths, total_commits = make_large_patrol_results()
        bot = LengthCheckingBot()
        context = FakeContext(bot=bot)

        with (
            patch("jobs.patrol.get_all_users", return_value=[(1, 10, 20)]),
            patch(
                "jobs.patrol.get_user_repos",
                return_value=[("Owner/Repo-00", 0, "")],
            ),
            patch(
                "jobs.patrol.collect_patrol_progress",
                new=AsyncMock(return_value=(results, total_commits)),
            ),
            patch("jobs.patrol.add_favorability") as add_favorability,
        ):
            await patrol._run_patrol_for_users(context, self.local())

        reward = total_commits * 5
        add_favorability.assert_called_once_with(1, reward)
        self.assertGreater(len(bot.messages), 1)
        self.assertEqual(bot.attempts[10], len(bot.messages))
        self.assertTrue(
            all(
                len(message["text"]) <= TELEGRAM_MAX_TEXT_LENGTH
                for message in bot.messages
            )
        )

        combined = "\n\n".join(message["text"] for message in bot.messages)
        self.assertEqual(combined.count("巡逻发现 Git 项目有新进度啦"), 1)
        self.assertEqual(combined.count("完整检查到"), 1)
        self.assertEqual(combined.count("**过去 24 小时项目巡逻**"), 1)
        self.assertEqual(combined.count("**当前状态**"), 1)
        self.assertEqual(combined.count("过去 24 小时巡逻结算"), 1)
        self.assertIn(f"好感度 +{reward}", combined)
        for repo_path in repo_paths:
            self.assertEqual(
                combined.count(f"https://github.com/{repo_path}"),
                1,
            )
        self.assertTrue(
            all(message["parse_mode"] == "Markdown" for message in bot.messages)
        )

    async def test_mid_chunk_failure_stops_that_user_but_continues_next_user(self):
        large_results, _, total_commits = make_large_patrol_results(
            repo_count=30,
        )
        next_user_results = [
            {
                "repo_path": "Other/Repo",
                "count": 0,
                "commits": [],
            }
        ]
        bot = LengthCheckingBot(fail_chat_id=10, fail_attempt=2)
        context = FakeContext(bot=bot)

        with (
            patch(
                "jobs.patrol.get_all_users",
                return_value=[(1, 10, 0), (2, 20, 5)],
            ),
            patch(
                "jobs.patrol.get_user_repos",
                return_value=[("Owner/Repo", 0, "")],
            ),
            patch(
                "jobs.patrol.collect_patrol_progress",
                new=AsyncMock(
                    side_effect=[
                        (large_results, total_commits),
                        (next_user_results, 0),
                    ]
                ),
            ) as collect_progress,
            patch("jobs.patrol.add_favorability") as add_favorability,
        ):
            await patrol._run_patrol_for_users(context, self.local())

        add_favorability.assert_called_once_with(1, total_commits * 5)
        self.assertEqual(collect_progress.await_count, 2)
        self.assertEqual(bot.attempts[10], 2)
        self.assertEqual(bot.attempts[20], 1)

        first_user_messages = [
            message for message in bot.messages if message["chat_id"] == 10
        ]
        second_user_messages = [
            message for message in bot.messages if message["chat_id"] == 20
        ]
        self.assertEqual(len(first_user_messages), 1)
        self.assertEqual(len(second_user_messages), 1)
        self.assertIn(
            f"好感度 +{total_commits * 5}",
            first_user_messages[0]["text"],
        )
        self.assertIn("Other/Repo", second_user_messages[0]["text"])


if __name__ == "__main__":
    unittest.main()
