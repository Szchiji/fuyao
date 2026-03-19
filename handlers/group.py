# handlers/group.py
from aiogram import Router, F
from aiogram.types import Message
from database import get_teacher_detail
from utils.helpers import send_teacher_detail   # 后续会定义

router = Router()

@router.message(F.text.regexp(r'@([a-zA-Z0-9_-]+)'))
async def handle_at_query(message: Message):
    teacher = message.text.split('@', 1)[1].strip()
    await send_teacher_detail(message, teacher)