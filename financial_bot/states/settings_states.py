from aiogram.fsm.state import State, StatesGroup


class SettingsState(StatesGroup):
    waiting_for_custom_timezone = State()
