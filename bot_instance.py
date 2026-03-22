# bot_instance.py
"""全局 Bot 实例 - 用于避免循环导入"""

import asyncio
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from config import TELEGRAM_BOT_TOKEN

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
            return link
        
        # 如果是私密频道，创建邀请链接
        try:
            invite_link = await bot.create_chat_invite_link(
                channel_id,
                creates_join_request=False  # 直接加入，不需要请求
            )
            link = invite_link.invite_link
            _channel_invite_cache[channel_id] = link
            return link
        except Exception as e:
            print(f"创建邀请链接失败: {e}")
            # 如果创建失败，尝试获取现有的邀请链接
            try:
                invite_links = await bot.get_chat_administrators(channel_id)
                # 这个方法不适用，尝试另一个方法
                raise e
            except:
                return ""
    
    except Exception as e:
        print(f"获取频道邀请链接失败: {e}")
        return ""


async def update_channel_link(channel_id: str) -> str:
    """
    更新频道邀请链接缓存
    
    Args:
        channel_id: 频道ID
    
    Returns:
        邀请链接
    """
    global _channel_invite_cache
    
    # 清除旧缓存
    if channel_id in _channel_invite_cache:
        del _channel_invite_cache[channel_id]
    
    # 获取新的邀请链接
    return await get_channel_invite_link(channel_id)