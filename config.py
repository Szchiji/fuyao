# config.py
"""
机器人配置文件
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ==================== Telegram Bot 配置 ====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN 未设置")

ADMIN_IDS = []
admin_ids_str = os.getenv("ADMIN_IDS", "")
if admin_ids_str:
    try:
        ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
    except ValueError:
        raise ValueError("❌ ADMIN_IDS 格式错误，必须是数字，用逗号分隔")

# ==================== 数据库配置 ====================
DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    DB_TYPE = "postgres"
else:
    DB_TYPE = "sqlite"
    DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/wolf_recs.db")

# ==================== 常量配置 ====================
MIN_REASON_LENGTH = 12
DAILY_RATING_LIMIT = 0
RATING_RETENTION_DAYS = 0

# ==================== 调试配置 ====================
DEBUG = os.getenv("DEBUG", "False").lower() == "true"