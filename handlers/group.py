# handlers/group.py
"""
群组处理模块
"""

import asyncio
import logging
import re
from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from database import get_teacher_stats, get_teacher_info
from states import RatingStates
from bot_instance import bot
from utils.helpers import fetch_tg_teacher_info, auto_delete_message

logger = logging.getLogger(__name__)
router = Router()

@router.message(StateFilter(None))
async def handle_teacher_mention(message: Message, state: FSMContext):
    """
    在群组中处理 @teacher_name 提及
    """
    # 只处理群组消息
    if message.chat.type == "private":
        return
    
    # 忽略没有文本的消息（图片、贴纸等）
    if not message.text:
        return
    
    # 只处理包含 @ 符号的消息
    if "@" not in message.text:
        return
    
    # 使用正则表达式提取 @username
    pattern = r'@([a-zA-Z0-9_]+)'
    matches = re.findall(pattern, message.text)
    
    if not matches:
        return
    
    # 取第一个匹配的教师名称
    teacher_name = matches[0]
    
    logger.info(f"用户 {message.from_user.id} 在群组中查询教师 @{teacher_name}")
    
    try:
        # 获取教师统计和信息
        stats = get_teacher_stats(teacher_name)
        teacher_info = get_teacher_info(teacher_name) or {}

        nickname = teacher_info.get("nickname", "")
        tid = teacher_info.get("teacher_id", "")

        # 若昵称或ID未在数据库中设置，尝试从 Telegram 获取
        nickname, tid = await fetch_tg_teacher_info(bot, teacher_name, nickname, tid)

        # 构建教师信息头部
        header = f"👨‍🏫 @{teacher_name}"
        if nickname:
            header += f"\n📛 昵称：{nickname}"
        if tid:
            header += f"\n🆔 ID：{tid}"

        if stats["total"] == 0:
            # 暂无评价
            display_text = f"""【{header}】
暂无评价记录
快来成为第一个评价的人吧！"""
        else:
            # 显示现有评价
            recommend_percentage = int((stats["recommend"] / stats["total"]) * 100) if stats["total"] > 0 else 0
            
            display_text = f"""【{header}】
📊 评价统计：
👍 推荐: {stats['recommend']} 人 ({recommend_percentage}%)
👎 不推荐: {stats['not_recommend']} 人 ({100-recommend_percentage}%)

📈 总评价数: {stats['total']}"""
            
            # 显示最新评价（含 ID）
            # latest 字段顺序: id(0), user_id(1), recommend(2), reason(3), time(4)
            if stats["latest"]:
                display_text += "\n\n📝 最新评价："
                for i, review in enumerate(stats["latest"][:2], 1):
                    rec_emoji = "👍" if review[2] else "👎"
                    display_text += f"\n{i}. {rec_emoji} [#{review[0]}] {review[3][:30]}..."
        
        # 创建评价按钮
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 推荐", callback_data=f"rec|1|{teacher_name}"),
                InlineKeyboardButton(text="👎 不推荐", callback_data=f"rec|0|{teacher_name}")
            ]
        ])
        
        sent = await message.reply(display_text, reply_markup=kb)
        asyncio.create_task(auto_delete_message(sent))
        
    except Exception as e:
        logger.error(f"处理教师提及时出错: {e}")
        sent_err = await message.reply(f"❌ 出错: {str(e)}")
        asyncio.create_task(auto_delete_message(sent_err))