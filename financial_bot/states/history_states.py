from aiogram.fsm.state import State, StatesGroup

class HistoryState(StatesGroup):

    waiting_for_period_history = State()
    waiting_for_two_weeks = State()
    waiting_for_arbitrary_period = State()