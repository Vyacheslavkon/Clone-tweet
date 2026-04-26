from aiogram.fsm.state import State, StatesGroup


class AmountState(StatesGroup):

    waiting_for_amount = State()  # enter amount
    waiting_for_type = State()  # income or expense
    waiting_for_cat = State()  # category expense
    waiting_for_description = State()  # description of consumption
