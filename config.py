# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot 配置
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

# 频道配置
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "")

# ============ 数据库配置 ============

# 使用 PostgreSQL (Railway)
DATABASE_URL = os.getenv("DATABASE_URL")

# 如果没有 PostgreSQL，则使用本地 SQLite
if DATABASE_URL:
    # PostgreSQL 模式
    DB_TYPE = "postgres"
else:
    # SQLite 模式
    DB_TYPE = "sqlite"
    DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/wolf_recs.db")

# 频道链接
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "")

# 常量配置
MIN_REASON_LENGTH = 12
DAILY_RATING_LIMIT = 0
RATING_RETENTION_DAYS = 0
DEBUG = os.getenv("DEBUG", "False").lower() == "true"