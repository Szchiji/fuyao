# config.py
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN 未设置，请在 Railway Variables 中添加")

REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL")   # 示例：-1001234567890
REQUIRED_GROUP   = os.getenv("REQUIRED_GROUP")     # 示例：-1009876543210
if not REQUIRED_CHANNEL or not REQUIRED_GROUP:
    raise ValueError("REQUIRED_CHANNEL 或 REQUIRED_GROUP 未设置")

CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/+xxxxxxxxxxxx")
GROUP_LINK   = os.getenv("GROUP_LINK", "https://t.me/+yyyyyyyyyyyy")

DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/wolf_recs.db")

RATE_LIMIT_SECONDS = int(os.getenv("RATE_LIMIT_SECONDS", "30"))

HOT_TRIGGER_WORDS = os.getenv(
    "HOT_TRIGGER_WORDS",
    "排行榜,top,hot,热门榜,老师排行,狼友热门,热门排名,榜单,排名"
).split(",")

SEARCH_TRIGGER_WORDS = os.getenv(
    "SEARCH_TRIGGER_WORDS",
    "搜,搜索,找,查,查老师,搜老师,找老师,老师搜,搜寻"
).split(",")

MAX_REASON_PREVIEW = 10
MAX_TOP_RANK = 10
