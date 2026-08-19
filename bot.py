# bot.py
"""
狼评机器人主程序 - 混合模式
同时支持 Webhook（主要）和轮询（备份）
"""

import asyncio
import logging
import os
import time
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import TELEGRAM_BOT_TOKEN, ADMIN_IDS
from database import init_db
from utils.middleware import BlacklistMiddleware

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger.info("🚀 启动狼评机器人（混合模式）...")
logger.info(f"📝 配置的管理员 ID: {ADMIN_IDS}")

# 导入路由器
try:
    from handlers.admin import router as admin_router
    logger.info("✅ admin_router 已加载")
except Exception as e:
    logger.error(f"❌ 加载 admin_router 失败: {e}")
    exit(1)

try:
    from handlers.rating import router as rating_router
    logger.info("✅ rating_router 已加载")
except Exception as e:
    logger.error(f"❌ 加载 rating_router 失败: {e}")
    exit(1)

try:
    from handlers.callback import router as callback_router
    logger.info("✅ callback_router 已加载")
except Exception as e:
    logger.error(f"❌ 加载 callback_router 失败: {e}")
    exit(1)

try:
    from handlers.private import router as private_router
    logger.info("✅ private_router 已加载")
except Exception as e:
    logger.error(f"❌ 加载 private_router 失败: {e}")
    exit(1)

try:
    from handlers.inline import router as inline_router
    logger.info("✅ inline_router 已加载")
except Exception as e:
    logger.error(f"❌ 加载 inline_router 失败: {e}")
    exit(1)

# 数据库初始化（带重试逻辑，应对服务器崩溃后数据库短暂不可用的情况）
_DB_INIT_RETRIES = 5
_DB_INIT_DELAY = 10  # 秒
for _attempt in range(_DB_INIT_RETRIES):
    try:
        init_db()
        logger.info("✅ 数据库初始化完成")
        break
    except Exception as _e:
        logger.error(f"❌ 数据库初始化失败（尝试 {_attempt + 1}/{_DB_INIT_RETRIES}）: {_e}")
        if _attempt < _DB_INIT_RETRIES - 1:
            logger.info(f"⏳ {_DB_INIT_DELAY} 秒后重试...")
            time.sleep(_DB_INIT_DELAY)
        else:
            logger.error("❌ 数据库多次初始化失败，退出")
            exit(1)


# 全局变量
bot = None
dp = None
webhook_mode = False
polling_mode = False


async def setup_dispatcher():
    """设置 Dispatcher"""
    global dp
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    logger.info("📋 注册路由器...")
    
    dp.include_router(admin_router)
    logger.info("✅ admin_router 已注册")
    
    dp.include_router(rating_router)
    logger.info("✅ rating_router 已注册")
    
    dp.include_router(callback_router)
    logger.info("✅ callback_router 已注册")
    
    dp.include_router(private_router)
    logger.info("✅ private_router 已注册")

    dp.include_router(inline_router)
    logger.info("✅ inline_router 已注册")

    # 注册黑名单中间件（拦截所有消息和回调）
    dp.message.middleware(BlacklistMiddleware())
    dp.callback_query.middleware(BlacklistMiddleware())
    logger.info("✅ 黑名单中间件已注册")


async def ensure_webhook_deleted(retries: int = 5, delay: float = 5.0) -> bool:
    """
    确保 Webhook 已删除，带重试逻辑。
    服务器崩溃后重启时，若此调用失败则轮询无法正常接收更新，
    因为 Telegram 仍会向旧 Webhook URL 推送消息。
    """
    for attempt in range(retries):
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook 已删除")
            return True
        except Exception as e:
            logger.warning(f"⚠️ 删除 Webhook 失败（尝试 {attempt + 1}/{retries}）: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
    logger.error("❌ 无法删除 Webhook，轮询可能无法正常接收更新")
    return False


async def webhook_handler(request: web.Request) -> web.Response:
    """
    处理来自 Telegram 的 Webhook 请求
    Telegram 服务器直接推送更新到这个端点
    """
    try:
        update_data = await request.json()
        update = Update(**update_data)
        
        # 处理更新
        await dp.feed_update(bot, update)
        
        return web.Response(text="ok", status=200)
    except Exception as e:
        logger.error(f"❌ Webhook 处理错误: {e}", exc_info=True)
        return web.Response(status=500, text="error")


async def polling_task():
    """
    轮询任务
    在非 Webhook 模式（开发/本地环境）下接收更新
    """
    logger.info("🔄 轮询已启动")
    
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            poll_interval=1.0,
            timeout=10,
            drop_pending_updates=True,
        )
    except asyncio.CancelledError:
        logger.info("⛔ 轮询备份已停止")
    except Exception as e:
        logger.error(f"❌ 轮询备份错误: {e}", exc_info=True)


