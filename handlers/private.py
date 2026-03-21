# handlers/private.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_LINK
from database import get_start_message, get_required_channel
from bot import bot

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """处理 /start 命令"""
    if message.chat.type != "private":
        return

    required = get_required_channel()
    if required:
        try:
            member = await bot.get_chat_member(required, message.from_user.id)
            if member.status in ('left', 'kicked', 'restricted'):
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="加入频道", url=CHANNEL_LINK)]
                ])
                await message.reply("⚠️ 请先加入频道", reply_markup=kb)
                return
        except Exception as e:
            print(f"检查频道成员时出错: {e}")

    welcome = get_start_message("欢迎使用狼评机器人！\n\n在群组中使用 @teacher_name 来查询或评价教师")
    await message.reply(welcome)

@router.message(Command("help"))
async def cmd_help(message: Message):
    """处理 /help 命令"""
    help_text = """
📖 使用帮助

👥 用户命令：
• /start - 启动机器人
• @teacher_name - 查询教师评价

⭐ 如何评价：
1. 在群组或私聊中输入 @teacher_name
2. 点击 👍推荐 或 👎不推荐
3. 填写评价理由（至少12个字）

管理员可以使用：
• /admin - 进入管理员面板
"""
    await message.reply(help_text)