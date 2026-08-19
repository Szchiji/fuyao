# utils/helpers.py
import asyncio
import logging
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_teacher_detail, get_user_by_username, get_auto_delete_delay, set_teacher_info

logger = logging.getLogger(__name__)

SCORE_DIMENSIONS = {
    "teaching": {
        "title": "服务质量",
        "short": "服务",
        "icon": "🤝",
        "description": "沟通、回应、负责程度"
    },
    "grading": {
        "title": "外貌形象",
        "short": "形象",
        "icon": "✨",
        "description": "气质、形象、状态观感"
    },
    "difficulty": {
        "title": "推荐指数",
        "short": "推荐",
        "icon": "🌟",
        "description": "你整体有多愿意推荐 TA"
    },
}


async def auto_delete_message(message: Message, delay: int = None):
    """在指定时间（秒）后自动删除消息。delay 为 None 时从数据库读取配置值"""
    if delay is None:
        delay = get_auto_delete_delay()
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        logger.debug(f"自动删除消息失败: {e}")


async def fetch_tg_teacher_info(bot: Bot, teacher_name: str, nickname: str, tid: str):
    """
    通过 Telegram API 获取昵称和 ID，优先使用 Telegram 实时数据。
    若 API 获取失败则回退到 users 表中已存储的用户信息，最后才使用传入的数值。
    """
    try:
        tg_chat = await bot.get_chat(f"@{teacher_name}")
        current_username = getattr(tg_chat, "username", None) or teacher_name
        full_name = tg_chat.first_name or ""
        if getattr(tg_chat, "last_name", None):
            full_name = f"{full_name} {tg_chat.last_name}".strip()
        nickname = full_name or nickname
        tid = str(tg_chat.id) if tg_chat.id else tid
        if tid:
            set_teacher_info(current_username, nickname, tid)
            if current_username.lower() != teacher_name.lower():
                set_teacher_info(teacher_name, nickname, tid)
    except Exception as e:
        logger.debug(f"从 Telegram 获取 @{teacher_name} 信息失败: {e}")
        # 回退：从 users 表查找曾与机器人互动过的同名用户
        user_row = get_user_by_username(teacher_name)
        if user_row:
            nickname = nickname or user_row.get("first_name", "")
            tid = tid or str(user_row.get("user_id", ""))
            if tid:
                set_teacher_info(teacher_name, nickname, tid)
    return nickname, tid


def build_score_keyboard(step_callback_prefix: str, teacher: str) -> InlineKeyboardMarkup:
    """构建更紧凑的 1-5 分打分键盘"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ 1", callback_data=f"{step_callback_prefix}|1|{teacher}"),
            InlineKeyboardButton(text="⭐⭐ 2", callback_data=f"{step_callback_prefix}|2|{teacher}"),
        ],
        [
            InlineKeyboardButton(text="⭐⭐⭐ 3", callback_data=f"{step_callback_prefix}|3|{teacher}"),
            InlineKeyboardButton(text="⭐⭐⭐⭐ 4", callback_data=f"{step_callback_prefix}|4|{teacher}"),
        ],
        [
            InlineKeyboardButton(text="⭐⭐⭐⭐⭐ 5", callback_data=f"{step_callback_prefix}|5|{teacher}")
        ],
        [
            InlineKeyboardButton(text="⏭️ 跳过本项", callback_data=f"{step_callback_prefix}|skip|{teacher}")
        ]
    ])


def format_score_line(scores: dict) -> str:
    """将评分均值格式化为一行文字，若无数据则返回空字符串"""
    parts = []
    for key in ("teaching", "grading", "difficulty"):
        score = scores.get(key)
        count = scores.get(f"{key}_count", 0)
        if score is not None and count >= 1:
            meta = SCORE_DIMENSIONS[key]
            parts.append(f"{meta['icon']} {meta['short']} {score}")
    return " | ".join(parts)


def extract_forwarded_teacher_info(message: Message) -> dict:
    """从转发消息中尽量提取教师 Telegram 信息"""
    info = {
        "teacher_id": "",
        "username": "",
        "nickname": "",
        "source_type": "",
    }

    origin = getattr(message, "forward_origin", None)
    if origin:
        info["source_type"] = getattr(origin, "type", "") or ""
        source_type = info["source_type"]

        if source_type == "user":
            user = getattr(origin, "sender_user", None) or getattr(origin, "user", None)
            if user:
                info["teacher_id"] = str(getattr(user, "id", "") or "")
                info["username"] = getattr(user, "username", "") or ""
                first_name = getattr(user, "first_name", "") or ""
                last_name = getattr(user, "last_name", "") or ""
                info["nickname"] = f"{first_name} {last_name}".strip()
        elif source_type == "hidden_user":
            info["nickname"] = getattr(origin, "sender_user_name", "") or ""
        elif source_type in {"chat", "channel"}:
            chat = (
                getattr(origin, "sender_chat", None)
                or getattr(origin, "chat", None)
                or getattr(message, "forward_from_chat", None)
            )
            if chat:
                info["teacher_id"] = str(getattr(chat, "id", "") or "")
                info["username"] = getattr(chat, "username", "") or ""
                info["nickname"] = (
                    getattr(chat, "title", None)
                    or getattr(chat, "full_name", None)
                    or ""
                )

    if not any(info.values()):
        user = getattr(message, "forward_from", None)
        if user:
            info["teacher_id"] = str(getattr(user, "id", "") or "")
            info["username"] = getattr(user, "username", "") or ""
            first_name = getattr(user, "first_name", "") or ""
            last_name = getattr(user, "last_name", "") or ""
            info["nickname"] = f"{first_name} {last_name}".strip()
            info["source_type"] = "user"
        else:
            info["nickname"] = getattr(message, "forward_sender_name", "") or ""
            info["source_type"] = "hidden_user" if info["nickname"] else ""

    return info

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