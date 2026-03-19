# states.py
from aiogram.fsm.state import State, StatesGroup

class RatingStates(StatesGroup):
    waiting_reason = State()
    waiting_channel_id = State()
    waiting_start_message = State()
