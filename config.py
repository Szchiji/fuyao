# config.py
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN 未设置")

DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/wolf_recs.db")
RATE_LIMIT_SECONDS = int(os.getenv("RATE_LIMIT_SECONDS", "25"))
MIN_REASON_LENGTH = 12

# 管理员白名单（支持多个ID，用逗号分隔）
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "123456789").split(",") if x.strip()]

CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/+你的频道hash")

HOT_TRIGGER_WORDS = ["排行榜", "top", "hot", "热门榜", "老师排行", "热门排名", "榜单"]