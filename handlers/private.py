# handlers/private.py
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_LINK
from database import get_start_message, get_required_channel
from bot_instance import bot

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """处理 /start 命令"""
    if message.chat.type != "private":
        return

    required = get_required_channel()
    logger.info(f"用户 {message.from_user.id} 启动机器人，频道要求: {required}")
    
    if required:
        try:
            # 检查用户是否是频道成员
            member = await bot.get_chat_member(required, message.from_user.id)
            logger.info(f"用户 {message.from_user.id} 在频道 {required} 的状态: {member.status}")
            
            # 检查成员状态
            if member.status in ('left', 'kicked', 'restricted'):
                logger.warning(f"用户 {message.from_user.id} 未订阅频道 {required}")
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="加入频道", url=CHANNEL_LINK)]
                ])
                await message.reply(
                    "⚠️ 请先加入频道后才能使用机器人\n\n点击下方按钮加入频道",
                    reply_markup=kb
                )
                return
            
            logger.info(f"用户 {message.from_user.id} 已订阅频道")
        
        except Exception as e:
            logger.error(f"检查频道成员时出错: {e}")
            # 如果检查失败，拒绝访问（不允许通过）
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="加入频道", url=CHANNEL_LINK)]
            ])
            await message.reply(
                "⚠️ 无法验证您的订阅状态，请确保已加入频道",
                reply_markup=kb
            )
            return

    welcome = get_start_message("欢迎使用狼评机器人！\n\n在群组中使用 @teacher_name 来查询或评价教师")
    await message.reply(welcome)

@router.message(Command("help"))
async def cmd_help(message: Message):
    """处理 /help 命令"""
    help_text = """📖 使用帮助

👥 用户命令：
• /start - 启动机器人
• /help - 获取帮助
• @teacher_name - 查询教师评价

⭐ 如何评价：
1. 在群组或私聊中输入 @teacher_name
2. 点击 👍推荐 或 👎不推荐
3. 填写评价理由（至少12个字）

管理员可以使用：
• /admin - 进入管理员面板"""
    await message.reply(help_text)