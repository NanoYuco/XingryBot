from collections.abc import Callable
from datetime import date, datetime, time, timedelta

from core.config import TIMEZONE_BEIJING

try:
    from chinese_calendar import is_holiday as _calendar_is_holiday
except Exception:
    _calendar_is_holiday = None


PATROL_WINDOW_START = time(10, 0)
PATROL_WINDOW_END = time(17, 0)


class CalendarUnavailableError(RuntimeError):
    """Raised when the offline holiday calendar cannot answer safely."""


HolidayChecker = Callable[[date], bool]


def _as_shanghai(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("patrol time must be timezone-aware")
    return value.astimezone(TIMEZONE_BEIJING)


def _holiday_for(day: date, holiday_checker: HolidayChecker | None) -> bool:
    checker = holiday_checker or _calendar_is_holiday
    if checker is None:
        raise CalendarUnavailableError("holiday calendar is unavailable")

    try:
        return bool(checker(day))
    except Exception as exc:
        raise CalendarUnavailableError(
            "holiday calendar cannot evaluate the requested date"
        ) from exc


def is_patrol_day(
    day: date,
    holiday_checker: HolidayChecker | None = None,
) -> bool:
    if day.weekday() >= 5:
        return False
    return not _holiday_for(day, holiday_checker)


def is_patrol_time(
    value: datetime,
    holiday_checker: HolidayChecker | None = None,
) -> bool:
    local_value = _as_shanghai(value)
    if not is_patrol_day(local_value.date(), holiday_checker):
        return False
    local_time = local_value.timetz().replace(tzinfo=None)
    return PATROL_WINDOW_START <= local_time < PATROL_WINDOW_END


def _next_open_window(
    value: datetime,
    holiday_checker: HolidayChecker | None,
) -> datetime:
    cursor = _as_shanghai(value)

    while True:
        current_day = cursor.date()
        if is_patrol_day(current_day, holiday_checker):
            window_start = datetime.combine(
                current_day,
                PATROL_WINDOW_START,
                tzinfo=TIMEZONE_BEIJING,
            )
            window_end = datetime.combine(
                current_day,
                PATROL_WINDOW_END,
                tzinfo=TIMEZONE_BEIJING,
            )
            if cursor < window_start:
                return window_start
            if cursor < window_end:
                return cursor

        next_day = current_day + timedelta(days=1)
        cursor = datetime.combine(
            next_day,
            PATROL_WINDOW_START,
            tzinfo=TIMEZONE_BEIJING,
        )


def add_patrol_seconds(
    start: datetime,
    patrol_seconds: int,
    holiday_checker: HolidayChecker | None = None,
) -> datetime:
    if not isinstance(patrol_seconds, int) or isinstance(patrol_seconds, bool):
        raise TypeError("patrol seconds must be an integer")
    if patrol_seconds < 0:
        raise ValueError("patrol seconds must not be negative")

    cursor = _next_open_window(start, holiday_checker)
    remaining = float(patrol_seconds)

    while True:
        window_end = datetime.combine(
            cursor.date(),
            PATROL_WINDOW_END,
            tzinfo=TIMEZONE_BEIJING,
        )
        available = (window_end - cursor).total_seconds()

        if remaining < available:
            return cursor + timedelta(seconds=remaining)

        remaining -= available
        cursor = _next_open_window(window_end, holiday_checker)
        if remaining == 0:
            return cursor
