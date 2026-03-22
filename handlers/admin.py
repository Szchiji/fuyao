# handlers/admin.py
"""
管理员命令处理模块（中文命令版本）
"""

import logging
from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import (
    add_required_channel,
    remove_required_channel,
    get_all_required_channels,
    set_start_message,
    get_global_stats,
    get_connection,
    get_teacher_stats,
    delete_teacher_data_from_db,
    delete_user_rating,
    get_teacher_all_ratings,
    delete_rating_by_id
)
from utils.decorators import admin_only
from bot_instance import bot
from states import AdminStates

logger = logging.getLogger(__name__)

# ⭐ 创建路由器
router = Router()

# ⭐ 在加载时输出日志
logger.info("🚀 加载 admin_router...")

from config import ADMIN_IDS
logger.info(f"📝 admin_router 已创建，管理员数: {len(ADMIN_IDS)}")
logger.info(f"📝 管理员 ID 列表: {ADMIN_IDS}")


def build_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """构建管理员菜单内联键盘"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 查看统计", callback_data="admin_stats"),
            InlineKeyboardButton(text="💾 数据库信息", callback_data="admin_db")
        ],
        [
            InlineKeyboardButton(text="📋 频道列表", callback_data="admin_channels"),
            InlineKeyboardButton(text="🧪 测试频道", callback_data="admin_test_channels")
        ],
        [
            InlineKeyboardButton(text="🔧 诊断频道", callback_data="admin_diagnose"),
            InlineKeyboardButton(text="➕ 添加频道", callback_data="admin_add_channel")
        ],
        [
            InlineKeyboardButton(text="✏️ 设置欢迎语", callback_data="admin_set_welcome"),
            InlineKeyboardButton(text="👨‍🏫 管理教师", callback_data="admin_manage_teacher")
        ],
        [
            InlineKeyboardButton(text="📖 管理帮助", callback_data="admin_help")
        ]
    ])


# ==================== /管理 命令 ====================
@router.message(Command("管理"))
@admin_only
async def admin_menu(message: Message):
    """管理员菜单"""
    logger.info(f"✅ 用户 {message.from_user.id} 访问管理后台")

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

    await message.reply(menu_text, reply_markup=build_admin_menu_keyboard())


# ==================== /添加频道 命令 ====================
@router.message(Command("添加频道"))
@admin_only
async def add_channel(message: Message):
    """添加频道"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            raise IndexError

        channel_id = parts[1].strip()

        if not channel_id.startswith('-100'):
            await message.reply("""❌ 频道ID格式错误

正确格式:
/添加频道 -1001234567890""")
            return

        result = add_required_channel(channel_id)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
        ])
        await message.reply(result["msg"], reply_markup=kb)
        logger.info(f"✅ 管理员 {message.from_user.id} 添加频道 {channel_id}")

    except IndexError:
        await message.reply("""❌ 用法错误

正确用法:
/添加频道 -1001234567890

💡 也可以点击 /管理 → ➕ 添加频道 按钮""")


# ==================== /删除频道 命令 ====================
@router.message(Command("删除频道"))
@admin_only
async def remove_channel(message: Message):
    """删除频道"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            raise IndexError

        channel_id = parts[1].strip()
        result = remove_required_channel(channel_id)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
        ])
        await message.reply(result["msg"], reply_markup=kb)
        logger.info(f"✅ 管理员 {message.from_user.id} 删除频道 {channel_id}")

    except IndexError:
        await message.reply("""❌ 用法错误

正确用法:
/删除频道 -1001234567890

