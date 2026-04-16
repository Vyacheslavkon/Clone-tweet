from aiogram.fsm.state import StatesGroup, State

class AddDataState(StatesGroup):

    waiting_for_type_data = State()
    waiting_for_monthly_budget = State()
    waiting_for_limit_expense = State()
    waiting_for_savings_goal = State()

