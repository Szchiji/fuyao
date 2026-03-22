# handlers/admin.py
"""
管理员命令处理模块（中文命令版本）
"""

import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from database import (
    add_required_channel,
    remove_required_channel,
    get_all_required_channels,
    set_start_message,
    get_global_stats,
    get_connection
)
from utils.decorators import admin_only
from bot_instance import bot

logger = logging.getLogger(__name__)

# ⭐ 创建路由器
router = Router()

# ⭐ 在加载时输出日志
logger.info("🚀 加载 admin_router...")

from config import ADMIN_IDS
logger.info(f"📝 admin_router 已创建，管理员数: {len(ADMIN_IDS)}")
logger.info(f"📝 管理员 ID 列表: {ADMIN_IDS}")


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

⚙️ 管理命令：
• /添加频道 [ID] - 添加频道
• /删除频道 [ID] - 删除频道
• /频道列表 - 查看频道
• /测试频道 - 测试频道
• /诊断频道 - 诊断频道
• /设置欢迎语 [内容] - 设置欢迎语
• /统计 - 详细统计
• /数据库 - 数据库信息"""
    
    await message.reply(menu_text)


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
        await message.reply(result["msg"])
        logger.info(f"✅ 管理员 {message.from_user.id} 添加频道 {channel_id}")
        
    except IndexError:
        await message.reply("""❌ 用法错误

正确用法:
/添加频道 -1001234567890""")


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
        await message.reply(result["msg"])
        logger.info(f"✅ 管理员 {message.from_user.id} 删除频道 {channel_id}")
        
    except IndexError:
        await message.reply("""❌ 用法错误

正确用法:
/删除频道 -1001234567890""")


# ==================== /频道列表 命令 ====================
@router.message(Command("频道列表"))
@admin_only
async def list_channels(message: Message):
    """列出所有频道"""
    channels = get_all_required_channels()
    
    if not channels:
        await message.reply("""❌ 未添加任何频道

使用 /添加频道 [ID] 添加频道""")
        return
    
    logger.info(f"✅ 管理员 {message.from_user.id} 查看频道列表")
    
    text = f"""📋 已添加频道 ({len(channels)} 个)

"""
    
    for i, ch_id in enumerate(channels, 1):
        try:
            ch = await bot.get_chat(ch_id)
            count = await bot.get_chat_member_count(ch_id)
            text += f"{i}. {ch.title}\n   📌 ID: {ch_id}\n   👥 成员: {count}\n   🗑️ 删除: /删除频道 {ch_id}\n\n"
        except Exception as e:
            logger.error(f"获取频道信息失败: {e}")
            text += f"{i}. (获取失败) ID: {ch_id}\n\n"
    
    await message.reply(text)


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
    
    text = f"""🧪 频道测试 ({len(channels)} 个)

"""
    
    for i, ch_id in enumerate(channels, 1):
        try:
            ch = await bot.get_chat(ch_id)
            mem = await bot.get_chat_member(ch_id, bot.id)
            is_admin = mem.status == "administrator"
            status_emoji = "✅" if is_admin else "❌"
            text += f"{i}. {status_emoji} {ch.title}\n   📌 ID: {ch_id}\n   🤖 状态: {mem.status}\n\n"
        except Exception as e:
            logger.error(f"测试频道失败: {e}")
            text += f"{i}. ❌ 错误: {str(e)[:30]}\n\n"
    
    await message.reply(text)


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
        await message.reply(f"✅ 欢迎语已更新:\n\n{welcome_msg}")
        logger.info(f"✅ 管理员 {message.from_user.id} 设置欢迎语")
        
    except IndexError:
        await message.reply("❌ 用法错误\n\n/设置欢迎语 [内容]")


# ==================== /统计 命令 ====================
@router.message(Command("统计"))
@admin_only
async def show_stats(message: Message):
    """显示统计"""
    stats = get_global_stats()
    
    avg = round(stats['total_eval']/max(1, stats['total_teacher']), 2)
    
    text = f"""📊 详细统计

📈 评价数据：
• 总评价数: {stats['total_eval']}
• 评价教师数: {stats['total_teacher']}
• 今日评价: {stats['today']}

📊 平均每个教师评价数: {avg}

🔄 运行状态: ✅ 正常"""
    
    await message.reply(text)
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
        
        await message.reply(text)
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
• /管理 - 显示管理后台
• /统计 - 查看统计数据
• /数据库 - 查看数据库信息

🔐 频道管理：
• /添加频道 [ID] - 添加频道要求
• /删除频道 [ID] - 删除频道要求  
• /频道列表 - 查看所有频道
• /测试频道 - 测试所有频道
• /诊断频道 - 深度诊断频道

✏️ 内容管理：
• /设置欢迎语 [欢迎语] - 设置欢迎语

❓ 其他：
• /管理帮助 - 显示此帮助

💡 使用示例:

1. 添加频道:
   /添加频道 -1001811864163

2. 查看所有频道:
   /频道列表

3. 测试频道:
   /测试频道

4. 删除频道:
   /删除频道 -1001811864163

5. 设置欢迎语:
   /设置欢迎语 欢迎使用狼评机器人！"""
    
    await message.reply(help_text)
    logger.info(f"✅ 管理员 {message.from_user.id} 查看管理帮助")