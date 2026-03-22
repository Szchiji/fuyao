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
    get_all_required_channels,
    remove_required_channel,
    get_teacher_stats,
    get_global_stats,
    get_connection,
    get_teacher_all_ratings,
    delete_rating_by_id,
    delete_teacher_data_from_db,
    get_leaderboard
)
from states import RatingStates, AdminStates
from bot_instance import bot, get_channel_invite_link
from utils.helpers import format_leaderboard_text

logger = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    """检查用户是否为管理员"""
    from config import ADMIN_IDS
    return user_id in ADMIN_IDS


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
• 最新评价（含 ID）

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

        if data == "show_leaderboard":
            leaderboard = get_leaderboard(10)
            text = format_leaderboard_text(leaderboard)
            await callback.answer()

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 返回主菜单", callback_data="back_to_start")]
            ])
            await bot.send_message(callback.from_user.id, text, reply_markup=kb)
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

        # ==================== 管理后台回调 ====================

        if data == "admin_menu":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            from handlers.admin import build_admin_menu_keyboard
            stats = get_global_stats()
            channels = get_all_required_channels()
            channel_status = f"✅ {len(channels)} 个频道" if channels else "❌ 未设置"

            menu_text = f"""🛠️ 管理员后台

📊 统计数据：
• 总评价数: {stats['total_eval']}
• 评价教师数: {stats['total_teacher']}
• 今日评价: {stats['today']}

🔐 频道管理：
• 状态: {channel_status}

请点击下方按钮进行操作："""

            await callback.answer()
            await bot.send_message(
                callback.from_user.id,
                menu_text,
                reply_markup=build_admin_menu_keyboard()
            )
            return

        if data == "admin_stats":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            stats = get_global_stats()
            avg = round(stats['total_eval'] / max(1, stats['total_teacher']), 2)

            text = f"""📊 详细统计

📈 评价数据：
• 总评价数: {stats['total_eval']}
• 评价教师数: {stats['total_teacher']}
• 今日评价: {stats['today']}

📊 平均每个教师评价数: {avg}

🔄 运行状态: ✅ 正常"""

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
            ])
            await callback.answer()
            await bot.send_message(callback.from_user.id, text, reply_markup=kb)
            return

        if data == "admin_db":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            try:
                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM recs")
                total = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(DISTINCT teacher) FROM recs")
                teachers = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM recs WHERE recommend = 1")
                rec = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM recs WHERE recommend = 0")
                not_rec = cursor.fetchone()[0]

                conn.close()

                text = f"""📊 数据库信息

📈 统计：
• 总评价: {total}
• 教师数: {teachers}
• 👍 推荐: {rec}
• 👎 不推荐: {not_rec}

💾 数据库状态: ✅ 正常"""

                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
                ])
                await callback.answer()
                await bot.send_message(callback.from_user.id, text, reply_markup=kb)
            except Exception as e:
                await callback.answer(f"❌ 错误: {str(e)[:50]}", show_alert=True)
            return

        if data == "admin_channels":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            channels = get_all_required_channels()

            if not channels:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ 添加频道", callback_data="admin_add_channel")],
                    [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
                ])
                await callback.answer()
                await bot.send_message(callback.from_user.id, "❌ 未添加任何频道", reply_markup=kb)
                return

            text = f"📋 已添加频道 ({len(channels)} 个)\n\n"
            kb_buttons = []

            for i, ch_id in enumerate(channels, 1):
                try:
                    ch = await bot.get_chat(ch_id)
                    count = await bot.get_chat_member_count(ch_id)
                    text += f"{i}. {ch.title}\n   📌 ID: <code>{ch_id}</code>\n   👥 成员: {count}\n\n"
                except Exception as e:
                    logger.error(f"获取频道信息失败: {e}")
                    text += f"{i}. (获取失败) ID: <code>{ch_id}</code>\n\n"

                kb_buttons.append([
                    InlineKeyboardButton(text=f"🗑️ 删除 {ch_id}", callback_data=f"delete_channel|{ch_id}")
                ])

            kb_buttons.append([
                InlineKeyboardButton(text="➕ 添加频道", callback_data="admin_add_channel"),
                InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")
            ])

            await callback.answer()
            await bot.send_message(
                callback.from_user.id,
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons)
            )
            return

        if data.startswith("delete_channel|"):
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            ch_id = data.split("|")[1]

            confirm_text = f"""⚠️ 确认删除频道

频道 ID: <code>{ch_id}</code>

此操作不可恢复！"""

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="✅ 确认删除",
                    callback_data=f"confirm_delete_channel|{ch_id}"
                )],
                [InlineKeyboardButton(text="❌ 取消", callback_data="admin_channels")]
            ])

            await callback.answer()
            await bot.send_message(callback.from_user.id, confirm_text, reply_markup=kb)
            return

        if data.startswith("confirm_delete_channel|"):
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            ch_id = data.split("|")[1]
            result = remove_required_channel(ch_id)

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 查看频道列表", callback_data="admin_channels")],
                [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
            ])
            await callback.answer()
            await bot.send_message(callback.from_user.id, result["msg"], reply_markup=kb)
            logger.info(f"✅ 管理员 {callback.from_user.id} 通过按钮删除频道 {ch_id}")
            return

        if data == "admin_test_channels":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            channels = get_all_required_channels()

            if not channels:
                await callback.answer("❌ 未添加任何频道", show_alert=True)
                return

            text = f"🧪 频道测试 ({len(channels)} 个)\n\n"

            for i, ch_id in enumerate(channels, 1):
                try:
                    ch = await bot.get_chat(ch_id)
                    mem = await bot.get_chat_member(ch_id, bot.id)
                    is_admin = mem.status == "administrator"
                    status_emoji = "✅" if is_admin else "❌"
                    text += f"{i}. {status_emoji} {ch.title}\n   📌 ID: <code>{ch_id}</code>\n   🤖 状态: {mem.status}\n\n"
                except Exception as e:
                    logger.error(f"测试频道失败: {e}")
                    text += f"{i}. ❌ 错误: {str(e)[:30]}\n\n"

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
            ])
            await callback.answer()
            await bot.send_message(callback.from_user.id, text, reply_markup=kb)
            return

        if data == "admin_diagnose":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            channels = get_all_required_channels()

            if not channels:
                await callback.answer("❌ 未添加任何频道", show_alert=True)
                return

            await callback.answer("🔧 诊断中...")

            try:
                text = "🔧 诊断报告\n\n"

                for idx, ch_id in enumerate(channels, 1):
                    text += f"\n━━━ 频道 {idx}/{len(channels)} ━━━\n"
                    try:
                        ch = await bot.get_chat(ch_id)
                        text += f"✅ 频道名: {ch.title}\n"

                        mem = await bot.get_chat_member(ch_id, bot.id)
                        is_admin = mem.status == "administrator"
                        text += f"{'✅' if is_admin else '❌'} 管理员: {is_admin}\n"

                        count = await bot.get_chat_member_count(ch_id)
                        text += f"✅ 成员: {count}\n"

                        if is_admin:
                            text += f"✅ 频道连接正常\n"
                        else:
                            text += f"❌ 机器人不是管理员，需要添加管理员权限\n"
                    except Exception as e:
                        text += f"❌ 错误: {str(e)[:50]}\n"

                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
                ])
                await bot.send_message(callback.from_user.id, text, reply_markup=kb)
            except Exception as e:
                logger.error(f"诊断失败: {e}")
                await bot.send_message(callback.from_user.id, f"❌ 诊断失败: {e}")
            return

        if data == "admin_add_channel":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            await state.set_state(AdminStates.waiting_channel_id)
            await callback.answer()

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ 取消", callback_data="cancel_admin_input")]
            ])
            await bot.send_message(
                callback.from_user.id,
                """➕ 添加频道

请发送频道 ID（格式: -1001234567890）

💡 如何获取频道 ID：
1. 将机器人添加为频道管理员
2. 频道 ID 以 -100 开头
3. 可使用 @userinfobot 查询

直接发送频道 ID 即可：""",
                reply_markup=kb
            )
            return

        if data == "admin_set_welcome":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            await state.set_state(AdminStates.waiting_welcome_msg)
            await callback.answer()

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ 取消", callback_data="cancel_admin_input")]
            ])
            await bot.send_message(
                callback.from_user.id,
                """✏️ 设置欢迎语

请发送新的欢迎语内容：

💡 说明：
• 用户发送 /开始 时会显示此欢迎语
• 支持 HTML 格式
• 示例: <b>欢迎使用教师评价机器人！</b>

直接发送欢迎语内容即可：""",
                reply_markup=kb
            )
            return

        if data == "admin_manage_teacher":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            await state.set_state(AdminStates.waiting_teacher_name)
            await callback.answer()

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ 取消", callback_data="cancel_admin_input")]
            ])
            await bot.send_message(
                callback.from_user.id,
                """👨‍🏫 管理教师

请发送要管理的教师名称（可带或不带 @）：

💡 示例：
• 李老师
• @王教授
• 数学老师

直接发送教师名称即可：""",
                reply_markup=kb
            )
            return

        if data == "cancel_admin_input":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            await state.clear()
            from handlers.admin import build_admin_menu_keyboard
            stats = get_global_stats()
            channels = get_all_required_channels()
            channel_status = f"✅ {len(channels)} 个频道" if channels else "❌ 未设置"

            menu_text = f"""🛠️ 管理员后台

📊 统计数据：
• 总评价数: {stats['total_eval']}
• 评价教师数: {stats['total_teacher']}
• 今日评价: {stats['today']}

🔐 频道管理：
• 状态: {channel_status}

请点击下方按钮进行操作："""

            await callback.answer("✅ 已取消")
            await bot.send_message(
                callback.from_user.id,
                menu_text,
                reply_markup=build_admin_menu_keyboard()
            )
            return

        if data == "admin_help":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            help_text = """📖 管理员帮助

🎛️ 基础命令：
• /管理 - 显示管理后台（含按钮菜单）
• /统计 - 查看统计数据
• /数据库 - 查看数据库信息

🔐 频道管理：
• /添加频道 [ID] - 添加频道要求
• /删除频道 [ID] - 删除频道要求
• /频道列表 - 查看所有频道（含删除按钮）
• /测试频道 - 测试所有频道
• /诊断频道 - 深度诊断频道

✏️ 内容管理：
• /设置欢迎语 [欢迎语] - 设置欢迎语

👨‍🏫 教师管理：
• /管理教师 [教师名] - 管理教师数据（含按钮）
• /查看评价 [教师名] - 查看所有评价（含操作按钮）
• /删除教师数据 [教师名] - 删除教师所有数据（含确认按钮）
• /删除评价 [教师名] [评价ID] - 删除单条评价

💡 交互式操作（推荐）：
点击下方菜单按钮，所有操作均可通过按钮完成！"""

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛠️ 打开管理菜单", callback_data="admin_menu")]
            ])
            await callback.answer()
            await bot.send_message(callback.from_user.id, help_text, reply_markup=kb)
            return

        if data.startswith("view_teacher_ratings|"):
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            teacher_name = data.split("|", 1)[1]
            ratings = get_teacher_all_ratings(teacher_name)

            if not ratings:
                await callback.answer(f"❌ 教师 @{teacher_name} 没有任何评价", show_alert=True)
                return

            from handlers.admin import build_ratings_view
            text, kb = build_ratings_view(teacher_name, ratings)

            await callback.answer()
            await bot.send_message(callback.from_user.id, text, reply_markup=kb)
            logger.info(f"✅ 管理员 {callback.from_user.id} 通过按钮查看教师 @{teacher_name} 的评价")
            return

        # ==================== 跳转私聊用户 ====================
        if data.startswith("jump_user|"):
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            parts = data.split("|")
            if len(parts) >= 2:
                try:
                    user_id = int(parts[1])
                    teacher_name = parts[2] if len(parts) > 2 else "未知教师"
                    rating_id = parts[3] if len(parts) > 3 else "未知"

                    try:
                        user_chat = await bot.get_chat(user_id)
                        username = user_chat.username or "无"
                        first_name = user_chat.first_name or "用户"

                        info_text = f"""👤 用户信息

名字: {first_name}
用户名: @{username}
ID: <code>{user_id}</code>
教师: @{teacher_name}
评价ID: #{rating_id}

🔗 跳转方式：
• 点击下方按钮私聊用户
• 或复制 ID 后手动发送"""

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
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            parts = data.split("|")
            if len(parts) >= 3:
                teacher_name = parts[1]
                rating_id = parts[2]

                confirm_text = f"""⚠️ 确认删除评价

教师: @{teacher_name}
评价ID: #{rating_id}

此操作不可恢复！"""

                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="✅ 确认删除",
                        callback_data=f"confirm_delete_rating|{teacher_name}|{rating_id}"
                    )],
                    [InlineKeyboardButton(
                        text="❌ 取消",
                        callback_data=f"back_to_ratings|{teacher_name}"
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
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            parts = data.split("|")
            if len(parts) >= 3:
                teacher_name = parts[1]
                rating_id = parts[2]

                result = delete_rating_by_id(rating_id, teacher_name)

                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🔙 返回评价列表",
                        callback_data=f"back_to_ratings|{teacher_name}"
                    )],
                    [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
                ])

                await callback.answer()
                await bot.send_message(
                    callback.from_user.id,
                    result["msg"],
                    reply_markup=kb
                )

                if result["success"]:
                    logger.warning(f"🗑️ 管理员 {callback.from_user.id} 删除了评价 {rating_id}")
            return

        # ==================== 删除教师全部数据 ====================
        if data.startswith("delete_all_teacher|"):
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            teacher_name = data.split("|")[1]
            stats = get_teacher_stats(teacher_name)

            confirm_text = f"""⚠️ 确认删除教师全部数据

教师: @{teacher_name}
总评价数: {stats['total']}
👍 推荐: {stats['recommend']}
👎 不推荐: {stats['not_recommend']}

⚠️ 此操作不可恢复！"""

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="✅ 确认删除",
                    callback_data=f"confirm_delete_teacher|{teacher_name}"
                )],
                [InlineKeyboardButton(
                    text="❌ 取消",
                    callback_data="cancel_delete"
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
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            teacher_name = data.split("|")[1]

            result = delete_teacher_data_from_db(teacher_name)

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
            ])

            await callback.answer()
            await bot.send_message(
                callback.from_user.id,
                result["msg"],
                reply_markup=kb
            )

            if result["success"]:
                logger.warning(f"🗑️ 管理员 {callback.from_user.id} 删除了教师 @{teacher_name} 的全部数据")
            return

        # ==================== 返回评价列表 ====================
        if data.startswith("back_to_ratings|"):
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            teacher_name = data.split("|")[1]
            ratings = get_teacher_all_ratings(teacher_name)

            if not ratings:
                await callback.answer(f"❌ 教师 @{teacher_name} 没有任何评价", show_alert=True)
                return

            from handlers.admin import build_ratings_view
            text, kb = build_ratings_view(teacher_name, ratings)

            await callback.answer()
            await bot.send_message(callback.from_user.id, text, reply_markup=kb)
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
