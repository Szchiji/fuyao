# bot.py
"""
Telegram 机器人主程序
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import TELEGRAM_BOT_TOKEN
from database import init_db

# 导入路由器
from handlers.private import router as private_router
from handlers.admin import router as admin_router
from handlers.callback import router as callback_router
from handlers.rating import router as rating_router

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化数据库
init_db()

async def main():
    """主函数"""
    # 创建存储
    storage = MemoryStorage()
    
    # 创建 Bot 实例
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    
    # 创建 Dispatcher
    dp = Dispatcher(storage=storage)
    
    # 注册所有路由器
    dp.include_router(private_router)
    dp.include_router(admin_router)
    dp.include_router(callback_router)
    dp.include_router(rating_router)
    
    logger.info("✅ 狼评机器人已启动")
    logger.info("🔄 开始轮询更新...")
    
    try:
        # 启动轮询
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("⛔ 机器人已停止")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())