💡 也可以点击 /管理 → 📋 频道列表，然后点击删除按钮""")


# ==================== /频道列表 命令 ====================
@router.message(Command("频道列表"))
@admin_only
async def list_channels(message: Message):
    """列出所有频道"""
    channels = get_all_required_channels()

    if not channels:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ 添加频道", callback_data="admin_add_channel")],
            [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
        ])
        await message.reply("❌ 未添加任何频道", reply_markup=kb)
        return

    logger.info(f"✅ 管理员 {message.from_user.id} 查看频道列表")

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

    await message.reply(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))


# ==================== /测试频道 命令 ====================
@router.message(Command("测试频道"))
@admin_only
async def test_channel(message: Message):
    """测试所有频道"""
    channels = get_all_required_channels()

    if not channels:
        await message.reply("❌ 未添加任何频道")
        return

    logger.info(f"✅ 管理员 {message.from_user.id} 测试频道")

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
    await message.reply(text, reply_markup=kb)


# ==================== /诊断频道 命令 ====================
@router.message(Command("诊断频道"))
@admin_only
async def debug_channel(message: Message):
    """诊断频道"""
    channels = get_all_required_channels()

    if not channels:
        await message.reply("❌ 未添加任何频道")
        return

    logger.info(f"开始诊断 {len(channels)} 个频道")

    msg = await message.reply(f"🔧 诊断中... ({len(channels)} 个频道)")

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

        await bot.edit_message_text(text, message.chat.id, msg.message_id)
    except Exception as e:
        logger.error(f"诊断失败: {e}")
        await bot.edit_message_text(f"❌ 诊断失败: {e}", message.chat.id, msg.message_id)


# ==================== /设置欢迎语 命令 ====================
@router.message(Command("设置欢迎语"))
@admin_only
async def set_welcome(message: Message):
    """设置欢迎语"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            raise IndexError

        welcome_msg = parts[1]
        set_start_message(welcome_msg)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="�� 返回管理菜单", callback_data="admin_menu")]
        ])
        await message.reply(f"✅ 欢迎语已更新:\n\n{welcome_msg}", reply_markup=kb)
        logger.info(f"✅ 管理员 {message.from_user.id} 设置欢迎语")

    except IndexError:
        await message.reply("❌ 用法错误\n\n/设置欢迎语 [内容]\n\n💡 也可以点击 /管理 → ✏️ 设置欢迎语 按钮")


# ==================== /统计 命令 ====================
@router.message(Command("统计"))
@admin_only
async def show_stats(message: Message):
    """显示统计"""
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
    await message.reply(text, reply_markup=kb)
    logger.info(f"✅ 管理员 {message.from_user.id} 查看统计")


# ==================== /数据库 命令 ====================
@router.message(Command("数据库"))
@admin_only
async def show_db(message: Message):
    """显示数据库信息"""
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
        await message.reply(text, reply_markup=kb)
        logger.info(f"✅ 管理员 {message.from_user.id} 查看数据库")
    except Exception as e:
        logger.error(f"获取数据库信息失败: {e}")
        await message.reply(f"❌ 错误: {e}")


# ==================== /管理帮助 命令 ====================
@router.message(Command("管理帮助"))
@admin_only
async def admin_help(message: Message):
    """管理员帮助"""
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
• /取消 - 取消操作

💡 交互式操作（推荐）：
点击 /管理 进入后台，所有操作均可通过按钮完成：
• 添加/删除/测试频道
• 设置欢迎语（直接发送文本）
• 管理教师数据（直接发送教师名）

❓ 其他：
• /管理帮助 - 显示此帮助"""

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠️ 打开管理菜单", callback_data="admin_menu")]
    ])
    await message.reply(help_text, reply_markup=kb)
    logger.info(f"✅ 管理员 {message.from_user.id} 查看管理帮助")


# ==================== /管理教师 命令 ====================
@router.message(Command("管理教师"))
@admin_only
async def manage_teacher(message: Message):
    """管理教师数据"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            raise IndexError

        teacher_name = parts[1].strip()

        # 获取教师统计
        stats = get_teacher_stats(teacher_name)

        if stats["total"] == 0:
            await message.reply(f"❌ 教师 @{teacher_name} 没有任何评价\n\n无法进行管理操作")
            return

        # 显示管理界面（含按钮）
        recommend_percentage = int((stats["recommend"] / stats["total"]) * 100) if stats["total"] > 0 else 0

        manage_text = f"""👨‍🏫 教师数据管理

教师: @{teacher_name}

📊 统计信息:
• 总评价数: {stats['total']}
• 👍 推荐: {stats['recommend']} 人 ({recommend_percentage}%)
• 👎 不推荐: {stats['not_recommend']} 人 ({100-recommend_percentage}%)

⚠️ 注意: 删除操作不可恢复"""

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 查看所有评价", callback_data=f"view_teacher_ratings|{teacher_name}")],
            [InlineKeyboardButton(text="🗑️ 删除该教师全部数据", callback_data=f"delete_all_teacher|{teacher_name}")],
            [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
        ])

        await message.reply(manage_text, reply_markup=kb)
        logger.info(f"✅ 管理员 {message.from_user.id} 访问教师管理: @{teacher_name}")

    except IndexError:
        await message.reply("""❌ 用法错误

正确用法:
/管理教师 李老师

💡 也可以点击 /管理 → 👨‍🏫 管理教师 按钮""")


