from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_confirm_kb():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_tx"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_tx"))
    return builder.as_markup()
