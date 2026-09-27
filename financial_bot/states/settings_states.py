from aiogram.fsm.state import StatesGroup, State


class SettingsState(StatesGroup):
    waiting_for_custom_timezone = State()