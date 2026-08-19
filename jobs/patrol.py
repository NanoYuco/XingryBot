import logging
import random
from collections.abc import Callable
from datetime import datetime

from telegram.ext import ContextTypes

from core.config import TIMEZONE_BEIJING
from database.patrol_repository import (
    clear_next_patrol_at,
    get_next_patrol_at,
    save_next_patrol_at,
)
from database.repo_repository import get_user_repos
from database.user_repository import add_favorability, get_all_users
from jobs.patrol_time import (
    CalendarUnavailableError,
    add_patrol_seconds,
    is_patrol_time,
)
from services.messages import generate_patrol_messages
from services.progress import collect_patrol_progress


MIN_PATROL_SECONDS = 15 * 3600
MAX_PATROL_SECONDS = 60 * 3600
CALENDAR_RETRY_SECONDS = 24 * 3600


def _current_time() -> datetime:
    return datetime.now(TIMEZONE_BEIJING)


def _register_target(job_queue, target: datetime, now: datetime) -> None:
    delay = max(0.0, (target - now).total_seconds())
    job_queue.run_once(scheduled_check_job, when=delay)
    logging.info("Next patrol scheduled for %s.", target.isoformat())


def _schedule_calendar_retry(
    job_queue,
    *,
    preserve_target: bool = False,
) -> None:
    if not preserve_target:
        clear_next_patrol_at()
    job_queue.run_once(
        retry_patrol_scheduling_job,
        when=CALENDAR_RETRY_SECONDS,
    )
    logging.error(
        "Patrol scheduling paused because the holiday calendar is unavailable; "
        "a low-frequency retry was scheduled."
    )


def schedule_new_patrol(
    job_queue,
    *,
    now: datetime | None = None,
    randint: Callable[[int, int], int] | None = None,
) -> datetime | None:
    current_time = now or _current_time()
    random_integer = randint or random.randint
    patrol_seconds = random_integer(MIN_PATROL_SECONDS, MAX_PATROL_SECONDS)

    try:
        target = add_patrol_seconds(current_time, patrol_seconds)
    except CalendarUnavailableError:
        _schedule_calendar_retry(job_queue)
        return None

    save_next_patrol_at(target)
    _register_target(job_queue, target, current_time)
    return target


def schedule_initial_patrol(
    job_queue,
    *,
    now: datetime | None = None,
    randint: Callable[[int, int], int] | None = None,
) -> datetime | None:
    current_time = now or _current_time()
    persisted_target = get_next_patrol_at()

    if persisted_target is not None and persisted_target > current_time:
        try:
            target_is_valid = is_patrol_time(persisted_target)
        except CalendarUnavailableError:
            _schedule_calendar_retry(job_queue, preserve_target=True)
            return None
        if target_is_valid:
            _register_target(job_queue, persisted_target, current_time)
            return persisted_target

    return schedule_new_patrol(
        job_queue,
        now=current_time,
        randint=randint,
    )


async def retry_patrol_scheduling_job(context: ContextTypes.DEFAULT_TYPE):
    schedule_initial_patrol(context.job_queue, now=_current_time())


async def _run_patrol_for_users(
    context: ContextTypes.DEFAULT_TYPE,
    baseline: datetime,
) -> None:
    for user_id, chat_id, fav in get_all_users():
        try:
            if not get_user_repos(user_id):
                continue

            results, total_commits = await collect_patrol_progress(
                user_id,
                baseline,
            )
            reward = 0
            if total_commits > 0:
                reward = total_commits * 5
                add_favorability(user_id, reward)
                fav += reward

            texts = generate_patrol_messages(results, fav, reward=reward)
            for text in texts:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
        except Exception:
            logging.error("Failed to process one patrol recipient.")


async def scheduled_check_job(context: ContextTypes.DEFAULT_TYPE):
    baseline = _current_time()
    calendar_failed = False

    try:
        if is_patrol_time(baseline):
            await _run_patrol_for_users(context, baseline)
        else:
            logging.warning("Skipped a patrol callback outside the legal window.")
    except CalendarUnavailableError:
        calendar_failed = True
        _schedule_calendar_retry(context.job_queue)
    except Exception:
        logging.error("Patrol execution failed.")

    if not calendar_failed:
        schedule_new_patrol(context.job_queue, now=_current_time())
