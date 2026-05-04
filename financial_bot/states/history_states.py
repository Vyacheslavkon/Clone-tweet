from aiogram.fsm.state import State, StatesGroup

class HistoryState(StatesGroup):

    waiting_for_period_history = State()
    waiting_for_data_start = State()
    waiting_for_data_end = State()

