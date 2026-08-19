import sqlite3

from database.connection import get_connection


def add_repo(user_id: int, repo_path: str) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO repos (user_id, repo_path) VALUES (?, ?)",
                (user_id, repo_path),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def remove_repo(user_id: int, repo_path: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM repos WHERE user_id = ? AND repo_path = ?",
            (user_id, repo_path),
        )
        return cursor.rowcount > 0


def get_user_repos(user_id: int):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT repo_path, last_commit_count, last_check_date
            FROM repos
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (user_id,),
        ).fetchall()


def update_repo_stats(
    user_id: int,
    repo_path: str,
    commit_count: int,
    check_date: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE repos
            SET last_commit_count = ?, last_check_date = ?
            WHERE user_id = ? AND repo_path = ?
            """,
            (commit_count, check_date, user_id, repo_path),
        )
