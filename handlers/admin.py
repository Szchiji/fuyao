# handlers/admin.py
"""
管理员命令处理模块
包含: /admin, /setchannel, /setstart, /stats, /testchannel, /removechannel
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from database import (
    set_required_channel, 
    set_start_message, 
    get_global_stats,
    get_required_channel,
    get_connection
)
from utils.decorators import admin_only
from bot_instance import bot

router = Router()

@router.message(Command("admin"))
@admin_only
async def admin_menu(message: Message):
    """管理员菜单 - 显示后台面板"""
    stats = get_global_stats()
    current_channel = get_required_channel()
    
    channel_status = f"✅ {current_channel}" if current_channel else "❌ 未设置"
    
    # 使用 | 代替 <> 符号，避免 HTML 解析错误
    menu_text = f"""🛠️ 管理员后台

📊 当前统计：
• 总评价数: {stats['total_eval']}
• 评价教师数: {stats['total_teacher']}
• 今日评价: {stats['today']}

🔐 频道管理：
• 频道状态: {channel_status}

⚙️ 管理命令：
• /setchannel [频道ID] - 设置频道要求
• /removechannel - 移除频道要求
• /setstart [欢迎语] - 设置欢迎语
• /stats - 查看详细统计
• /testchannel - 测试频道连接
• /dbinfo - 查看数据库信息"""
    
    await message.reply(menu_text)


@router.message(Command("setchannel"))
@admin_only
async def set_channel(message: Message):
    """设置频道要求"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            raise IndexError
        
        channel_id = parts[1].strip()
        
        # 验证格式
        if not channel_id.startswith('-100'):
            await message.reply("""❌ 频道ID格式错误

正确格式示例:
/setchannel -1001234567890

如何获取频道ID:
1️⃣ 在频道中转发消息到 @userinfobot
2️⃣ 获取频道ID，前面加 -100
3️⃣ 例如: /setchannel -1001811864163""")
            return
        
        set_required_channel(channel_id)
        await message.reply(f"""✅ 频道已设置

频道ID: {channel_id}

现在用户必须订阅此频道才能使用机器人
要验证设置，请使用: /testchannel""")
    
    except (IndexError, ValueError):
        await message.reply("""❌ 用法错误

正确用法:
/setchannel -1001234567890

说明:
• 频道ID必须以 -100 开头
• 机器人必须是频道管理员
• 使用 /testchannel 验证设置""")


@router.message(Command("removechannel"))
@admin_only
async def remove_channel(message: Message):
    """移除频道要求"""
    current_channel = get_required_channel()
    
    if not current_channel:
        await message.reply("❌ 当前未设置频道要求")
        return
    
    set_required_channel("")  # 清空频道
    await message.reply("""✅ 频道要求已移除

现在所有用户都可以使用机器人，无需订阅频道""")


@router.message(Command("setstart"))
@admin_only
async def set_start_msg(message: Message):
    """设置欢迎语"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            raise IndexError
        
        start_msg = parts[1].strip()
        
        if len(start_msg) < 5:
            await message.reply("❌ 欢迎语太短，至少需要5个字")
            return
        
        set_start_message(start_msg)
        await message.reply(f"""✅ 欢迎语已更新

新欢迎语:
{start_msg}

用户发送 /start 时会看到此消息""")
    
    except (IndexError, ValueError):
        await message.reply("""❌ 用法错误

正确用法:
/setstart 欢迎使用狼评机器人！

说明:
• 可以包含中文、emoji、换行等
• 长度至少5个字""")


@router.message(Command("stats"))
@admin_only
async def show_stats(message: Message):
    """显示详细统计信息"""
    stats = get_global_stats()
    
    stats_text = f"""📊 机器人详细统计

📈 评价统计：
• 总评价数: {stats['total_eval']}
• 评价教师数: {stats['total_teacher']}
• 今日评价数: {stats['today']}

平均每个教师评价数: {round(stats['total_eval'] / max(1, stats['total_teacher']), 2)}

🔄 运行状态: ✅ 正常运行"""
    
    await message.reply(stats_text)


@router.message(Command("testchannel"))
@admin_only
async def test_channel(message: Message):
    """测试频道连接 - 诊断频道问题"""
    channel_id = get_required_channel()
    
    if not channel_id:
        await message.reply("""❌ 未设置频道

