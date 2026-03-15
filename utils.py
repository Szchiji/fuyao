# utils.py
import time
import re
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import REQUIRED_CHANNEL, REQUIRED_GROUP, CHANNEL_LINK, GROUP_LINK, RATE_LIMIT_SECONDS
from database import user_has_rated

_last_query = {}

def check_rate_limit(user_id: int) -> bool:
    now = time.time()
    last = _last_query.get(user_id, 0)
    if now - last < RATE_LIMIT_SECONDS:
        return False
    _last_query[user_id] = now
    return True

async def is_subscribed(user_id: int, bot: types.Bot) -> bool:
    try:
        ch = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        if ch.status in ('left', 'kicked', 'restricted'):
            return False
        gp = await bot.get_chat_member(REQUIRED_GROUP, user_id)
        if gp.status in ('left', 'kicked', 'restricted'):
            return False
        return True
    except:
        return False

async def send_join_prompt(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="加入频道", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="加入群组", url=GROUP_LINK)]
    ])
    await message.reply("⚠️ 必须先加入指定频道与群组才能使用", reply_markup=kb)

def build_detail_keyboard(teacher: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍 推荐", callback_data=f"rec|1|{teacher}")],
        [InlineKeyboardButton(text="👎 不推荐", callback_data=f"rec|0|{teacher}")],
        [InlineKeyboardButton(text="只看推荐👍", callback_data=f"view_yes|{teacher}")]
    ])
