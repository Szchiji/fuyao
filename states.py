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
    waiting_channel_id = State()        # 等待管理员输入频道 ID
    waiting_teacher_name = State()      # 等待管理员输入教师名称
    waiting_welcome_msg = State()       # 等待管理员输入欢迎语
    waiting_welcome_buttons = State()   # 等待管理员输入欢迎语按钮
    waiting_broadcast_msg = State()     # 等待管理员输入广播消息
    waiting_broadcast_buttons = State() # 等待管理员输入广播按钮（可选）
    waiting_teacher_info = State()      # 等待管理员输入教师昵称/ID
