# states.py
"""
有限状态机 (FSM) 定义
"""

from aiogram.fsm.state import State, StatesGroup


class RatingStates(StatesGroup):
    """评价流程状态机"""
    waiting_reason = State()  # 等待用户填写评价理由


class AdminStates(StatesGroup):
    """管理员操作状态机"""
    waiting_channel_id = State()   # 等待管理员输入频道 ID
    waiting_teacher_name = State() # 等待管理员输入教师名称
    waiting_welcome_msg = State()  # 等待管理员输入欢迎语