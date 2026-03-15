# bot.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command

from config import TELEGRAM_BOT_TOKEN
from database import init_db
from handlers import (
    handle_group_message, handle_callback,
    handle_reason, handle_admin_clear, Form
)
from utils import is_subscribed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message()
async def message_router(message: types.Message, state: FSMContext):
    # 私聊管理员命令
    if message.chat.type == "private" and message.text.startswith(("/clearteacher", "/cleart")):
        await handle_admin_clear(message, bot)
        return

    # 私聊填写理由
    current_state = await state.get_state()
    if current_state == Form.waiting_reason:
        await handle_reason(message, state, bot)
        return

    # 群内消息处理
    await handle_group_message(message, state, bot)

@dp.callback_query()
async def callback_router(callback: types.CallbackQuery, state: FSMContext):
    await handle_callback(callback, state, bot)
    await callback.answer()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.chat.type == "private":
        await message.reply(
            "✅ 机器人已启动！\n\n"
            "在群组内直接发送 @老师名 或 搜 老师名片段 即可查询\n"
            "排行榜：发送 排行榜 / top / 热门榜 等\n"
            "管理员私聊：/clearteacher 老师名 清空数据"
        )
    else:
        await message.reply("群内使用请直接 @老师名 查询～")

async def main():
    init_db()
    logger.info("机器人启动成功")
    await dp.start_polling(bot, allowed_updates=types.Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())
