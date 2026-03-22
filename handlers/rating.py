# handlers/rating.py
"""
评价流程处理模块
"""

import logging
from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states import RatingStates
from database import add_evaluation, check_user_rated_teacher, MIN_REASON_LENGTH
from bot_instance import bot

logger = logging.getLogger(__name__)
router = Router()

@router.message(StateFilter(RatingStates.waiting_reason))
async def process_rating_reason(message: Message, state: FSMContext):
    """处理评价理由"""
    user_id = message.from_user.id
    reason = message.text.strip()
    data = await state.get_data()
    
    teacher = data.get("teacher")
    recommend = data.get("recommend")
    
    # 验证理由长度
    if len(reason) < MIN_REASON_LENGTH:
        await message.reply(
            f"❌ 理由太短！至少需要 {MIN_REASON_LENGTH} 个字\n\n"
            f"您填写了: {len(reason)} 个字\n\n"
            f"请重新填写："
        )
        return
    
    # 再次检查是否已评价（防止并发问题）
    if check_user_rated_teacher(teacher, user_id):
        await state.clear()
        await message.reply(
            f"❌ 您已经评价过 @{teacher} 了\n\n"
            f"每个教师只能评价一次"
        )
        return
    
    # 添加评价
    result = add_evaluation(teacher, recommend, reason, user_id)
    
    if result["success"]:
        # 成功
        await state.set_state(RatingStates.completed)
        
        success_msg = f"""✅ 评价提交成功！

📊 您的评价：
教师: @{teacher}
态度: {'👍 推荐' if recommend else '👎 不推荐'}
理由: {reason[:30]}...

🎉 感谢您的反馈！
您的评价将帮助其他同学做出更好的选择！"""
        
        await message.reply(success_msg)
        
        logger.info(f"用户 {user_id} 成功评价了 @{teacher}")
    else:
        # 失败
        await message.reply(result["msg"])
        logger.warning(f"用户 {user_id} 评价失败: {result['msg']}")
    
    # 清理状态
    await state.clear()