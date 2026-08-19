import json
from datetime import datetime, timezone

from database.connection import get_connection


def normalize_repo_path(repo_path: str) -> str:
    return repo_path.strip().strip("/").casefold()


def get_repo_overview_snapshot(
    repo_path: str,
) -> tuple[dict, datetime] | None:
    normalized_path = normalize_repo_path(repo_path)
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT snapshot_json, fetched_at
            FROM repo_overview_snapshots
            WHERE repo_path = ?
            """,
            (normalized_path,),
        ).fetchone()

    if not row:
        return None

    try:
        snapshot = json.loads(row[0])
        fetched_at = datetime.fromisoformat(row[1])
    except (TypeError, ValueError, json.JSONDecodeError):
        return None

    if not isinstance(snapshot, dict):
        return None
    if fetched_at.tzinfo is None or fetched_at.utcoffset() is None:
        return None
    return snapshot, fetched_at


def save_repo_overview_snapshot(
    repo_path: str,
    snapshot: dict,
    fetched_at: datetime,
) -> None:
    if fetched_at.tzinfo is None or fetched_at.utcoffset() is None:
        raise ValueError("snapshot time must be timezone-aware")

    normalized_path = normalize_repo_path(repo_path)
    snapshot_json = json.dumps(
        snapshot,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    fetched_at_utc = fetched_at.astimezone(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO repo_overview_snapshots (
                repo_path,
                snapshot_json,
                fetched_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(repo_path) DO UPDATE SET
                snapshot_json = excluded.snapshot_json,
                fetched_at = excluded.fetched_at
            """,
            (normalized_path, snapshot_json, fetched_at_utc),
        )
