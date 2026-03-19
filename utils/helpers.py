# utils/helpers.py
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_teacher_detail, get_encourage

async def send_teacher_detail(message: Message, teacher: str, edit_msg_id=None):
    detail = get_teacher_detail(teacher)
    if not detail:
        text = f"【@{teacher}】\n暂无评价记录\n快来成为第一个评价的人吧！"
    else:
        text = f"【@{teacher}】\n👍 推荐：{detail['yes']} 人　👎 不推荐：{detail['no']} 人\n\n"
        text += "\n".join(detail['reasons'][:12])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍 推荐", callback_data=f"rec|1|{teacher}")],
        [InlineKeyboardButton(text="👎 不推荐", callback_data=f"rec|0|{teacher}")],
        [InlineKeyboardButton(text="只看推荐", callback_data=f"view_yes|{teacher}")]
    ])

    if edit_msg_id:
        await message.bot.edit_message_text(text, message.chat.id, edit_msg_id, reply_markup=kb)
    else:
        await message.reply(text, reply_markup=kb)