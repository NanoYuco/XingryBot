import os
import unittest
from datetime import date, datetime

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

from core.config import TIMEZONE_BEIJING
from jobs.patrol_time import (
    CalendarUnavailableError,
    add_patrol_seconds,
    is_patrol_day,
    is_patrol_time,
)


def no_holidays(_day: date) -> bool:
    return False


class PatrolTimeTests(unittest.TestCase):
    def local(self, year, month, day, hour, minute=0, second=0):
        return datetime(
            year,
            month,
            day,
            hour,
            minute,
            second,
            tzinfo=TIMEZONE_BEIJING,
        )

    def test_window_includes_ten_and_excludes_seventeen(self):
        self.assertTrue(
            is_patrol_time(self.local(2026, 3, 2, 10), no_holidays)
        )
        self.assertTrue(
            is_patrol_time(
                self.local(2026, 3, 2, 16, 59, 59),
                no_holidays,
            )
        )
        self.assertFalse(
            is_patrol_time(self.local(2026, 3, 2, 17), no_holidays)
        )

    def test_fifteen_patrol_hours_cross_multiple_days(self):
        result = add_patrol_seconds(
            self.local(2026, 3, 2, 10),
            15 * 3600,
            no_holidays,
        )
        self.assertEqual(result, self.local(2026, 3, 4, 11))

    def test_sixty_patrol_hours_skip_weekend(self):
        result = add_patrol_seconds(
            self.local(2026, 3, 2, 10),
            60 * 3600,
            no_holidays,
        )
        self.assertEqual(result, self.local(2026, 3, 12, 14))

    def test_exact_seventeen_boundary_moves_to_next_opening(self):
        result = add_patrol_seconds(
            self.local(2026, 3, 2, 16),
            3600,
            no_holidays,
        )
        self.assertEqual(result, self.local(2026, 3, 3, 10))

    def test_night_and_weekend_time_do_not_consume_interval(self):
        night_result = add_patrol_seconds(
            self.local(2026, 3, 2, 20),
            3600,
            no_holidays,
        )
        weekend_result = add_patrol_seconds(
            self.local(2026, 3, 7, 12),
            3600,
            no_holidays,
        )
        self.assertEqual(night_result, self.local(2026, 3, 3, 11))
        self.assertEqual(weekend_result, self.local(2026, 3, 9, 11))

    def test_holiday_is_skipped_without_consuming_seconds(self):
        holiday = date(2026, 3, 3)
        result = add_patrol_seconds(
            self.local(2026, 3, 2, 16),
            2 * 3600,
            lambda day: day == holiday,
        )
        self.assertEqual(result, self.local(2026, 3, 4, 11))

    def test_real_calendar_rejects_holiday_and_makeup_weekend(self):
        self.assertFalse(is_patrol_day(date(2026, 10, 1)))
        self.assertFalse(is_patrol_day(date(2026, 10, 10)))

    def test_unsupported_year_and_calendar_failure_are_safe_errors(self):
        with self.assertRaises(CalendarUnavailableError):
            is_patrol_time(self.local(2027, 1, 4, 10))

        def broken_calendar(_day):
            raise RuntimeError("calendar unavailable")

        with self.assertRaises(CalendarUnavailableError):
            add_patrol_seconds(
                self.local(2026, 3, 2, 10),
                3600,
                broken_calendar,
            )

    def test_naive_datetimes_and_invalid_intervals_are_rejected(self):
        with self.assertRaises(ValueError):
            add_patrol_seconds(datetime(2026, 3, 2, 10), 1, no_holidays)
        with self.assertRaises(TypeError):
            add_patrol_seconds(
                self.local(2026, 3, 2, 10),
                1.5,
                no_holidays,
            )
        with self.assertRaises(ValueError):
            add_patrol_seconds(
                self.local(2026, 3, 2, 10),
                -1,
                no_holidays,
            )


if __name__ == "__main__":
    unittest.main()
