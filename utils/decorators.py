# utils/decorators.py
"""
装饰器模块
包含权限检查等
"""

import logging
from functools import wraps
from aiogram.types import Message

logger = logging.getLogger(__name__)


def admin_only(func):
    """管理员权限检查装饰器"""
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        user_id = message.from_user.id
        username = message.from_user.username or "无"
        
        # ⭐ 动态导入 ADMIN_IDS，避免循环导入
        from config import ADMIN_IDS
        
        logger.info(f"🔍 用户 {user_id}(@{username}) 尝试执行命令: {message.text}")
        logger.debug(f"📝 当前 ADMIN_IDS 值: {ADMIN_IDS}")
        logger.debug(f"🔍 用户 ID {user_id} 在 ADMIN_IDS 中吗? {user_id in ADMIN_IDS}")
        
        if user_id not in ADMIN_IDS:
            logger.warning(f"❌ 用户 {user_id} 无管理员权限")
            await message.reply(
                f"""❌ 您没有权限执行此命令

���� 您的用户ID: <code>{user_id}</code>

如需成为管理员，请：
1️⃣ 复制上方用户ID
2️⃣ 进入 Railway → fuyao → Variables
3️⃣ 设置 ADMIN_IDS={user_id}
   (多个用逗号分隔: 123,456,789)
4️⃣ 保存并点击 Redeploy

当前管理员数: {len(ADMIN_IDS)}"""
            )
            return
        
        logger.info(f"✅ 用户 {user_id} 有管理员权限，执行命令...")
        return await func(message, *args, **kwargs)
    
    return wrapper