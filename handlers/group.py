# handlers/group.py
from aiogram import Router, F
from aiogram.types import Message
from database import get_teacher_detail
from utils.helpers import send_teacher_detail

router = Router()

@router.message(F.text.regexp(r'@([a-zA-Z0-9_]{5,32})'))
async def handle_at_query(message: Message):
    """处理 @username 查询"""
    try:
        # 提取用户名
        parts = message.text.split()
        for part in parts:
            if part.startswith('@'):
                teacher = part[1:].strip()
                await send_teacher_detail(message, teacher)
                return
    except Exception as e:
        print(f"处理查询时出错: {e}")