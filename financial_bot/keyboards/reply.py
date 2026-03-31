from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="Enter amount"),
                        KeyboardButton(text="Add data"),
                        KeyboardButton(text="Generate report"))

    builder.row(KeyboardButton(text="Settings"), KeyboardButton(text="AI"))
    # as_markup() превращает строителя в объект клавиатуры
    return builder.as_markup(resize_keyboard=True)
