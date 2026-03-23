# utils/helpers.py
import logging
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_teacher_detail, get_user_by_username

logger = logging.getLogger(__name__)


async def fetch_tg_teacher_info(bot: Bot, teacher_name: str, nickname: str, tid: str):
    """
    通过 Telegram API 获取昵称和 ID，优先使用 Telegram 实时数据。
    若 API 获取失败则回退到 users 表中已存储的用户信息，最后才使用传入的数值。
    """
    try:
        tg_chat = await bot.get_chat(f"@{teacher_name}")
        full_name = tg_chat.first_name or ""
        if getattr(tg_chat, "last_name", None):
            full_name = f"{full_name} {tg_chat.last_name}".strip()
        nickname = full_name or nickname
        tid = str(tg_chat.id) if tg_chat.id else tid
    except Exception as e:
        logger.debug(f"从 Telegram 获取 @{teacher_name} 信息失败: {e}")
        # 回退：从 users 表查找曾与机器人互动过的同名用户
        user_row = get_user_by_username(teacher_name)
        if user_row:
            nickname = nickname or user_row.get("first_name", "")
            tid = tid or str(user_row.get("user_id", ""))
    return nickname, tid

async def send_teacher_detail(message: Message, teacher: str, edit_msg_id=None):
    """发送教师评价详情"""
    detail = get_teacher_detail(teacher)
    
    if not detail:
        text = f"【@{teacher}】\n暂无评价记录\n快来成为第一个评价的人吧！"
    else:
        text = f"【@{teacher}】\n👍 推荐：{detail['yes']} 人　👎 不推荐：{detail['no']} 人\n\n"
        text += "评价记录：\n"
        text += "\n".join(detail['reasons'][:10])
        if len(detail['reasons']) > 10:
            text += f"\n... 还有 {len(detail['reasons']) - 10} 条评价"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍 推荐", callback_data=f"rec|1|{teacher}")],
        [InlineKeyboardButton(text="👎 不推荐", callback_data=f"rec|0|{teacher}")],
    ])

    try:
        if edit_msg_id:
            await message.bot.edit_message_text(text, message.chat.id, edit_msg_id, reply_markup=kb)
        else:
            await message.reply(text, reply_markup=kb)
    except Exception as e:
        await message.reply(f"发送失败: {str(e)}")


def format_leaderboard_text(leaderboard: list) -> str:
    """将排行榜数据格式化为消息文本"""
    if not leaderboard:
        return "📊 暂无排行榜数据\n\n快去评价教师吧！"

    medals = ["🥇", "🥈", "🥉"]
    text = "🏆 教师推荐排行榜 TOP 10\n\n"
    for i, entry in enumerate(leaderboard, 1):
        prefix = medals[i - 1] if i <= 3 else f"{i}."
        text += (
            f"{prefix} @{entry['teacher']}\n"
            f"   👍 {entry['recommend']} | 👎 {entry['not_recommend']} | "
            f"总 {entry['total']} | 推荐率 {entry['recommend_pct']}%\n\n"
        )
    return text