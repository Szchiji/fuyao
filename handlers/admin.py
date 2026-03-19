from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from database import set_required_channel, set_start_message
from utils.decorators import admin_only

router = Router()

@router.message(Command("admin"))
@admin_only
async def admin_menu(message: Message):
    await message.reply("🛠️ 管理员后台\n/setchannel -100xxx 设置频道\n/setstart 新欢迎语")