import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()

_db_file = os.getenv("DB_FILE", "cat_xingry.db").strip() or "cat_xingry.db"
DB_FILE = Path(_db_file)
if not DB_FILE.is_absolute():
    DB_FILE = BASE_DIR / DB_FILE

TIMEZONE_BEIJING = ZoneInfo("Asia/Shanghai")

GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"
GITHUB_USER_AGENT = "XingryTelegramBot/1.0"
GITHUB_REQUEST_TIMEOUT = 10