# ==================== /查看评价 命令 ====================
@router.message(Command("查看评价"))
@admin_only
async def view_teacher_ratings(message: Message):
    """查看某个教师的所有评价 - 支持点击跳转私聊"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            raise IndexError

        teacher_name = parts[1].strip()

        ratings = get_teacher_all_ratings(teacher_name)

        if not ratings:
            await message.reply(f"❌ 教师 @{teacher_name} 没有任何评价")
            return

        text, kb = build_ratings_view(teacher_name, ratings)
        await message.reply(text, reply_markup=kb)
        logger.info(f"✅ 管理员 {message.from_user.id} 查看教师 @{teacher_name} 的评价")

    except IndexError:
        await message.reply("""❌ 用法错误

正确用法:
/查看评价 李老师""")


def build_ratings_view(teacher_name: str, ratings: list) -> tuple:
    """构建教师评价列表视图（返回文本和键盘）"""
    text = f"📝 教师 @{teacher_name} 的所有评价 ({len(ratings)} 条)\n\n"
    kb_buttons = []

    for i, rating in enumerate(ratings[:10], 1):
        rating_id = rating[0]
        user_id = rating[1]
        recommend = rating[2]
        reason = rating[3]
        time_val = rating[4]

        emoji = "👍" if recommend else "👎"
        text += f"{i}. {emoji} [#{rating_id}] 用户: <code>{user_id}</code>\n"
        text += f"   {reason[:50]}{'...' if len(reason) > 50 else ''}\n"
        text += f"   🕐 {time_val}\n\n"

        kb_buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} #{rating_id}",
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
    kb_buttons.append([
        InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")
    ])

    return text, InlineKeyboardMarkup(inline_keyboard=kb_buttons)


# ==================== /删除教师数据 命令 ====================
@router.message(Command("删除教师数据"))
@admin_only
async def delete_teacher_data(message: Message):
    """删除某个教师的所有评价数据"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            raise IndexError

        teacher_name = parts[1].strip()

        if not teacher_name:
            await message.reply("❌ 用法错误\n\n/删除教师数据 李老师")
            return

        stats = get_teacher_stats(teacher_name)

        if stats["total"] == 0:
            await message.reply(f"❌ 教师 @{teacher_name} 没有任何评价数据\n\n无需删除")
            return

        confirm_text = f"""⚠️ 确认删除教师数据

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
            [InlineKeyboardButton(text="❌ 取消", callback_data="cancel_delete")]
        ])

        await message.reply(confirm_text, reply_markup=kb)
        logger.info(f"⚠️ 管理员 {message.from_user.id} 请求删除教师 @{teacher_name} 的数据")

    except IndexError:
        await message.reply("❌ 用法错误\n\n/删除教师数据 李老师")


# ==================== /确认删除 命令（保留向后兼容）====================
@router.message(Command("确认删除"))
@admin_only
async def confirm_delete_teacher(message: Message):
    """确认删除教师数据"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("❌ 请指定要删除的教师名称\n\n/确认删除 李老师")
            return

        teacher_name = parts[1].strip()

        result = delete_teacher_data_from_db(teacher_name)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
        ])
        await message.reply(result["msg"], reply_markup=kb)

        if result["success"]:
            logger.warning(f"🗑️ 管理员 {message.from_user.id} 删除了教师 @{teacher_name} 的所有数据")
        else:
            logger.error(f"❌ 删除教师数据失败: {result['msg']}")

    except Exception as e:
        logger.error(f"删除教师数据出错: {e}")
        await message.reply(f"❌ 删除失败: {str(e)}")


