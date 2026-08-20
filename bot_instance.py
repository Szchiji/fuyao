# bot_instance.py
"""
全局 Bot 实例
避免循环导入问题
"""

import logging
from collections import OrderedDict
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

# 创建全局 Bot 实例
bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

# 存储频道邀请链接的缓存（LRU，最多缓存 256 个条目，避免无限增长）
_channel_invite_cache: OrderedDict = OrderedDict()
_CACHE_MAX_SIZE = 256
_bot_username: str = ""


def _cache_put(key: str, value: str) -> None:
    """将条目存入 LRU 缓存，若缓存已满则淘汰最久未使用的条目"""
    if key in _channel_invite_cache:
        _channel_invite_cache.move_to_end(key)
    _channel_invite_cache[key] = value
    if len(_channel_invite_cache) > _CACHE_MAX_SIZE:
        _channel_invite_cache.popitem(last=False)


async def get_channel_invite_link(channel_id: str) -> str:
    """
    为频道生成或获取邀请链接
    
    Args:
        channel_id: 频道ID，格式: -1001234567890
    
    Returns:
        邀请链接，格式: https://t.me/+xxxxx
    """
    # 检查缓存（命中时移到末尾表示最近使用）
    if channel_id in _channel_invite_cache:
        _channel_invite_cache.move_to_end(channel_id)
        return _channel_invite_cache[channel_id]
    
    try:
        # 获取频道信息
        channel = await bot.get_chat(channel_id)
        
        # 如果是公开频道，使用用户名生成链接
        if channel.username:
            link = f"https://t.me/{channel.username}"
            _cache_put(channel_id, link)
            logger.info(f"✅ 获取公开频道链接: {channel.username}")
            return link
        
        # 如果是私密频道，创建邀请链接
        try:
            invite_link = await bot.create_chat_invite_link(
                channel_id,
                creates_join_request=False
            )
            link = invite_link.invite_link
            _cache_put(channel_id, link)
            logger.info(f"✅ 创建私密频道邀请链接成功")
            return link
        except Exception as e:
            logger.warning(f"⚠️ 创建邀请链接失败: {e}")
            return ""
    
    except Exception as e:
        logger.error(f"❌ 获取频道邀请链接失败: {e}")
        return ""


async def get_bot_username() -> str:
    """获取机器人用户名，并尽量复用缓存"""
    global _bot_username
    if _bot_username:
        return _bot_username

    try:
        me = await bot.get_me()
        _bot_username = me.username or ""
        return _bot_username
    except Exception as e:
        logger.error(f"❌ 获取机器人用户名失败: {e}")
        return ""


async def get_bot_start_url(payload: str = "") -> str:
    """生成机器人私聊 deep link"""
    username = await get_bot_username()
    if not username:
        return ""
    if payload:
        return f"https://t.me/{username}?start={payload}"
    return f"https://t.me/{username}"