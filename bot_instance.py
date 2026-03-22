# bot_instance.py
"""
全局 Bot 实例
避免循环导入问题
"""

import logging
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

# 创建全局 Bot 实例
bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

# 存储频道邀请链接的缓存
_channel_invite_cache = {}


async def get_channel_invite_link(channel_id: str) -> str:
    """
    为频道生成或获取邀请链接
    
    Args:
        channel_id: 频道ID，格式: -1001234567890
    
    Returns:
        邀请链接，格式: https://t.me/+xxxxx
    """
    global _channel_invite_cache
    
    # 检查缓存
    if channel_id in _channel_invite_cache:
        return _channel_invite_cache[channel_id]
    
    try:
        # 获取频道信息
        channel = await bot.get_chat(channel_id)
        
        # 如果是公开频道，使用用户名生成链接
        if channel.username:
            link = f"https://t.me/{channel.username}"
            _channel_invite_cache[channel_id] = link
            logger.info(f"✅ 获取公开频道链接: {channel.username}")
            return link
        
        # 如果是私密频道，创建邀请链接
        try:
            invite_link = await bot.create_chat_invite_link(
                channel_id,
                creates_join_request=False
            )
            link = invite_link.invite_link
            _channel_invite_cache[channel_id] = link
            logger.info(f"✅ 创建私密频道邀请链接成功")
            return link
        except Exception as e:
            logger.warning(f"⚠️ 创建邀请链接失败: {e}")
            return ""
    
    except Exception as e:
        logger.error(f"❌ 获取频道邀请链接失败: {e}")
        return ""