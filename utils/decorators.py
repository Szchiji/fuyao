# utils/decorators.py
from aiogram import types
from functools import wraps
from config import ADMIN_IDS

def admin_only(func):
    """仅管理员装饰器"""
    @wraps(func)
    async def wrapper(message: types.Message, *args, **kwargs):
        if message.from_user.id not in ADMIN_IDS:
            await message.reply("❌ 您没有管理员权限")
            return
        return await func(message, *args, **kwargs)
    return wrapper