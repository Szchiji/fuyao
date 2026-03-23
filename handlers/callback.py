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
    get_leaderboard,
    get_start_message,
    get_start_buttons,
    set_start_message,
    set_start_buttons,
    get_all_user_ids,
    get_teacher_info,
    set_teacher_info,
    get_teacher_reviews_page
)
from states import RatingStates, AdminStates
from bot_instance import bot, get_channel_invite_link
from utils.helpers import format_leaderboard_text

logger = logging.getLogger(__name__)
router = Router()

REVIEWS_PER_PAGE = 5  # 「更多评价」每页显示的评价条数


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
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 返回主菜单", callback_data="back_to_start")]
            ])
            await callback.message.edit_text(
                """📖 快速帮助

⭐ 使用步骤：
1️⃣ 输入 @teacher_name
2️⃣ 点击 👍 或 👎
3️⃣ 填写评价理由（12字以上）
4️⃣ 提交

📝 评价示例：
"讲课很生动，逻辑清晰，认真负责，强烈推荐"

💡 更多帮助:
/帮助""",
                reply_markup=kb
            )
            return

        if data == "how_to_rate":
            await callback.answer()
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 返回主菜单", callback_data="back_to_start")]
            ])
            await callback.message.edit_text("""⭐ 如何评价教师

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
• 具体说明优缺点""", reply_markup=kb)
            return

        if data == "faq":
            await callback.answer()
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 返回主菜单", callback_data="back_to_start")]
            ])
            await callback.message.edit_text("""❓ 常见问题

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
A: 可以用别账号""", reply_markup=kb)
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
            await callback.message.edit_text(text, reply_markup=kb)
            return

        if data == "retry_verify":
            await callback.answer("正在重新验证...")
            from handlers.private import cmd_start
            await cmd_start(callback.message)
            return

        if data == "back_to_start":
            await callback.answer()
            from handlers.private import _build_welcome_keyboard
            default_welcome = (
                "👋 欢迎使用狼评机器人！🎓\n\n"
                "这是一个教师评价平台，帮助同学们了解教师的教学情况。\n\n"
                "📝 使用方法：\n"
                "在群组中输入 @teacher_name 来查询或评价教师\n\n"
                "例如：@李老师、@王教授、@张老师\n\n"
                "💡 更多帮助请输入 /帮助"
            )
            welcome = get_start_message(default_welcome)
            start_buttons = get_start_buttons()
            kb = _build_welcome_keyboard(start_buttons)
            await callback.message.answer(welcome, reply_markup=kb)
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
            await callback.message.edit_text(
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
            await callback.message.edit_text(text, reply_markup=kb)
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
                await callback.message.edit_text(text, reply_markup=kb)
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
                await callback.message.edit_text("❌ 未添加任何频道", reply_markup=kb)
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
            await callback.message.edit_text(
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
            await callback.message.edit_text(confirm_text, reply_markup=kb)
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
            await callback.message.edit_text(result["msg"], reply_markup=kb)
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
            await callback.message.edit_text(text, reply_markup=kb)
            return

        if data == "admin_diagnose":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            channels = get_all_required_channels()

            if not channels:
                await callback.answer("❌ 未添加任何频道", show_alert=True)
                return

            await callback.answer()
            await callback.message.edit_text(f"🔧 诊断中，请稍候...（共 {len(channels)} 个频道）")

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
                await callback.message.edit_text(text, reply_markup=kb)
            except Exception as e:
                logger.error(f"诊断失败: {e}")
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
                ])
                await callback.message.edit_text(f"❌ 诊断失败: {e}", reply_markup=kb)
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
            await callback.message.edit_text(
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
            await callback.message.edit_text(
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
            await callback.message.edit_text(
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
            await callback.message.edit_text(
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
• /设置欢迎语 [欢迎语] - 设置欢迎语（支持添加按钮）

📢 广播功能：
• 点击菜单中的 📢 广播消息 按钮
• 向所有使用过机器人的用户发送消息
• 支持添加自定义按钮

👨‍🏫 教师管理：
• /管理教师 [教师名] - 管理教师数据（含按钮）
• /查看评价 [教师名] - 查看所有评价（含操作按钮）
• /删除教师数据 [教师名] - 删除教师所有数据（含确认按钮）
• /删除评价 [教师名] [评价ID] - 删除单条评价

💡 交互式操作（推荐）：
点击下方菜单按钮，所有操作均可通过按钮完成！"""

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛠️ 返回管理菜单", callback_data="admin_menu")]
            ])
            await callback.answer()
            await callback.message.edit_text(help_text, reply_markup=kb)
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
            await callback.message.edit_text(text, reply_markup=kb)
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
                        await callback.message.edit_text(
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
                await callback.message.edit_text(confirm_text, reply_markup=kb)

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
                await callback.message.edit_text(result["msg"], reply_markup=kb)

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
            await callback.message.edit_text(confirm_text, reply_markup=kb)

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
            await callback.message.edit_text(result["msg"], reply_markup=kb)

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
            await callback.message.edit_text(text, reply_markup=kb)
            logger.info(f"✅ 返回教师 @{teacher_name} 的评价列表")
            return

        # ==================== 取消删除 ====================
        if data == "cancel_delete":
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

            await callback.answer("✅ 删除已取消")
            await callback.message.edit_text(menu_text, reply_markup=build_admin_menu_keyboard())
            return

        # ==================== 欢迎语按钮相关回调 ====================

        if data == "save_welcome_no_buttons":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            state_data = await state.get_data()
            welcome_msg = state_data.get("welcome_msg", "")
            await state.clear()

            if welcome_msg:
                set_start_message(welcome_msg)
                set_start_buttons([])

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
            ])
            await callback.answer()
            await callback.message.edit_text(
                f"✅ 欢迎语已保存（无附加按钮）",
                reply_markup=kb
            )
            return

        if data == "add_welcome_buttons":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            await callback.answer()
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ 取消", callback_data="cancel_welcome_buttons")]
            ])
            await callback.message.edit_text(
                """🔘 添加欢迎语按钮

请按以下格式发送按钮信息（每行一个按钮，最多 5 个）：

格式：按钮名称|链接地址

示例：
加入官方群|https://t.me/xxxx
查看公告|https://example.com/news

直接发送按钮内容即可：""",
                reply_markup=kb
            )
            return

        if data == "cancel_welcome_buttons":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            await state.clear()
            from handlers.admin import build_admin_menu_keyboard
            await callback.answer("✅ 已取消")
            stats = get_global_stats()
            channels = get_all_required_channels()
            channel_status = f"✅ {len(channels)} 个频道" if channels else "❌ 未设置"
            menu_text = (
                f"🛠️ 管理员后台\n\n"
                f"📊 统计数据：\n• 总评价数: {stats['total_eval']}\n"
                f"• 评价教师数: {stats['total_teacher']}\n• 今日评价: {stats['today']}\n\n"
                f"🔐 频道管理：\n• 状态: {channel_status}\n\n请点击下方按钮进行操作："
            )
            await callback.message.edit_text(menu_text, reply_markup=build_admin_menu_keyboard())
            return

        # ==================== 广播相关回调 ====================

        if data == "admin_broadcast":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            await state.set_state(AdminStates.waiting_broadcast_msg)
            await callback.answer()

            user_count = len(get_all_user_ids())
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ 取消", callback_data="cancel_broadcast")]
            ])
            await callback.message.edit_text(
                f"""📢 发送广播消息

当前共有 {user_count} 名注册用户可接收广播。

请直接发送要广播的消息内容：

💡 支持换行、表情符号和 HTML 格式
💡 可在下一步选择是否附加按钮""",
                reply_markup=kb
            )
            return

        if data == "broadcast_send_no_buttons":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            state_data = await state.get_data()
            broadcast_msg = state_data.get("broadcast_msg", "")
            await state.clear()

            if not broadcast_msg:
                await callback.answer("❌ 广播内容为空", show_alert=True)
                return

            from handlers.admin import _do_broadcast
            await callback.answer()
            await callback.message.edit_text("📤 正在发送广播，请稍候...")
            await _do_broadcast(callback.message, broadcast_msg, [])
            return

        if data == "add_broadcast_buttons":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            await callback.answer()
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ 取消广播", callback_data="cancel_broadcast")]
            ])
            await callback.message.edit_text(
                """🔘 为广播添加按钮

请按以下格式发送按钮信息（每行一个按钮，最多 5 个）：

格式：按钮名称|链接地址

示例：
了解更多|https://example.com
加入群组|https://t.me/xxxx

直接发送按钮内容即可：""",
                reply_markup=kb
            )
            return

        if data == "cancel_broadcast":
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            await state.clear()
            from handlers.admin import build_admin_menu_keyboard
            await callback.answer("✅ 广播已取消")
            stats = get_global_stats()
            channels = get_all_required_channels()
            channel_status = f"✅ {len(channels)} 个频道" if channels else "❌ 未设置"
            menu_text = (
                f"🛠️ 管理员后台\n\n"
                f"📊 统计数据：\n• 总评价数: {stats['total_eval']}\n"
                f"• 评价教师数: {stats['total_teacher']}\n• 今日评价: {stats['today']}\n\n"
                f"🔐 频道管理：\n• 状态: {channel_status}\n\n请点击下方按钮进行操作："
            )
            await callback.message.edit_text(menu_text, reply_markup=build_admin_menu_keyboard())
            return

        # ==================== 设置教师昵称/ID ====================

        if data.startswith("set_teacher_info|"):
            if not _is_admin(callback.from_user.id):
                await callback.answer("❌ 无权限", show_alert=True)
                return

            teacher_name = data.split("|", 1)[1]
            teacher_info = get_teacher_info(teacher_name)

            await state.update_data(teacher_name=teacher_name)
            await state.set_state(AdminStates.waiting_teacher_info)
            await callback.answer()

            current = ""
            if teacher_info["nickname"] or teacher_info["teacher_id"]:
                current = f"\n\n当前设置：\n📛 昵称：{teacher_info['nickname'] or '（未设置）'}\n🆔 ID：{teacher_info['teacher_id'] or '（未设置）'}"

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ 取消", callback_data="cancel_admin_input")]
            ])
            await callback.message.edit_text(
                f"""✏️ 设置教师昵称/ID

教师：@{teacher_name}{current}

请按以下格式发送（昵称和ID用 | 分隔）：
昵称|ID编号

示例：
李明教授|T001
王老师|EMP202

如只设置昵称，可省略ID：
张数学老师

直接发送内容即可：""",
                reply_markup=kb
            )
            return

        # ==================== 查看更多评价 ====================

        if data.startswith("more_reviews|"):
            parts = data.split("|")
            if len(parts) < 3:
                await callback.answer("❌ 数据错误", show_alert=True)
                return

            teacher_name = parts[1]
            try:
                page = int(parts[2])
            except ValueError:
                page = 0

            per_page = REVIEWS_PER_PAGE
            reviews = get_teacher_reviews_page(teacher_name, page, per_page)
            stats = get_teacher_stats(teacher_name)
            teacher_info = get_teacher_info(teacher_name)
            total = stats["total"]

            if not reviews:
                await callback.answer("📭 没有更多评价了", show_alert=True)
                return

            nickname = teacher_info.get("nickname", "")
            tid = teacher_info.get("teacher_id", "")
            header = f"📋 @{teacher_name}"
            if nickname:
                header += f"（{nickname}）"
            if tid:
                header += f" · ID: {tid}"

            offset = page * per_page
            text = f"{header} 的评价\n\n"
            text += f"━━━━━━━━━━━━━━━━━━━\n"
            text += f"第 {offset + 1}–{min(offset + per_page, total)} 条 / 共 {total} 条\n"
            text += f"━━━━━━━━━━━━━━━━━━━\n\n"

            for i, review in enumerate(reviews, offset + 1):
                rec_emoji = "👍" if review[2] else "👎"
                reason_text = review[3]
                time_str = str(review[4])[:16] if review[4] else ""
                text += f"{i}. {rec_emoji} [#{review[0]}]\n"
                text += f"   💬 {reason_text[:60]}{'...' if len(reason_text) > 60 else ''}\n"
                if time_str:
                    text += f"   🕐 {time_str}\n"
                text += "\n"

            nav_buttons = []
            if page > 0:
                nav_buttons.append(
                    InlineKeyboardButton(text="⬅️ 上一页", callback_data=f"more_reviews|{teacher_name}|{page-1}")
                )
            if offset + per_page < total:
                nav_buttons.append(
                    InlineKeyboardButton(text="➡️ 下一页", callback_data=f"more_reviews|{teacher_name}|{page+1}")
                )

            kb_rows = []
            if nav_buttons:
                kb_rows.append(nav_buttons)
            kb_rows.append([
                InlineKeyboardButton(text="👍 推荐", callback_data=f"rec|1|{teacher_name}"),
                InlineKeyboardButton(text="👎 不推荐", callback_data=f"rec|0|{teacher_name}")
            ])

            kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
            await callback.answer()
            await callback.message.edit_text(text, reply_markup=kb)
            return

    except Exception as e:
        logger.error(f"处理回调时出错: {e}", exc_info=True)
        await callback.answer(f"❌ 出错: {str(e)[:50]}", show_alert=True)

