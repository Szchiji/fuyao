# handlers/admin.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from database import set_required_channel, set_start_message, get_global_stats
from utils.decorators import admin_only

router = Router()

@router.message(Command("admin"))
@admin_only
async def admin_menu(message: Message):
    """管理员菜单"""
    stats = get_global_stats()
    menu_text = f"""🛠️ 管理员后台

📊 当前统计：
• 总评价数: {stats['total_eval']}
• 评价教师数: {stats['total_teacher']}
• 今日评价: {stats['today']}

⚙️ 管理命令：
• /setchannel 频道ID - 设置频道要求
• /setstart 欢迎语 - 设置欢迎语
• /stats - 查看详细统计"""
    
    await message.reply(menu_text)

@router.message(Command("setchannel"))
@admin_only
async def set_channel(message: Message):
    """设置频道"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            raise IndexError
        
        channel_id = parts[1].strip()
        set_required_channel(channel_id)
        await message.reply(f"✅ 频道已设置为: {channel_id}")
    except (IndexError, ValueError):
        await message.reply("❌ 用法: /setchannel -1001234567890")

@router.message(Command("setstart"))
@admin_only
async def set_start_msg(message: Message):
    """设置欢迎语"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            raise IndexError
        
        start_msg = parts[1].strip()
        set_start_message(start_msg)
        await message.reply(f"✅ 欢迎语已更新:\n{start_msg}")
    except (IndexError, ValueError):
        await message.reply("❌ 用法: /setstart 欢迎使用狼评机器人")

@router.message(Command("stats"))
@admin_only
async def show_stats(message: Message):
    """显示统计信息"""
    stats = get_global_stats()
    stats_text = f"""📊 机器人统计

总体：
• 总评价数: {stats['total_eval']}
• 评价教师数: {stats['total_teacher']}
• 今日评价: {stats['today']}

运行状态: ✅ 正常"""
    
    await message.reply(stats_text)