# handlers/callback.py
from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from states import RatingStates
from utils.helpers import send_teacher_detail
from database import add_evaluation, get_encourage
from bot_instance import bot

router = Router()

@router.callback_query()
async def handle_callback(callback: CallbackQuery, state: FSMContext):
    """处理回调查询"""
    try:
        if callback.data.startswith("rec|"):
            # 处理推荐/不推荐
            _, rec_str, teacher = callback.data.split("|", 2)
            recommend = int(rec_str)

            await state.update_data(
                teacher=teacher,
                recommend=recommend,
                msg_id=callback.message.message_id,
                chat_id=callback.message.chat.id
            )
            await state.set_state(RatingStates.waiting_reason)

            await bot.send_message(
                callback.from_user.id,
                f"您选择了 {'👍推荐' if recommend else '👎不推荐'} 「@{teacher}」\n\n请填写评价理由（至少12字）："
            )
            await callback.answer("请在私聊中填写")
            return

        if callback.data.startswith("view_yes|"):
            # 处理只看推荐
            teacher = callback.data.split("|", 1)[1]
            await send_teacher_detail(
                callback.message,
                teacher,
                edit_msg_id=callback.message.message_id
            )
            await callback.answer()

    except Exception as e:
        await callback.answer(f"❌ 出错: {str(e)}")

@router.message(RatingStates.waiting_reason)
async def process_reason(message: Message, state: FSMContext):
    """处理评价理由"""
    data = await state.get_data()
    teacher = data.get("teacher")
    recommend = data.get("recommend")
    user_id = message.from_user.id

    if len(message.text.strip()) < 12:
        await message.reply("❌ 理由至少需要12个字，请重新填写")
        return

    result = add_evaluation(teacher, recommend, message.text, user_id)
    if result["success"]:
        await message.reply(get_encourage())
    else:
        await message.reply(result["msg"])

    await state.clear()