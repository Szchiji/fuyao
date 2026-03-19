# utils/decorators.py
from aiogram import types
from functools import wraps
from database import get_required_channel
from config import ADMIN_IDS

def require_subscription(func):
    @wraps(func)
    async def wrapper(message: types.Message, *args, **kwargs):
        required = get_required_channel()
        if required:
            try:
                member = await bot.get_chat_member(required, message.from_user.id)
                if member.status in ('left', 'kicked', 'restricted'):
                    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="加入频道", url=CHANNEL_LINK)]])
                    await message.reply("⚠️ 请先加入频道才能使用", reply_markup=kb)
                    return
            except:
                pass
        return await func(message, *args, **kwargs)
    return wrapper

def admin_only(func):
    @wraps(func)
    async def wrapper(message: types.Message, *args, **kwargs):
        if message.from_user.id not in ADMIN_IDS:
            await message.reply("❌ 您没有管理员权限")
            return
        return await func(message, *args, **kwargs)
    return wrapper