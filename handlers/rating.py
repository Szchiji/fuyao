# handlers/rating.py
"""
评价流程处理模块
处理用户填写的评价理由
"""

import logging
from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states import RatingStates
from database import (
    add_evaluation,
    check_user_rated_teacher,
    MIN_REASON_LENGTH,
    get_teacher_stats,
    is_user_blacklisted
)
from bot_instance import bot

logger = logging.getLogger(__name__)
router = Router()


@router.message(StateFilter(RatingStates.waiting_reason))
async def process_rating_reason(message: Message, state: FSMContext):
    """处理用户填写的评价理由"""
    
    if message.chat.type != "private":
        await message.reply("❌ 请在私聊中填写评价理由")
        return
    
    user_id = message.from_user.id
    reason = message.text.strip()
    
    data = await state.get_data()
    teacher = data.get("teacher")
    recommend = data.get("recommend")
    
    logger.info(f"📝 用户 {user_id} 提交评价，字数: {len(reason)}")

    # 检查用户是否在黑名单中
    if is_user_blacklisted(user_id):
        await state.clear()
        await message.reply("🚫 您已被限制使用评价功能")
        logger.warning(f"🚫 黑名单用户 {user_id} 尝试提交评价")
        return

    if not teacher or recommend is None:
        logger.error("❌ 状态数据不完整")
        await message.reply("❌ 评价过程出错，请重新开始")
        await state.clear()
        return
    
    # 验证理由长度
    if len(reason) < MIN_REASON_LENGTH:
        remaining = MIN_REASON_LENGTH - len(reason)
        await message.reply(
            f"""❌ 理由太短！

您填写了: {len(reason)} 个字
还需要: {remaining} 个字

请重新填写："""
        )
        return
    
    # 再次检查是否已评价
    if check_user_rated_teacher(teacher, user_id):
        await state.clear()
        await message.reply(f"""❌ 您已经评价过 @{teacher} 了

每个教师只能评价一次""")
        return
    
    # 提交评价
    result = add_evaluation(teacher, recommend, reason, user_id)
    
    if result["success"]:
        stats = get_teacher_stats(teacher)
        recommend_percentage = int((stats["recommend"] / stats["total"]) * 100) if stats["total"] > 0 else 0
        
        success_msg = f"""✅ 评价提交成功！

📊 您的评价：
教师: @{teacher}
态度: {'👍 推荐' if recommend else '👎 不推荐'}
理由: {reason[:50]}...

📈 最新统计：
• 总评价数: {stats['total']}
• 👍 推荐: {stats['recommend']} 人 ({recommend_percentage}%)
• 👎 不推荐: {stats['not_recommend']} 人 ({100-recommend_percentage}%)

🎉 感谢您的反馈！"""
        
        await message.reply(success_msg)
        logger.info(f"✅ 用户 {user_id} 成功评价了 @{teacher}")
    else:
        await message.reply(result["msg"])
        logger.error(f"❌ 评价提交失败: {result['msg']}")
    
    await state.clear()