# handlers/callback.py
"""
回调查询处理模块
处理所有按钮点击事件
"""

import logging
from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import (
    check_user_rated_teacher,
    get_all_required_channels
)
from states import RatingStates
from bot_instance import bot, get_channel_invite_link

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query()
async def handle_callback(callback: CallbackQuery, state: FSMContext):
    """处理所有回调查询"""
    try:
        data = callback.data
        logger.info(f"📌 处理回调: {data}")
        
        # ==================== 评价按钮 ====================
        if data.startswith("rec|"):
            parts = data.split("|", 2)
            if len(parts) < 3:
                await callback.answer("❌ 数据错误", show_alert=True)
                return
            
            try:
                recommend = int(parts[1])
                teacher = parts[2]
            except (ValueError, IndexError):
                await callback.answer("❌ 数据错误", show_alert=True)
                return
            
            user_id = callback.from_user.id
            
            if check_user_rated_teacher(teacher, user_id):
                await callback.answer(
                    f"❌ 您已经评价过 @{teacher} 了",
                    show_alert=True
                )
                return
            
            logger.info(f"✅ 用户 {user_id} 选择了 {'推荐' if recommend else '不推荐'} @{teacher}")
            
            await state.update_data(
                teacher=teacher,
                recommend=recommend,
                user_id=user_id
            )
            await state.set_state(RatingStates.waiting_reason)
            
            await callback.answer()
            
            emoji = "👍" if recommend else "👎"
            await bot.send_message(
                user_id,
                f"""📝 您选择了 {emoji} {'推荐' if recommend else '不推荐'} @{teacher}

请在下方填写您的评价理由（至少 12 字）：

💡 评价示例：
"讲课很生动，逻辑清晰，认真负责，强烈推荐"
"教学速度较快，不太照顾基础差的同学"
"""
            )
            return
        
        # ==================== 快捷按钮 ====================
        
        if data == "show_help":
            await callback.answer()
            await bot.send_message(
                callback.from_user.id,
                """📖 快速帮助

⭐ 使用步骤：
1️⃣ 输入 @teacher_name
2️⃣ 点击 👍 或 👎
3️⃣ 填写评价理由（12字以上）
4️⃣ 提交

📝 评价示例：
"讲课很生动，逻辑清晰，认真负责，强烈推荐"

💡 更多帮助:
/帮助"""
            )
            return
        
        if data == "how_to_rate":
            await callback.answer()
            await bot.send_message(callback.from_user.id, """⭐ 如何评价教师

步骤 1️⃣：输入教师名称
在群组中输入: @李老师

步骤 2️⃣：查看评价卡片
机器人显示该教师的：
• 推荐人数: 👍 5
• 不推荐人数: 👎 2
• 最新评价

步骤 3️⃣：选择态度
• 👍 推荐
• 👎 不推荐

步骤 4️⃣：填写理由
在私聊中输入评价理由
至少 12 个字

步骤 5️⃣：提交
评价成功后机器人会显示确认

💡 小贴士：
• 一个教师只能评价一次
• 评价要真实客观
• 具体说明优缺点""")
            return
        
        if data == "faq":
            await callback.answer()
            await bot.send_message(callback.from_user.id, """❓ 常见问题

Q: 如何查询教师评价？
A: 输入 @teacher_name

Q: 可以评价多少次？
A: 每个教师只能一次，不同教师可多次

Q: 评价立即显示吗？
A: 是的，立即保存和显示

Q: 可以修改评价吗？
A: 不支持修改

Q: 评价公开吗？
A: 是的，所有用户都能看到

Q: 如何举报不当评价？
A: 联系管理员

Q: 可以匿名评价吗？
A: 可以用别账号""")
            return
        
        if data == "contact_admin":
            await callback.answer()
            await bot.send_message(callback.from_user.id, """📞 联系管理员

如有问题或建议：

1️⃣ 在群组中反馈
   标记管理员

2️⃣ 私聊管理员
   获取联系方式

3️⃣ 报告问题
   • 不当评价举报
   • 机器人故障
   • 功能建议

管理员会尽快回复！""")
            return
        
        if data == "channel_info":
            channels = get_all_required_channels()
            
            if not channels:
                await callback.answer("❌ 未设置频道", show_alert=True)
                return
            
            await callback.answer()
            
            kb_buttons = []
            for channel_id in channels:
                try:
                    channel = await bot.get_chat(channel_id)
                    link = await get_channel_invite_link(channel_id)
                    if link:
                        kb_buttons.append([
                            InlineKeyboardButton(text=f"📢 {channel.title}", url=link)
                        ])
                except:
                    pass
            
            kb_buttons.append([InlineKeyboardButton(text="🔙 返回", callback_data="back_to_start")])
            
            await bot.send_message(
                callback.from_user.id,
                """📢 频道介绍

教师评价平台，帮助同学们：
✅ 了解教师风格
✅ 参考他人评价
✅ 做出选课决定

🎯 频道内容：
• 热门教师排行
• 评价统计分析
• 用户反馈""",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons)
            )
            return
        
        if data == "retry_verify":
            await callback.answer("正在重新验证...")
            from handlers.private import cmd_start
            await cmd_start(callback.message)
            return
        
        if data == "back_to_start":
            await callback.answer()
            from handlers.private import cmd_start
            await cmd_start(callback.message)
            return
        
        if data == "check_all_subscriptions":
            channels = get_all_required_channels()
            user_id = callback.from_user.id
            
            not_subscribed = []
            for channel_id in channels:
                try:
                    member = await bot.get_chat_member(channel_id, user_id)
                    if member.status in ('left', 'kicked', 'restricted'):
                        not_subscribed.append(channel_id)
                except:
                    not_subscribed.append(channel_id)
            
            if not_subscribed:
                await callback.answer("❌ 您还未全部加入频道", show_alert=True)
            else:
                await callback.answer("✅ 验证成功！")
                from handlers.private import cmd_start
                await cmd_start(callback.message)
            return
        
        # ==================== 跳转私聊用户 ====================
        if data.startswith("jump_user|"):
            parts = data.split("|")
            if len(parts) >= 2:
                try:
                    user_id = int(parts[1])
                    teacher_name = parts[2] if len(parts) > 2 else "未知教师"
                    rating_id = parts[3] if len(parts) > 3 else "未知"
                    
                    # 显示用户信息
                    try:
                        user_chat = await bot.get_chat(user_id)
                        username = user_chat.username or "无"
                        first_name = user_chat.first_name or "用户"
                        
                        info_text = f"""👤 用户信息

名字: {first_name}
用户名: @{username}
ID: <code>{user_id}</code>
教师: @{teacher_name}
评价ID: {rating_id}

🔗 跳转方式：
• 点击下方按钮私聊用户
• 或复制 ID 后手动发送"""
                        
                        # 创建私聊按钮
                        kb = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text="💬 私聊用户",
                                url=f"https://t.me/user?id={user_id}"
                            )],
                            [InlineKeyboardButton(
                                text="🔙 返回列表",
                                callback_data=f"back_to_ratings|{teacher_name}"
                            )]
                        ])
                        
                        await callback.answer()
                        await bot.send_message(
                            callback.from_user.id,
                            info_text,
                            reply_markup=kb
                        )
                        
                        logger.info(f"✅ 管理员 {callback.from_user.id} 跳转到用户 {user_id}")
                    
                    except Exception as e:
                        logger.error(f"获取用户信息失败: {e}")
                        await callback.answer("❌ 获取用户信息失败", show_alert=True)
                
                except ValueError:
                    await callback.answer("❌ 用户ID格式错误", show_alert=True)
            return
        
        # ==================== 删除单条评价 ====================
        if data.startswith("delete_rating|"):
            parts = data.split("|")
            if len(parts) >= 3:
                teacher_name = parts[1]
                rating_id = parts[2]
                
                # 确认删除
                confirm_text = f"""⚠️ 确认删除评价

教师: @{teacher_name}
评价ID: {rating_id}

此操作不可恢复！

点击下方按钮确认删除"""
                
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="✅ 确认删除",
                        callback_data=f"confirm_delete_rating|{teacher_name}|{rating_id}"
                    )],
                    [InlineKeyboardButton(
                        text="❌ 取消",
                        callback_data=f"cancel_delete"
                    )]
                ])
                
                await callback.answer()
                await bot.send_message(
                    callback.from_user.id,
                    confirm_text,
                    reply_markup=kb
                )
                
                logger.info(f"⚠️ 管理员 {callback.from_user.id} 请求删除评价 {rating_id}")
            return
        
        # ==================== 确认删除单条评价 ====================
        if data.startswith("confirm_delete_rating|"):
            parts = data.split("|")
            if len(parts) >= 3:
                teacher_name = parts[1]
                rating_id = parts[2]
                
                from database import delete_rating_by_id
                result = delete_rating_by_id(rating_id, teacher_name)
                
                await callback.answer()
                await bot.send_message(
                    callback.from_user.id,
                    result["msg"]
                )
                
                if result["success"]:
                    logger.warning(f"🗑️ 管理员 {callback.from_user.id} 删除了评价 {rating_id}")
            return
        
        # ==================== 删除教师全部数据 ====================
        if data.startswith("delete_all_teacher|"):
            teacher_name = data.split("|")[1]
            
            from database import get_teacher_stats
            stats = get_teacher_stats(teacher_name)
            
            confirm_text = f"""⚠️ 确认删除教师全部数据

教师: @{teacher_name}
总评价数: {stats['total']}
👍 推荐: {stats['recommend']}
👎 不推荐: {stats['not_recommend']}

⚠️ 此操作不可恢复！

点击下方按钮确认删除"""
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="✅ 确认删除",
                    callback_data=f"confirm_delete_teacher|{teacher_name}"
                )],
                [InlineKeyboardButton(
                    text="❌ 取消",
                    callback_data=f"cancel_delete"
                )]
            ])
            
            await callback.answer()
            await bot.send_message(
                callback.from_user.id,
                confirm_text,
                reply_markup=kb
            )
            
            logger.info(f"⚠️ 管理员 {callback.from_user.id} 请求删除教师 @{teacher_name} 的全部数据")
            return
        
        # ==================== 确认删除教师全部数据 ====================
        if data.startswith("confirm_delete_teacher|"):
            teacher_name = data.split("|")[1]
            
            from database import delete_teacher_data_from_db
            result = delete_teacher_data_from_db(teacher_name)
            
            await callback.answer()
            await bot.send_message(
                callback.from_user.id,
                result["msg"]
            )
            
            if result["success"]:
                logger.warning(f"🗑️ 管理员 {callback.from_user.id} 删除了教师 @{teacher_name} 的全部数据")
            return
        
        # ==================== 返回评价列表 ====================
        if data.startswith("back_to_ratings|"):
            teacher_name = data.split("|")[1]
            
            await callback.answer()
            
            # 重新调用查看评价的逻辑
            from database import get_teacher_all_ratings
            
            ratings = get_teacher_all_ratings(teacher_name)
            
            if not ratings:
                await bot.send_message(
                    callback.from_user.id,
                    f"❌ 教师 @{teacher_name} 没有任何评价"
                )
                return
            
            text = f"""📝 教师 @{teacher_name} 的所有评价 ({len(ratings)} 条)

"""
            
            kb_buttons = []
            
            for i, rating in enumerate(ratings[:10], 1):
                rating_id = rating[0]
                user_id = rating[1]
                recommend = rating[2]
                reason = rating[3]
                time = rating[4]
                
                emoji = "👍" if recommend else "👎"
                text += f"""{i}. {emoji} 用户 ID: {user_id}
   理由: {reason[:50]}...
   时间: {time}

"""
                
                btn_text = f"{emoji} 用户 {user_id}"
                kb_buttons.append([
                    InlineKeyboardButton(
                        text=btn_text,
                        callback_data=f"jump_user|{user_id}|{teacher_name}|{rating_id}"
                    ),
                    InlineKeyboardButton(
                        text="🗑️ 删",
                        callback_data=f"delete_rating|{teacher_name}|{rating_id}"
                    )
                ])
            
            if len(ratings) > 10:
                text += f"\n... 还有 {len(ratings) - 10} 条评价"
            
            kb_buttons.append([
                InlineKeyboardButton(
                    text="🗑️ 删除该教师全部数据",
                    callback_data=f"delete_all_teacher|{teacher_name}"
                )
            ])
            
            kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
            
            await bot.send_message(
                callback.from_user.id,
                text,
                reply_markup=kb
            )
            
            logger.info(f"✅ 返回教师 @{teacher_name} 的评价列表")
            return
        
        # ==================== 取消删除 ====================
        if data == "cancel_delete":
            await callback.answer()
            await bot.send_message(
                callback.from_user.id,
                "✅ 删除已取消"
            )
            return

    except Exception as e:
        logger.error(f"处理回调时出错: {e}", exc_info=True)
        await callback.answer(f"❌ 出错: {str(e)[:50]}", show_alert=True)