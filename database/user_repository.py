from database.connection import get_connection


def register_user(user_id: int, chat_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, chat_id)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET chat_id = excluded.chat_id
            """,
            (user_id, chat_id),
        )


def get_user(user_id: int):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT favorability, pats_today, last_pat_date
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()


def get_all_users():
    with get_connection() as conn:
        return conn.execute(
            "SELECT user_id, chat_id, favorability FROM users"
        ).fetchall()


def add_favorability(user_id: int, amount: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET favorability = favorability + ? WHERE user_id = ?",
            (amount, user_id),
        )


def update_pat(user_id: int, pats: int, pat_date: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE users
            SET pats_today = ?, last_pat_date = ?
            WHERE user_id = ?
            """,
            (pats, pat_date, user_id),
        )
