# handlers.py
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import (
    HOT_TRIGGER_WORDS, SEARCH_TRIGGER_WORDS,
    MAX_REASON_PREVIEW, MAX_TOP_RANK
)
from database import (
    get_teacher_detail, get_top_teachers, get_fuzzy_search,
    add_evaluation, user_has_rated, delete_teacher
)
from utils import (
    is_subscribed, check_rate_limit, send_join_prompt, build_detail_keyboard
)

class Form:
    waiting_reason = "waiting_reason"

async def handle_group_message(message: types.Message, state: FSMContext, bot):
    if message.chat.type not in {"group", "supergroup"}:
        return

    text = message.text.strip()
    lower_text = text.lower()
    user_id = message.from_user.id

    if not check_rate_limit(user_id):
        return

    # 1. 排行榜触发
    if any(w.lower() in lower_text for w in HOT_TRIGGER_WORDS):
        if not await is_subscribed(user_id, bot):
            await send_join_prompt(message)
            return
        rows = get_top_teachers(MAX_TOP_RANK)
        if not rows:
            await message.reply("暂无评价数据～")
            return
        lines = ["🔥 **热门老师排行榜**（前 {} 名，按推荐数排序）\n".format(MAX_TOP_RANK)]
        for i, (t, y, tot) in enumerate(rows, 1):
            lines.append(f"{i}. @{t}   👍 {y}  (总 {tot} 条)")
        await message.reply("\n".join(lines))
        return

    # 2. 搜索触发
    search_query = None
    for trigger in SEARCH_TRIGGER_WORDS:
        if trigger in text:
            idx = text.find(trigger)
            if idx != -1:
                q = text[idx + len(trigger):].strip()
                if q and len(q) >= 2:
                    search_query = q
                    break

    if search_query:
        if not await is_subscribed(user_id, bot):
            await send_join_prompt(message)
            return

        results = get_fuzzy_search(search_query)
        if not results:
            await message.reply(f"未找到包含「{search_query}」的老师～")
            return

        if len(results) == 1:
            teacher = results[0][0]
            await send_teacher_detail(message, teacher, bot)
            return

        lines = [f"找到 {len(results)} 个相似老师：\n"]
        for t, y, tot in results:
            lines.append(f"• @{t}   👍 {y}  (总 {tot})")
        lines.append("\n直接发 @老师名 查看详细评价")
        await message.reply("\n".join(lines))
        return

    # 3. @老师名 触发
    import re
    match = re.search(r'@(\S+)', text)
    if match:
        teacher = match.group(1).strip()
        if not await is_subscribed(user_id, bot):
            await send_join_prompt(message)
            return
        await send_teacher_detail(message, teacher, bot)

async def send_teacher_detail(message: types.Message, teacher: str, bot):
    detail = get_teacher_detail(teacher)
    if not detail:
        text = f"【@{teacher}】\n暂无狼友评价\n快来成为第一个！"
    else:
        text = f"【@{teacher}】\n👍 推荐：{detail['yes']} 人　👎 不推荐：{detail['no']} 人\n\n"
        text += "\n".join(detail['reasons'][:MAX_REASON_PREVIEW])

    kb = build_detail_keyboard(teacher)
    await message.reply(text, reply_markup=kb)

# 按钮处理
async def handle_callback(callback: types.CallbackQuery, state: FSMContext, bot):
    data = callback.data
    user_id = callback.from_user.id

    if data.startswith("rec|"):
        _, rec_str, teacher = data.split("|", 2)
        recommend = int(rec_str)

        if not await is_subscribed(user_id, bot):
            await callback.answer("请先加入频道与群组", show_alert=True)
            return

        if user_has_rated(teacher, user_id):
            await callback.answer("你已经评价过这个老师了！", show_alert=True)
            return

        await state.update_data(
            teacher=teacher,
            recommend=recommend,
            query_msg_id=callback.message.message_id,
            query_chat_id=callback.message.chat.id
        )
        await state.set_state(Form.waiting_reason)

        kb_cancel = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="取消", callback_data="cancel_reason")
        ]])

        try:
            await bot.send_message(
                user_id,
                f"您选择了 {'👍推荐' if recommend else '👎不推荐'} 「@{teacher}」\n\n"
                "请直接回复这条消息，填写理由（可多行）：",
                reply_markup=kb_cancel
            )
            await callback.answer("请私聊填写理由")
        except:
            await callback.message.reply("请先私聊机器人 /start 开启对话")

    elif data.startswith("view_yes|"):
        teacher = data.split("|", 1)[1]
        if not await is_subscribed(user_id, bot):
            await callback.answer("请先加入频道与群组", show_alert=True)
            return

        detail = get_teacher_detail(teacher)
        if not detail or not detail["reasons"]:
            await callback.answer("暂无推荐评价", show_alert=True)
            return

        text = f"【@{teacher}】 只看推荐 👍\n\n" + "\n".join(
            [r for r in detail["reasons"] if r.startswith("👍")][:10]
        )
        await callback.message.reply(text)

    elif data == "cancel_reason":
        await state.clear()
        await callback.answer("已取消")
        await bot.send_message(user_id, "✅ 已取消本次评价")

# 私聊填写理由
async def handle_reason(message: types.Message, state: FSMContext, bot):
    if message.chat.type != "private":
        return

    data = await state.get_data()
    if not data:
        return

    teacher = data.get("teacher")
    recommend = data.get("recommend")
    query_msg_id = data.get("query_msg_id")
    query_chat_id = data.get("query_chat_id")

    reason = message.text.strip()
    if not reason:
        await message.reply("理由不能为空，请重新输入或取消")
        return

    success = add_evaluation(teacher, recommend, reason, message.from_user.id)
    if not success:
        await message.reply("评价失败（可能已重复），请稍后再试")
        await state.clear()
        return

    await message.reply(f"✅ 评价已记录！\n感谢你的贡献～")

    # 尝试更新群内原消息
    if query_msg_id and query_chat_id:
        try:
            detail = get_teacher_detail(teacher)
            text = f"【@{teacher}】\n👍 推荐：{detail['yes']}　👎 不推荐：{detail['no']}\n\n"
            text += "\n".join(detail['reasons'][:MAX_REASON_PREVIEW])

            kb = build_detail_keyboard(teacher)

            await bot.edit_message_text(
                chat_id=query_chat_id,
                message_id=query_msg_id,
                text=text,
                reply_markup=kb
            )
        except Exception as e:
            print(f"编辑群消息失败: {e}")

    await state.clear()

# 私聊管理员清空
async def handle_admin_clear(message: types.Message, bot):
    if message.chat.type != "private":
        return

    text = message.text.strip()
    if not text.startswith(("/clearteacher", "/cleart")):
        return

    args = text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("用法：/clearteacher 老师名\n示例：/clearteacher nsbbxha")
        return

    teacher = args[1].strip().lstrip('@')

    try:
        member = await bot.get_chat_member(REQUIRED_GROUP, message.from_user.id)
        if member.status not in ("administrator", "creator"):
            await message.reply("❌ 仅本群管理员可在私聊使用此命令")
            return
    except:
        await message.reply("❌ 验证失败，请确认你是本群管理员")
        return

    deleted = delete_teacher(teacher)
    await message.reply(f"✅ 已清空 @{teacher} 的所有评价（共删除 {deleted} 条）")
