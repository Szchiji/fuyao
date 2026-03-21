# handlers/callback.py
"""
回调查询处理模块
处理按钮点击事件
"""

import logging
from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from states import RatingStates
from utils.helpers import send_teacher_detail
from database import add_evaluation, get_encourage
from bot_instance import bot

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query()
async def handle_callback(callback: CallbackQuery, state: FSMContext):
    """处理所有回调查询"""
    try:
        data = callback.data
        
        # 处理推荐/不推荐
        if data.startswith("rec|"):
            _, rec_str, teacher = data.split("|", 2)
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
                f"您选择了 {'👍推荐' if recommend else '👎不推荐'} 「@{teacher}」\n\n"
                f"请填写评价理由（至少12字）："
            )
            await callback.answer("请在私聊中填写评价理由")
            return

        # 处理查看详情
        if data.startswith("view_yes|"):
            teacher = data.split("|", 1)[1]
            await send_teacher_detail(
                callback.message,
                teacher,
                edit_msg_id=callback.message.message_id
            )
            await callback.answer()
            return

        # 处理帮助按钮
        if data == "show_help":
            help_text = """📖 快速帮助

⭐ 使用步骤：
1️⃣ 输入 @teacher_name
2️⃣ 点击 👍 或 👎
3️⃣ 填写评价理由（12字以上）
4️⃣ 提交

📝 评价示例：
"讲课很生动，逻辑清晰，认真负责，强烈推荐"

💡 获取完整帮助:
/help"""
            await callback.answer()
            await bot.send_message(
                callback.from_user.id,
                help_text
            )
            return

        # 处理频道介绍
        if data == "channel_info":
            info_text = """📢 频道介绍

这是一个教师评价平台，帮助同学们：
✅ 了解��师的教学风格
✅ 参考其他同学的评价
✅ 做出选课决定
✅ 互相分享学习体验

🎯 频道内容：
• 热门教师排行榜
• 评价统计分析
• 用户反馈和建议

🔗 加入频道获得：
• 实时评价更新
• 教师排行榜
• 社区讨论

点击下方按钮加入频道："""
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            from config import CHANNEL_LINK
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📢 立即加入频道",
                    url=CHANNEL_LINK
                )],
                [InlineKeyboardButton(
                    text="🔙 返回",
                    callback_data="back_to_start"
                )]
            ])
            
            await callback.answer()
            await bot.send_message(callback.from_user.id, info_text, reply_markup=kb)
            return

        # 处理如何评价
        if data == "how_to_rate":
            rate_text = """⭐ 如何评价教师

步骤 1️⃣：输入教师名称
在群组中输入: @李老师

步骤 2️⃣：查看评价卡片
机器人显示该教师的：
• 推荐人数: 👍 5
• 不推荐人数: 👎 2
• 历史评价记录

步骤 3️⃣：选择态度
• 👍 推荐
• 👎 不推荐

步骤 4️⃣：填写理由
在私聊中输入评价理由
至少 12 个字

评价示例：
✅ "讲课清楚，课件详细，认真解答问题，非常推荐"
✅ "教学速度较快，基础差的同学跟不上"

步骤 5️⃣：提交
评价成功后机器人会显示确认信息

💡 小贴士：
• 一个教师只能评价一次
• 评价要真实客观
• 具体说明优缺点
• 尊重教师和同学"""
            
            await callback.answer()
            await bot.send_message(callback.from_user.id, rate_text)
            return

        # 处理常见问题
        if data == "faq":
            faq_text = """❓ 常见问题

Q: 如何查询教师评价？
A: 输入 @teacher_name，机器人会显示评价统计

Q: 我可以评价多少次？
A: 每个教师只能评价一次，不同教师可以多次评价

Q: 评价会立即显示吗？
A: 是的，评价提交后立即保存和显示

Q: 可以修改评价吗？
A: 当前不支持修改，请联系管理员

Q: 评价内容会被公开吗？
A: 会的，所有用户都可以看到评价

Q: 如何举报不当评价？
A: 联系管理员，提供教师名称和时间

Q: 可以匿名评价吗？
A: 可以使用别的账号，但机器人会记录用户ID

Q: 为什么看不到我的评价？
A: 检查教师名称是否正确，或稍后刷新

Q: 机器人什么时候更新排行榜？
A: 实时更新

Q: 如何成为管理员？
A: 使用 /myid 获取ID，告诉原管理员"""
            
            await callback.answer()
            await bot.send_message(callback.from_user.id, faq_text)
            return

        # 处理联系管理员
        if data == "contact_admin":
            admin_text = """📞 联系管理员

如果您有任何问题或建议，可以：

1️⃣ 在群组中反馈
   标记管理员，描述问题

2️⃣ 私聊管理员
   获取管理员联系方式

3️⃣ 报告问题
   • 不当评价举报
   • 机器人故障报告
   • 功能建议反馈

管理员会尽快回复您！"""
            
            await callback.answer()
            await bot.send_message(callback.from_user.id, admin_text)
            return

        # 处理重新验证
        if data == "retry_verify":
            await callback.answer("正在重新验证您的身份...")
            # 重新调用 /start
            await cmd_start(callback.message)
            return

        # 处理返回主菜单
        if data == "back_to_start":
            from handlers.private import cmd_start
            await callback.answer()
            await cmd_start(callback.message)
            return

    except Exception as e:
        logger.error(f"处理回调时出错: {e}")
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