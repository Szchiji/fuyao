# bot.py
"""
Telegram 机器人主程序
"""

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import TELEGRAM_BOT_TOKEN
from database import init_db

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 导入路由器
try:
    from handlers.private import router as private_router
    logger.info("✅ 已加载 private_router")
except Exception as e:
    logger.error(f"❌ 加载 private_router 失败: {e}")
    sys.exit(1)

try:
    from handlers.admin import router as admin_router
    logger.info("✅ 已加载 admin_router")
except Exception as e:
    logger.error(f"❌ 加载 admin_router 失败: {e}")
    sys.exit(1)

try:
    from handlers.callback import router as callback_router
    logger.info("✅ 已加载 callback_router")
except Exception as e:
    logger.error(f"❌ 加载 callback_router 失败: {e}")
    sys.exit(1)

try:
    from handlers.rating import router as rating_router
    logger.info("✅ 已加载 rating_router")
except Exception as e:
    logger.error(f"❌ 加载 rating_router 失败: {e}")
    sys.exit(1)

# 初始化数据库
try:
    init_db()
    logger.info("✅ 数据库初始化成功")
except Exception as e:
    logger.error(f"❌ 数据库初始化失败: {e}")
    sys.exit(1)

# 从 config 导入 ADMIN_IDS 用于调试
try:
    from config import ADMIN_IDS
    logger.info(f"📝 ADMIN_IDS 配置: {ADMIN_IDS}")
except Exception as e:
    logger.error(f"❌ 读取 ADMIN_IDS 失败: {e}")
    ADMIN_IDS = []

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
    logger.info("📋 开始注册路由器...")
    
    dp.include_router(private_router)
    logger.info("✅ private_router 已注册")
    
    dp.include_router(admin_router)
    logger.info("✅ admin_router 已注册")
    
    dp.include_router(callback_router)
    logger.info("✅ callback_router 已注册")
    
    dp.include_router(rating_router)
    logger.info("✅ rating_router 已注册")
    
    logger.info("✅ 狼评机器人已启动")
    logger.info("🔄 开始轮询更新...")
    
    try:
        # 启动轮询
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("⛔ 机器人已停止")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())