# states.py
from aiogram.fsm.state import State, StatesGroup

class RatingStates(StatesGroup):
    """评价状态"""
    waiting_reason = State()  # 等待评价理由
    waiting_channel_id = State()  # 等待频道ID
    waiting_start_message = State()  # 等待开始消息