from aiogram.fsm.state import State, StatesGroup


class GenerateReport(StatesGroup):

    waiting_for_period = State()
    sending_by_mail = State()  # for a paid subscription
