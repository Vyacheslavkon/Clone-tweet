from aiogram.fsm.state import State, StatesGroup


class AmountState(StatesGroup):

    waiting_for_amount = State()
    waiting_for_type = State()
    waiting_for_cat = State()
    waiting_for_description = State()
