import sqlite3

from core.config import DB_FILE


def get_connection() -> sqlite3.Connection:
    """Create a SQLite connection to the configured database file."""
    return sqlite3.connect(DB_FILE)