请先设置频道:
/setchannel -1001234567890""")
        return
    
    try:
        # 尝试获取频道信息
        channel = await bot.get_chat(channel_id)
        
        # 获取频道成员数
        try:
            member_count = await bot.get_chat_member_count(channel_id)
        except:
            member_count = "未知"
        
        # 尝试检查机器人自己的权限
        try:
            bot_member = await bot.get_chat_member(channel_id, bot.id)
            bot_status = bot_member.status
            is_admin = bot_member.is_member
        except:
            bot_status = "未知"
            is_admin = False
        
        status_text = f"""✅ 频道已连接

📋 频道信息：
• 频道名: {channel.title}
• 频道ID: {channel.id}
• 频道类型: {channel.type}
• 成员数: {member_count}

🤖 机器人状态：
• 状态: {bot_status}
• 是否为管理���: {"✅ 是" if is_admin else "❌ 否"}

✅ 频道验证功能应该正常工作
如果仍有问题，请检查:
1. 机器人是否在频道管理员列表中
2. 机器人是否有访问成员信息的权限"""
        
        await message.reply(status_text)
    
    except Exception as e:
        error_msg = str(e)
        
        if "chat not found" in error_msg.lower():
            await message.reply(f"""❌ 频道未找到

频道ID: {channel_id}

可能的原因:
1. 频道ID错误
2. 频道已被删除
3. 机器人未被邀请到频道

解决方案:
1. 确认频道ID: /setchannel -1001811864163
2. 确认机器人在频道中
3. 赋予机器人管理员权限""")
        
        elif "not enough rights" in error_msg.lower() or "forbidden" in error_msg.lower():
            await message.reply(f"""❌ 机器人权限不足

频道ID: {channel_id}

机器人需要以下权限:
• 删除消息
• 限制成员
• 邀请用户
• 更改群组信息

解决方案:
1. 进入频道设置 → 管理员
2. 选择 @tan1tan_bot
3. 赋予上述权限""")
        
        else:
            await message.reply(f"""❌ 测试失败

频道ID: {channel_id}
错误: {error_msg}

请检查:
1. 机器人是否是频道管理员
2. 频道ID是否正确
3. 频道是否存在""")


@router.message(Command("dbinfo"))
@admin_only
async def show_db_info(message: Message):
    """显示数据库信息"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 获取评价表信息
        cursor.execute("SELECT COUNT(*) FROM recs")
        total_recs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT teacher) FROM recs")
        total_teachers = cursor.fetchone()[0]
        
        # 获取推荐统计
        cursor.execute("SELECT COUNT(*) FROM recs WHERE recommend = 1")
        recommend_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM recs WHERE recommend = 0")
        not_recommend_count = cursor.fetchone()[0]
        
        # 获取最近的评价
        cursor.execute("""
            SELECT teacher, recommend, reason, time 
            FROM recs 
            ORDER BY time DESC 
            LIMIT 1
        """)
        latest = cursor.fetchone()
        
        conn.close()
        
        latest_text = ""
        if latest:
            teacher, recommend, reason, time = latest
            latest_text = f"\n\n📝 最后一条评价:\n教师: {teacher}\n态度: {'👍 推荐' if recommend else '👎 不推荐'}\n理由: {reason[:50]}...\n时间: {time}"
        
        db_info = f"""📊 数据库信息

📈 统计数据：
• 总评价数: {total_recs}
• 评价教师数: {total_teachers}
• 推荐数: {recommend_count}
• 不推荐数: {not_recommend_count}

💾 数据库状态: ✅ 正常
数据库位置: /data/wolf_recs.db
{latest_text}"""
        
        await message.reply(db_info)
    
    except Exception as e:
        await message.reply(f"❌ 获取数据库信息失败: {str(e)}")


@router.message(Command("help_admin"))
@admin_only
async def admin_help(message: Message):
    """管理员帮助"""
    help_text = """📖 管理员帮助

🎛️ 主要命令：
/admin - 显示管理后台
/stats - 查看统计数据
/dbinfo - 查看数据库信息

🔐 频道管理：
/setchannel [ID] - 设置频道要求
/removechannel - 移除频道要求  
/testchannel - 测试频道连接

✏️ 内容管理：
/setstart [欢迎语] - 设置欢迎语

❓ 其他：
/help_admin - 显示此帮助"""
    
    await message.reply(help_text)