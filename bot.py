# bot.py
import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import TELEGRAM_BOT_TOKEN
from database import init_db

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

# 创建数据库目录（如果不存在）
db_dir = Path(os.getenv("DATABASE_PATH", "/app/data/wolf_recs.db")).parent
db_dir.mkdir(parents=True, exist_ok=True)

# 初始化Bot和Dispatcher
bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher(storage=MemoryStorage())

# 注册路由
dp.include_router(private_router)
dp.include_router(group_router)
dp.include_router(callback_router)
dp.include_router(admin_router)

async def main():
    """主函数"""
    try:
        # 初始化数据库
        init_db()
        logger.info("✅ 数据库初始化成功")
        
        # 启动轮询
        logger.info("✅ 狼评机器人已启动（长轮询模式）")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        raise
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())