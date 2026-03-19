# bot.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import TELEGRAM_BOT_TOKEN
from database import init_db

from handlers.group import router as group_router
from handlers.callback import router as callback_router
from handlers.private import router as private_router
from handlers.admin import router as admin_router

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(group_router)
dp.include_router(callback_router)
dp.include_router(private_router)
dp.include_router(admin_router)

async def main():
    init_db()
    print("✅ 狼评机器人重构版已启动（结构清晰）")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())