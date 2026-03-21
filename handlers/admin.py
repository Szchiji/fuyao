from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from database import set_required_channel, set_start_message
from states import RatingStates
from utils.decorators import admin_only

router = Router()

@router.message(Command("admin"))
@admin_only
async def admin_menu(message: Message):
    await message.reply("🛠️ 管理员后台\n/setchannel -100xxx - 设置频道\n/setstart - 设置欢迎语")

@router.message(Command("setchannel"))
@admin_only
async def set_channel(message: Message):
    try:
        channel_id = message.text.split(maxsplit=1)[1].strip()
        set_required_channel(channel_id)
        await message.reply(f"✅ 频道已设置为: {channel_id}")
    except IndexError:
        await message.reply("❌ 用法: /setchannel <频道ID>")

@router.message(Command("setstart"))
@admin_only
async def set_start_msg(message: Message):
    try:
        start_msg = message.text.split(maxsplit=1)[1].strip()
        set_start_message(start_msg)
        await message.reply(f"✅ 欢迎语已更新:\n{start_msg}")
    except IndexError:
        await message.reply("❌ 用法: /setstart <欢迎语内容>")