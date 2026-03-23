# config.py
"""
机器人配置文件
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ==================== Telegram Bot 配置 ====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN 未设置")

# ⭐ 关键修复：正确解析 ADMIN_IDS
ADMIN_IDS = []
admin_ids_str = os.getenv("ADMIN_IDS", "")

logger.info(f"📝 原始 ADMIN_IDS 字符串: '{admin_ids_str}'")

if admin_ids_str:
    try:
        # 处理多种格式：
        # "123456789"
        # "123456789,987654321"
        # " 123456789 , 987654321 "
        ADMIN_IDS = [
            int(x.strip()) 
            for x in admin_ids_str.split(",") 
            if x.strip().isdigit()
        ]
        logger.info(f"✅ 成功解析 ADMIN_IDS: {ADMIN_IDS}")
    except ValueError as e:
        logger.error(f"❌ ADMIN_IDS 格式错误: {e}")
        logger.error(f"❌ 请确保 ADMIN_IDS 是数字，用逗号分隔")
        logger.error(f"❌ 例如: ADMIN_IDS=123456789,987654321")
        raise

if not ADMIN_IDS:
    logger.warning("⚠️ 警告：ADMIN_IDS 为空！无人可以使用管理员命令")

# ==================== 数据库配置 ====================
DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    DB_TYPE = "postgres"
    logger.info(f"📝 使用 PostgreSQL 数据库")
else:
    DB_TYPE = "sqlite"
    DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/wolf_recs.db")
    logger.info(f"📝 使用 SQLite 数据库: {DATABASE_PATH}")

# ==================== 常量配置 ====================
MIN_REASON_LENGTH = int(os.getenv("MIN_REASON_LENGTH", "12"))
if MIN_REASON_LENGTH < 1:
    raise ValueError(f"❌ MIN_REASON_LENGTH 必须大于 0，当前值: {MIN_REASON_LENGTH}")

DAILY_RATING_LIMIT = int(os.getenv("DAILY_RATING_LIMIT", "0"))
RATING_RETENTION_DAYS = int(os.getenv("RATING_RETENTION_DAYS", "0"))

# ==================== 调试配置 ====================
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

if DEBUG:
    logger.info("🔧 调试模式已启用")