import os
from pathlib import Path
from dotenv import load_dotenv

# .env faylini yuklash
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "bot_database.db"))

report_time = os.getenv("DAILY_REPORT_TIME", "23:30").split(":")
DAILY_REPORT_HOUR = int(report_time[0]) if len(report_time) > 0 else 23
DAILY_REPORT_MINUTE = int(report_time[1]) if len(report_time) > 1 else 30

# Telegram kanallari uchun eng faol vaqtlar (Smart Peak Hours)
# Foydalanuvchi "Faol vaqtda joylash"ni tanlaganda navbatdagi eng yaqin faol soatda chiqariladi
PEAK_HOURS = [
    {"hour": 9, "minute": 0, "label": "Ertalabki faol vaqt (09:00)"},
    {"hour": 13, "minute": 0, "label": "Tushlik faol vaqt (13:00)"},
    {"hour": 18, "minute": 30, "label": "Kechki faol vaqt (18:30)"},
    {"hour": 21, "minute": 0, "label": "Kechki dam olish vaqti (21:00)"},
]
