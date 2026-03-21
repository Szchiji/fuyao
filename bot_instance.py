# bot_instance.py
"""全局 Bot 实例 - 避免循环导入"""

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from config import TELEGRAM_BOT_TOKEN

# 创建全局 Bot 实例
bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)