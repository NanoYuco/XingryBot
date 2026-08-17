import os
from datetime import timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

_db_file = os.getenv("DB_FILE", "cat_xingry.db").strip() or "cat_xingry.db"
DB_FILE = Path(_db_file)
if not DB_FILE.is_absolute():
    DB_FILE = BASE_DIR / DB_FILE

TIMEZONE_BEIJING = timezone(timedelta(hours=8))

GITHUB_USER_AGENT = "XingryTelegramBot/1.0"
GITHUB_REQUEST_TIMEOUT = 10
