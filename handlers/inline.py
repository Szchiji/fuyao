# handlers/inline.py
"""
内联模式处理模块
支持用户在任何群里输入 @机器人名 李老师 查询教师评价
"""

import logging
from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from database import get_teacher_stats, search_teachers, get_teacher_score_averages
from utils.helpers import format_score_line, SCORE_DIMENSIONS

logger = logging.getLogger(__name__)
router = Router()


def _build_teacher_result(teacher_name: str) -> InlineQueryResultArticle:
    """构建单个教师的内联查询结果"""
    stats = get_teacher_stats(teacher_name)
    scores = get_teacher_score_averages(teacher_name)
    score_line = format_score_line(scores)

    if stats["total"] == 0:
        description = "暂无评价"
        text = (
            f"┏━━━━━━━━━━━━━━\n"
            f"👨‍🏫 @{teacher_name}\n"
            f"┗━━━━━━━━━━━━━━\n\n"
            f"📭 暂无公开评价\n"
            f"✨ 你可以成为第一位提交评价的人。"
        )
    else:
        recommend_pct = int((stats["recommend"] / stats["total"]) * 100) if stats["total"] > 0 else 0
        not_rec_pct = 100 - recommend_pct
        description = f"👍 {stats['recommend']}  👎 {stats['not_recommend']}  总 {stats['total']}  推荐率 {recommend_pct}%"

        text = (
            f"┏━━━━━━━━━━━━━━\n"
            f"👨‍🏫 @{teacher_name}\n"
            f"┗━━━━━━━━━━━━━━\n\n"
            f"📌 当前概览\n"
            f"• 评价样本：{stats['total']} 条\n"
            f"• 推荐人数：{stats['recommend']} 人（{recommend_pct}%）\n"
            f"• 不推荐：{stats['not_recommend']} 人（{not_rec_pct}%）\n"
        )
        if score_line:
            text += f"\n⭐ 综合印象\n{score_line}\n"

        if stats["latest"]:
            text += "\n📝 最新反馈\n"
            for i, review in enumerate(stats["latest"][:3], 1):
                rec_emoji = "👍" if review[2] else "👎"
                reason = review[3]
                text += f"{i}. {rec_emoji} {reason[:60]}{'...' if len(reason) > 60 else ''}\n"

    return InlineQueryResultArticle(
        id=teacher_name,
        title=f"@{teacher_name}",
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=text
        ),
        thumbnail_url=None,
    )


@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery):
    """处理内联查询"""
    query = (inline_query.query or "").strip().lstrip("@")
    logger.info(f"🔍 内联查询: '{query}' by user {inline_query.from_user.id}")

    if not query:
        # 无关键词时提示用法
        await inline_query.answer(
            results=[
                InlineQueryResultArticle(
                    id="help",
                    title="🔍 输入教师名称查询",
                    description="例如：李老师  王教授  张老师",
                    input_message_content=InputTextMessageContent(
                        message_text="💡 使用方法：在输入框输入 @机器人名 + 教师名，即可查询教师评价。"
                    ),
                )
            ],
            cache_time=5,
            is_personal=False,
        )
        return

    # 搜索匹配的教师
    matches = search_teachers(query)

    if not matches:
        await inline_query.answer(
            results=[
                InlineQueryResultArticle(
                    id="not_found",
                    title=f"未找到「{query}」相关教师",
                    description="换个关键词试试",
                    input_message_content=InputTextMessageContent(
                        message_text=f"🔍 未找到与「{query}」相关的教师评价记录。"
                    ),
                )
            ],
            cache_time=10,
            is_personal=False,
        )
        return

    results = [_build_teacher_result(name) for name in matches[:10]]
    await inline_query.answer(results=results, cache_time=30, is_personal=False)
