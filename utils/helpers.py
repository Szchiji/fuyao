# utils/helpers.py
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_teacher_detail

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