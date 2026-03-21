# config.py
import os

# 必需的配置
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN 环境变量未设置")

# 数据库配置
DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/wolf_recs.db")

# 速率限制
RATE_LIMIT_SECONDS = int(os.getenv("RATE_LIMIT_SECONDS", "25"))

# 评价最小长度
MIN_REASON_LENGTH = 12

# 管理员ID白名单
ADMIN_IDS = []
admin_ids_str = os.getenv("ADMIN_IDS", "")
if admin_ids_str:
    try:
        ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
    except ValueError:
        raise ValueError("❌ ADMIN_IDS 格式错误，应为逗号分隔的数字")

if not ADMIN_IDS:
    raise ValueError("❌ ADMIN_IDS 未设置，至少需要一个管理员ID")

# 频道链接
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/your_channel")

# 热门搜索关键词
HOT_TRIGGER_WORDS = ["排行榜", "top", "hot", "热门榜", "老师排行", "热门排名", "榜单"]

# 日志级别
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")