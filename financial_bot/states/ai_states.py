from aiogram.fsm.state import State, StatesGroup


class AIState(StatesGroup):

    waiting_for_request = State()
    waiting_for_receipt = State()