# ==================== /删除评价 命令 ====================
@router.message(Command("删除评价"))
@admin_only
async def delete_single_rating(message: Message):
    """删除某条评价"""
    try:
        parts = message.text.split()
        if len(parts) < 3:
            raise IndexError

        teacher_name = parts[1]
        rating_id = parts[2]

        result = delete_rating_by_id(rating_id, teacher_name)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
        ])
        await message.reply(result["msg"], reply_markup=kb)

        if result["success"]:
            logger.warning(f"🗑️ 管理员 {message.from_user.id} 删除了一条评价")

    except (IndexError, ValueError):
        await message.reply("❌ 用法错误\n\n/删除评价 李老师 1")


# ==================== /取消 命令 ====================
@router.message(Command("取消"))
@admin_only
async def cancel_operation(message: Message, state: FSMContext):
    """取消操作"""
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
    ])
    await message.reply("✅ 操作已取消", reply_markup=kb)
    logger.info(f"✅ 管理员 {message.from_user.id} 取消了操作")


# ==================== FSM: 等待频道 ID 输入 ====================
@router.message(StateFilter(AdminStates.waiting_channel_id))
async def process_channel_id_input(message: Message, state: FSMContext):
    """处理管理员输入的频道 ID"""
    from config import ADMIN_IDS
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    channel_id = message.text.strip() if message.text else ""
    await state.clear()

    if not channel_id:
        await message.reply("❌ 未收到有效输入，操作已取消")
        return

    if not channel_id.startswith('-100'):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 重新输入", callback_data="admin_add_channel")],
            [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
        ])
        await message.reply("❌ 频道ID格式错误\n\n正确格式: -1001234567890", reply_markup=kb)
        return

    result = add_required_channel(channel_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 查看频道列表", callback_data="admin_channels")],
        [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
    ])
    await message.reply(result["msg"], reply_markup=kb)
    logger.info(f"✅ 管理员 {message.from_user.id} 通过交互式方式添加频道 {channel_id}")


# ==================== FSM: 等待欢迎语输入 ====================
@router.message(StateFilter(AdminStates.waiting_welcome_msg))
async def process_welcome_msg_input(message: Message, state: FSMContext):
    """处理管理员输入的欢迎语"""
    from config import ADMIN_IDS
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    welcome_msg = message.text.strip() if message.text else ""
    await state.clear()

    if not welcome_msg:
        await message.reply("❌ 未收到有效内容，操作已取消")
        return

    set_start_message(welcome_msg)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
    ])
    await message.reply(f"✅ 欢迎语已更新:\n\n{welcome_msg}", reply_markup=kb)
    logger.info(f"✅ 管理员 {message.from_user.id} 通过交互式方式设置欢迎语")


# ==================== FSM: 等待教师名称输入 ====================
@router.message(StateFilter(AdminStates.waiting_teacher_name))
async def process_teacher_name_input(message: Message, state: FSMContext):
    """处理管理员输入的教师名称"""
    from config import ADMIN_IDS
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    teacher_name = message.text.strip() if message.text else ""
    # 去掉可能携带的 @ 前缀
    teacher_name = teacher_name.lstrip("@")
    await state.clear()

    if not teacher_name:
        await message.reply("❌ 未收到有效内容，操作已取消")
        return

    stats = get_teacher_stats(teacher_name)

    if stats["total"] == 0:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 重新输入", callback_data="admin_manage_teacher")],
            [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
        ])
        await message.reply(f"❌ 教师 @{teacher_name} 没有任何评价", reply_markup=kb)
        return

    recommend_percentage = int((stats["recommend"] / stats["total"]) * 100) if stats["total"] > 0 else 0

    manage_text = f"""👨‍🏫 教师数据管理

教师: @{teacher_name}

📊 统计信息:
• 总评价数: {stats['total']}
• 👍 推荐: {stats['recommend']} 人 ({recommend_percentage}%)
• 👎 不推荐: {stats['not_recommend']} 人 ({100-recommend_percentage}%)

⚠️ 注意: 删除操作不可恢复"""

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 查看所有评价", callback_data=f"view_teacher_ratings|{teacher_name}")],
        [InlineKeyboardButton(text="🗑️ 删除该教师全部数据", callback_data=f"delete_all_teacher|{teacher_name}")],
        [InlineKeyboardButton(text="🔙 返回管理菜单", callback_data="admin_menu")]
    ])

    await message.reply(manage_text, reply_markup=kb)
    logger.info(f"✅ 管理员 {message.from_user.id} 通过交互式方式管理教师 @{teacher_name}")
