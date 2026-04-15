from aiogram.fsm.state import StatesGroup, State

class AddDataState(StatesGroup):

    waiting_for_type_data = State()

