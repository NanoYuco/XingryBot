from datetime import datetime, timezone

from database.connection import get_connection


def get_next_patrol_at() -> datetime | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT next_run_at FROM patrol_schedule WHERE id = 1"
        ).fetchone()

    if not row:
        return None

    try:
        value = datetime.fromisoformat(row[0])
    except (TypeError, ValueError):
        return None

    if value.tzinfo is None or value.utcoffset() is None:
        return None
    return value


def save_next_patrol_at(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("next patrol time must be timezone-aware")

    value_utc = value.astimezone(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO patrol_schedule (id, next_run_at)
            VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET next_run_at = excluded.next_run_at
            """,
            (value_utc,),
        )


def clear_next_patrol_at() -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM patrol_schedule WHERE id = 1")
