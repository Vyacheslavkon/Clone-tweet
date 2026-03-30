from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="Registration"), KeyboardButton(text="Get started"))
    builder.row(KeyboardButton(text="Settings"))
    # as_markup() превращает строителя в объект клавиатуры
    return builder.as_markup(resize_keyboard=True)
