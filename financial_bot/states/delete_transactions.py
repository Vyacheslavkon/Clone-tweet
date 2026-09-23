from aiogram.fsm.state import State, StatesGroup


class DeleteTodayState(StatesGroup):
    browsing = State()