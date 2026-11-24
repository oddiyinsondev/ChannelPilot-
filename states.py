from aiogram.fsm.state import State, StatesGroup

class AddChannelState(StatesGroup):
    waiting_for_channel = State()

class PostState(StatesGroup):
    waiting_for_content = State()
    waiting_for_target_channel = State()
    waiting_for_schedule_type = State()
    waiting_for_custom_time = State()
