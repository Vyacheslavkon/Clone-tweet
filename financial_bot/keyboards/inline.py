from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.i18n import gettext as _


def get_back_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text=_("⬅️ Back"), callback_data="back")
    return builder.as_markup()

def get_type():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=_("Income"), callback_data="type_income"))
    builder.add(InlineKeyboardButton(text=_("Expense"), callback_data="type_expense"))
    # 2. Получаем билдер с кнопкой "Назад"
    back_builder = get_back_kb()

    # 3. Приклеиваем "Назад" к основной клавиатуре
    # .attach() добавит кнопки из back_builder в конец main_builder
    builder.attach(back_builder)
    return builder.as_markup()


def get_category():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=_("Food"), callback_data="cat_food"))
    builder.add(InlineKeyboardButton(text=_("Home"), callback_data="cat_home"))
    builder.add(InlineKeyboardButton(text=_("Entertainment"), callback_data="cat_entertainment"))
    builder.add(InlineKeyboardButton(text=_("Transport"), callback_data="cat_transport"))
    builder.add(InlineKeyboardButton(text=_("Health"), callback_data="cat_health"))
    builder.add(InlineKeyboardButton(text=_("Other"), callback_data="cat_other"))
    builder.adjust(2)
    back_builder = get_back_kb()
    builder.attach(back_builder)
    return builder.as_markup()

def get_description():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=_("Description"), callback_data="description"))
    builder.add(InlineKeyboardButton(text=_("Skip description"), callback_data="skip_description"))

    back_builder = get_back_kb()
    builder.attach(back_builder)
    return builder.as_markup()
