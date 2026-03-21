from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_LINK
from database import get_start_message, get_required_channel
from bot import bot

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.chat.type != "private":
        return

    required = get_required_channel()
    if required:
        try:
            member = await bot.get_chat_member(required, message.from_user.id)
            if member.status in ('left', 'kicked', 'restricted'):
                kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="加入频道", url=CHANNEL_LINK)]])
                await message.reply("⚠️ 请先加入频道", reply_markup=kb)
                return
        except:
            pass

    welcome = get_start_message("欢迎使用狼评机器人！")
    await message.reply(welcome)