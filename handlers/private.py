# handlers/private.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from states import RatingStates
from database import get_start_message, get_global_stats, get_required_channel
from utils.helpers import send_teacher_detail

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.chat.type != "private":
        await message.reply("✅ 机器人已在群内可用，直接发送 @英文用户名 查询即可。")
        return

    required_channel = get_required_channel()
    if required_channel:
        try:
            member = await bot.get_chat_member(required_channel, message.from_user.id)
            if member.status in ('left', 'kicked', 'restricted'):
                kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="加入频道", url=CHANNEL_LINK)]])
                await message.reply("⚠️ 请先加入频道才能使用", reply_markup=kb)
                return
            else:
                await message.reply("✅ 关注成功！欢迎使用狼评机器人～")
        except:
            pass

    welcome = get_start_message("欢迎使用狼评机器人！")
    await message.reply(welcome)

@router.message(F.text.in_({"帮助", "菜单", "怎么用"}))
async def cmd_help(message: Message):
    await message.reply("📖 使用帮助：群里发 @英文用户名 查询，点击按钮后私聊写理由。")