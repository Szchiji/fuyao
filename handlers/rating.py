# handlers/rating.py
"""
评价流程处理模块
处理用户填写的评价理由
"""

import logging
from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states import RatingStates
from database import (
    add_evaluation,
    check_user_rated_teacher,
    MIN_REASON_LENGTH,
    get_teacher_stats,
    is_user_blacklisted,
    set_teacher_info,
)
from bot_instance import bot
from utils.helpers import SCORE_DIMENSIONS, extract_forwarded_teacher_info

logger = logging.getLogger(__name__)
router = Router()


@router.message(StateFilter(RatingStates.waiting_forwarded_message))
async def process_forwarded_teacher_message(message: Message, state: FSMContext):
    """处理用户转发的教师消息"""
    if message.chat.type != "private":
        await message.reply("❌ 请在私聊中转发教师消息")
        return

    data = await state.get_data()
    teacher = data.get("teacher")
    if not teacher:
        await state.clear()
        await message.reply("❌ 评价过程已失效，请重新输入 @教师用户名 开始")
        return

    forward_info = extract_forwarded_teacher_info(message)
    if not any([
        getattr(message, "forward_origin", None),
        getattr(message, "forward_from", None),
        getattr(message, "forward_from_chat", None),
        getattr(message, "forward_sender_name", None),
    ]):
        await message.reply(
            "⚠️ 这不是一条转发消息，请直接使用 Telegram 的“转发”功能发送教师消息给我。"
        )
        return

    teacher_id = forward_info["teacher_id"]
    teacher_username = forward_info["username"]
    nickname = forward_info["nickname"]

    if teacher_id or nickname:
        set_teacher_info(teacher, nickname, teacher_id)
    if teacher_username and teacher_username.lower() != teacher.lower():
        set_teacher_info(teacher_username, nickname, teacher_id)

    await state.update_data(
        forward_checked=True,
        forwarded_teacher_id=teacher_id,
        forwarded_teacher_username=teacher_username,
        forwarded_teacher_nickname=nickname,
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 推荐", callback_data=f"rec|1|{teacher}"),
            InlineKeyboardButton(text="👎 不推荐", callback_data=f"rec|0|{teacher}")
        ]
    ])

    identified_parts = []
    if teacher_username:
        identified_parts.append(f"@{teacher_username}")
    if nickname:
        identified_parts.append(nickname)
    if teacher_id:
        identified_parts.append(f"ID：{teacher_id}")

    identify_text = (
        "✅ 已收到转发消息\n"
        f"已识别：{' / '.join(identified_parts)}\n\n"
        if identified_parts else
        "✅ 已收到转发消息\n"
        "⚠️ 由于转发来源或隐私设置限制，暂时无法读取教师 ID，但可以继续评价。\n\n"
    )

    await message.reply(
        identify_text + f"第 2 步：请为 @{teacher} 选择您的态度：",
        reply_markup=kb
    )


@router.message(StateFilter(RatingStates.waiting_reason))
async def process_rating_reason(message: Message, state: FSMContext):
    """处理用户填写的评价理由"""
    
    if message.chat.type != "private":
        await message.reply("❌ 请在私聊中填写评价理由")
        return
    
    user_id = message.from_user.id
    if not message.text:
        await message.reply("⚠️ 请直接发送文字评价内容，至少 12 个字。")
        return
    reason = message.text.strip()
    
    data = await state.get_data()
    teacher = data.get("teacher")
    recommend = data.get("recommend")
    score_teaching = data.get("score_teaching")
    score_grading = data.get("score_grading")
    score_difficulty = data.get("score_difficulty")
    
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
    result = add_evaluation(teacher, recommend, reason, user_id,
                            score_teaching=score_teaching,
                            score_grading=score_grading,
                            score_difficulty=score_difficulty)
    
    if result["success"]:
        stats = get_teacher_stats(teacher)
        recommend_percentage = int((stats["recommend"] / stats["total"]) * 100) if stats["total"] > 0 else 0
        score_summary = (
            f"{SCORE_DIMENSIONS['teaching']['icon']} {SCORE_DIMENSIONS['teaching']['title']}："
            f"{f'{score_teaching} 分' if score_teaching is not None else '已跳过'}\n"
            f"{SCORE_DIMENSIONS['grading']['icon']} {SCORE_DIMENSIONS['grading']['title']}："
            f"{f'{score_grading} 分' if score_grading is not None else '已跳过'}\n"
            f"{SCORE_DIMENSIONS['difficulty']['icon']} {SCORE_DIMENSIONS['difficulty']['title']}："
            f"{f'{score_difficulty} 分' if score_difficulty is not None else '已跳过'}"
        )
        
        success_msg = f"""✅ 评价提交成功！

📊 您的评价：
教师: @{teacher}
态度: {'👍 推荐' if recommend else '👎 不推荐'}
评分:
{score_summary}
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