async def main():
    """主函数 - 生产环境使用 Webhook，开发环境使用轮询"""
    global bot, webhook_mode, polling_mode
    
    # 创建 Bot 实例
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    
    # 设置 Dispatcher
    await setup_dispatcher()
    
    # 获取环境变量
    PORT = int(os.getenv('PORT', 8080))
    NODE_ENV = os.getenv('NODE_ENV', 'development')
    RAILWAY_PUBLIC_URL = os.getenv('RAILWAY_PUBLIC_URL', '')
    
    # 判断运行环境
    is_production = NODE_ENV == 'production' and RAILWAY_PUBLIC_URL
    
    logger.info(f"🌍 运行环境: {NODE_ENV}")
    logger.info(f"🔗 Railway Public URL: {RAILWAY_PUBLIC_URL if RAILWAY_PUBLIC_URL else '无（本地开发）'}")
    
    # ==================== 创建 Web 应用 ====================
    app = web.Application()
    
    # ⭐ 修复：使用正确的 aiohttp API
    # 添加 Webhook 路由
    app.router.add_post('/webhook', webhook_handler)
    
    # 添加健康检查路由
    async def health_check(request):
        """健康检查端点"""
        return web.Response(
            text='{"status": "ok"}',
            content_type='application/json'
        )
    
    app.router.add_get('/health', health_check)
    
    # 添加信息端点
    async def info_handler(request):
        """获取机器人信息"""
        info = {
            "status": "running",
            "mode": "webhook" if webhook_mode else "polling",
            "webhook_enabled": webhook_mode,
            "polling_enabled": polling_mode,
            "bot_id": bot.id if bot else None,
            "environment": NODE_ENV
        }
        return web.json_response(info)
    
    app.router.add_get('/info', info_handler)
    
    # ==================== 启动 Web 服务器 ====================
    logger.info(f"🌐 启动 Web 服务器（监听 0.0.0.0:{PORT}）...")
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    logger.info(f"✅ Web 服务器运行在 0.0.0.0:{PORT}")
    
    # ==================== 设置 Webhook ====================
    if is_production and RAILWAY_PUBLIC_URL:
        logger.info("🚀 生产环境检测到 - 启用 Webhook 模式")
        webhook_mode = True
        
        webhook_url = f"{RAILWAY_PUBLIC_URL}/webhook"
        logger.info(f"🔗 设置 Webhook URL: {webhook_url}")
        
        try:
            # 先确保旧 Webhook 已删除（带重试），避免残留指向旧服务器
            await ensure_webhook_deleted()
            
            # 设置新 Webhook
            await bot.set_webhook(
                url=webhook_url,
                allowed_updates=dp.resolve_used_update_types(),
                drop_pending_updates=False
            )
            logger.info("✅ Webhook 已设置成功")
            
            # 获取 Webhook 信息
            webhook_info = await bot.get_webhook_info()
            logger.info(f"📊 Webhook 信息: {webhook_info}")
            
        except Exception as e:
            logger.error(f"❌ 设置 Webhook 失败: {e}")
            logger.warning("⚠️ 将回退到轮询模式")
            webhook_mode = False
            # 确保 Webhook 已删除，否则轮询收不到任何更新
            await ensure_webhook_deleted()
    else:
        logger.info("💻 开发环境或本地运行 - 禁用 Webhook")
        webhook_mode = False
        
        # 确保 Webhook 已删除（带重试），否则轮询收不到任何更新
        await ensure_webhook_deleted()
    
    # ==================== 启动轮询（仅在非 Webhook 模式下） ====================
    polling_task_obj = None
    if not webhook_mode:
        logger.info("🔄 启动轮询任务...")
        polling_mode = True
        polling_task_obj = asyncio.create_task(polling_task())
    else:
        logger.info("ℹ️ Webhook 模式已启用，跳过轮询")
        polling_mode = False
    
    # ==================== 显示启动信息 ====================
    logger.info("")
    logger.info("=" * 50)
    logger.info("🎉 狼评机器人已启动")
    logger.info("=" * 50)
    logger.info(f"📊 工作模式:")
    logger.info(f"  • Webhook:  {'✅ 已启用' if webhook_mode else '❌ 已禁用'}")
    logger.info(f"  • 轮询:     {'✅ 已启用' if polling_mode else '❌ 已禁用'}")
    logger.info(f"🌐 服务地址: http://0.0.0.0:{PORT}")
    logger.info(f"🔗 健康检查: http://localhost:{PORT}/health")
    logger.info(f"📋 机器人信息: http://localhost:{PORT}/info")
    logger.info("=" * 50)
    logger.info("")
    
    # 保持运行
    try:
        await asyncio.sleep(float('inf'))
    except KeyboardInterrupt:
        logger.info("⛔ 收到停止信号...")
    except Exception as e:
        logger.error(f"❌ 运行错误: {e}")
    finally:
        logger.info("🛑 关闭机器人...")
        
        # 取消轮询任务（如果已启动）
        if polling_task_obj is not None:
            polling_task_obj.cancel()
            try:
                await polling_task_obj
            except asyncio.CancelledError:
                pass
        
        # 关闭 Bot 连接
        await bot.session.close()
        
        # 关闭 Web 服务器
        await runner.cleanup()
        
        logger.info("✅ 机器人已关闭")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⛔ 机器人已停止")
    except Exception as e:
        logger.error(f"❌ 致命错误: {e}", exc_info=True)
        exit(1)