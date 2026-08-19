# utils/decorators.py
"""
装饰器模块
包含权限检查等
"""

import logging
from functools import wraps
from aiogram.types import Message

logger = logging.getLogger(__name__)


def _get_admin_ids():
    from config import ADMIN_IDS
    return ADMIN_IDS


def _is_super_admin(user_id: int) -> bool:
    return user_id in _get_admin_ids()


def _is_any_admin(user_id: int) -> bool:
    """超级管理员或普通管理员均返回 True"""
    if _is_super_admin(user_id):
        return True
    try:
        from database import is_sub_admin
        return is_sub_admin(user_id)
    except Exception:
        return False


def admin_only(func):
    """超级管理员权限检查装饰器（仅 ADMIN_IDS 中的用户可用）"""
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        user_id = message.from_user.id
        username = message.from_user.username or "无"
        admin_ids = _get_admin_ids()

        logger.info(f"🔍 用户 {user_id}(@{username}) 尝试执行命令: {message.text}")
        logger.debug(f"📝 当前 ADMIN_IDS 值: {admin_ids}")
        logger.debug(f"🔍 用户 ID {user_id} 在 ADMIN_IDS 中吗? {user_id in admin_ids}")

        if user_id not in admin_ids:
            logger.warning(f"❌ 用户 {user_id} 无超级管理员权限")
            await message.reply(
                f"❌ 您没有权限执行此命令\n\n"
                f"👤 您的用户ID: <code>{user_id}</code>\n\n"
                f"如需成为管理员，请：\n"
                f"1️⃣ 复制上方用户ID\n"
                f"2️⃣ 进入 Railway → fuyao → Variables\n"
                f"3️⃣ 设置 ADMIN_IDS={user_id}\n"
                f"   (多个用逗号分隔: 123,456,789)\n"
                f"4️⃣ 保存并点击 Redeploy\n\n"
                f"当前超级管理员数: {len(admin_ids)}"
            )
            return

        logger.info(f"✅ 用户 {user_id} 有超级管理员权限，执行命令...")
        return await func(message, *args, **kwargs)

    return wrapper


def any_admin_only(func):
    """普通管理员或超级管理员均可使用的权限装饰器"""
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        user_id = message.from_user.id
        username = message.from_user.username or "无"

        logger.info(f"🔍 用户 {user_id}(@{username}) 尝试执行命令: {message.text}")

        if not _is_any_admin(user_id):
            logger.warning(f"❌ 用户 {user_id} 无管理员权限")
            await message.reply(
                f"❌ 您没有权限执行此命令\n\n"
                f"👤 您的用户ID: <code>{user_id}</code>\n\n"
                f"请联系超级管理员授权。"
            )
            return

        logger.info(f"✅ 用户 {user_id} 有管理员权限，执行命令...")
        return await func(message, *args, **kwargs)

    return wrapper
