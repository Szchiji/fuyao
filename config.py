# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot 配置
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

# 频道配置
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "")  # 频道ID，如: -1001811864163

# 数据库配置
DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/wolf_recs.db")

# 频道链接 - 将由机器人自动生成
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "")  # 备用配置，如果自动生成失败就使用这个