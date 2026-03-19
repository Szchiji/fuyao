# handlers/callback.py
from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from states import RatingStates
from database import get_teacher_detail
from utils.helpers import send_teacher_detail, get_encourage

router = Router()

@router.callback_query()
async def handle_callback(callback: CallbackQuery, state: FSMContext):
    if callback.data.startswith("rec|"):
        _, rec_str, teacher = callback.data.split("|", 2)
        recommend = int(rec_str)

        await state.update_data(teacher=teacher, recommend=recommend, 
                               msg_id=callback.message.message_id, 
                               chat_id=callback.message.chat.id)
        await state.set_state(RatingStates.waiting_reason)

        await bot.send_message(callback.from_user.id,
            f"您选择了 {'👍推荐' if recommend else '👎不推荐'} 「@{teacher}」\n\n"
            "请直接回复这条消息填写理由（至少12个字）：")
        await callback.answer("请私聊填写理由")

    elif callback.data.startswith("view_yes|"):
        teacher = callback.data.split("|", 1)[1]
        detail = get_teacher_detail(teacher)
        if detail:
            text = f"【@{teacher}】 只看推荐 👍\n\n" + "\n".join(r for r in detail["reasons"] if r.startswith("👍"))
            await callback.message.reply(text)