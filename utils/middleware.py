# utils/middleware.py
"""
中间件模块
包含黑名单检查等中间件
"""

import logging
from typing import Callable, Awaitable, Dict, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from config import ADMIN_IDS
from database import is_user_blacklisted

logger = logging.getLogger(__name__)


class BlacklistMiddleware(BaseMiddleware):
    """黑名单中间件：阻止被拉黑的用户使用机器人"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user

        if user:
            user_id = user.id
            # 管理员不受黑名单限制
            if user_id not in ADMIN_IDS and is_user_blacklisted(user_id):
                logger.warning(f"🚫 黑名单用户 {user_id} 尝试使用机器人，已拦截")
                if isinstance(event, Message):
                    await event.reply("🚫 您已被限制使用此机器人")
                elif isinstance(event, CallbackQuery):
                    await event.answer("🚫 您已被限制使用此机器人", show_alert=True)
                return

        return await handler(event, data)
