from aiogram.fsm.state import State, StatesGroup


class AIState(StatesGroup):

    waiting_for_request = State()
    waiting_for_weekly_analysis = State()
    waiting_for_monthly_analysis = State()
    waiting_for_check = State()