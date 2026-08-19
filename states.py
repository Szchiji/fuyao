# states.py
"""
有限状态机 (FSM) 定义
"""

from aiogram.fsm.state import State, StatesGroup


class RatingStates(StatesGroup):
    """评价流程状态机"""
    waiting_forwarded_message = State()  # 等待用户转发教师消息
    waiting_score_teaching = State()   # 等待用户为教学质量打分（1-5）
    waiting_score_grading = State()    # 等待用户为给分情况打分（1-5）
    waiting_score_difficulty = State() # 等待用户为课程难度打分（1-5）
    waiting_reason = State()           # 等待用户填写评价理由


class AdminStates(StatesGroup):
    """管理员操作状态机"""
    waiting_channel_id = State()          # 等待管理员输入频道 ID
    waiting_teacher_name = State()        # 等待管理员输入教师名称
    waiting_welcome_msg = State()         # 等待管理员输入欢迎语
    waiting_welcome_buttons = State()     # 等待管理员输入欢迎语按钮
    waiting_broadcast_msg = State()       # 等待管理员输入广播消息
    waiting_broadcast_buttons = State()   # 等待管理员输入广播按钮（可选）
    waiting_teacher_info = State()        # 等待管理员输入教师昵称/ID
    waiting_blacklist_user_id = State()   # 等待管理员输入要拉黑的用户 ID
    waiting_auto_delete_delay = State()   # 等待管理员输入自动删除时间
