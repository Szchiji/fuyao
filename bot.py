# bot.py
import asyncio
import logging
import os
from pathlib import Path

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import TELEGRAM_BOT_TOKEN
from database import init_db
from bot_instance import bot

# 导入路由处理器
from handlers.private import router as private_router
from handlers.group import router as group_router
from handlers.callback import router as callback_router
from handlers.admin import router as admin_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建数据库目录
db_dir = Path(os.getenv("DATABASE_PATH", "/app/data/wolf_recs.db")).parent
db_dir.mkdir(parents=True, exist_ok=True)

# 创建 Dispatcher
dp = Dispatcher(storage=MemoryStorage())

# 注册所有路由
dp.include_router(private_router)
dp.include_router(group_router)
dp.include_router(callback_router)
dp.include_router(admin_router)

async def main():
    """启动机器人"""
    try:
        init_db()
        logger.info("✅ 数据库初始化成功")
        logger.info("✅ 狼评机器人已启动")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        raise
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())