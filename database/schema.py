from database.connection import get_connection


def init_db() -> None:
    """Create required tables if they do not already exist."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
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
            CREATE TABLE IF NOT EXISTS repos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                repo_path TEXT NOT NULL,
                last_commit_count INTEGER DEFAULT 0,
                last_check_date TEXT DEFAULT '',
                UNIQUE(user_id, repo_path)
            )
            """
        )
