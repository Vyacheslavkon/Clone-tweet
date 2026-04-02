from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_back_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="back")
    return builder.as_markup()

def get_type():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Income", callback_data="type_income"))
    builder.add(InlineKeyboardButton(text="Expense", callback_data="type_expense"))
    # 2. Получаем билдер с кнопкой "Назад"
    back_builder = get_back_kb()

    # 3. Приклеиваем "Назад" к основной клавиатуре
    # .attach() добавит кнопки из back_builder в конец main_builder
    builder.attach(back_builder)
    return builder.as_markup()


