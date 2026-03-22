# states.py
"""
有限状态机 (FSM) 定义
"""

from aiogram.fsm.state import State, StatesGroup


class RatingStates(StatesGroup):
    """评价流程状态机"""
    waiting_reason = State()  # 等待用户填写评价理由