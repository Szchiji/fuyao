# states.py
"""
有限状态机 (FSM) 定义
"""

from aiogram.fsm.state import State, StatesGroup

class RatingStates(StatesGroup):
    """评价流程状态"""
    waiting_teacher = State()      # 等待教师名称
    waiting_reason = State()        # 等待填写理由
    confirming = State()            # 确认提交
    completed = State()             # 完成