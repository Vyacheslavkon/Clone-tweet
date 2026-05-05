import os
from typing import Union

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.i18n import gettext as _
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import html
from aiogram.types import ErrorEvent
from loguru import logger
from dotenv import load_dotenv

from financial_bot.filters import I18nTextFilter
from financial_bot.keyboards.reply import get_main_menu
from financial_bot.repositories import create_user, get_user_by_id
from financial_bot.schemas import CreateUser

router = Router()
load_dotenv()
admin_id = os.getenv("ADMIN_ID")

@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):

    if not message.from_user:
        return

    user = await get_user_by_id(session, message.from_user.id)

    if not user:
        new_user = CreateUser(
            tg_id=message.from_user.id,
            first_name=message.from_user.first_name,
            language_code=message.from_user.language_code or "en",
        )

        await create_user(session, new_user)
        await message.answer(
            _("Hello, {name}! Glad to meet you!").format(
                name=message.from_user.first_name
            ),
            reply_markup=get_main_menu(),
        )

    else:

        await message.answer(
            _("Glad to see you {name}! Your balance: 0").format(
                name=message.from_user.first_name
            ),
            reply_markup=get_main_menu(),
        )


@router.message(I18nTextFilter("Cancel"))
@router.callback_query(F.data == "cancel")
async def cancel_handler(event: Union[Message, CallbackQuery], state: FSMContext):

    await state.clear()

    text = _("Action canceled. Returning to main menu...")
    kb = get_main_menu()

    if isinstance(event, Message):

        await event.answer(text, reply_markup=kb)

    elif isinstance(event, CallbackQuery) and isinstance(event.message, Message):

        await event.message.answer(text, reply_markup=kb)
        await event.answer()


# @router.errors()
# async def global_error_handler(event: ErrorEvent):
#     # 1. Логируем в Loguru для истории в файлах
#     logger.exception("Global error caught")
#
#     # 2. Собираем данные о пользователе
#     user = event.update.event_from_user
#     if user:
#         user_info = f"{html.bold(user.full_name)} (ID: {html.code(user.id)})"
#         # Ссылка на профиль (работает даже без username)
#         user_link = f"tg://user?id={user.id}"
#     else:
#         user_info = "Unknown user"
#         user_link = None
#
#     # 3. Формируем сообщение для админа
#     # Ограничиваем текст ошибки, чтобы не выйти за лимиты Telegram (4096 символов)
#     error_text = str(event.exception)[:500]
#
#     admin_msg = (
#         f"❌ {html.bold('Критическая ошибка!')}\n\n"
#         f"👤 {html.bold('От кого:')} {user_info}\n"
#         f"🛠 {html.bold('Ошибка:')} {html.code(type(event.exception).__name__)}\n"
#         f"📝 {html.bold('Детали:')} {html.code(error_text)}\n\n"
#         f"🔗 <a href='{user_link}'>Перейти к профилю пользователя</a>"
#     )
#
#     # 4. Отправка админу
#     try:
#         await event.update.bot.send_message(
#             chat_id=admin_id,
#             text=admin_msg,
#             parse_mode="HTML"
#         )
#     except Exception as e:
#         logger.error(f"Не удалось отправить уведомление админу: {e}")
#
#     # 5. Вежливый ответ пользователю
#     try:
#         if event.update.callback_query:
#             await event.update.callback_query.answer(
#                 "Произошла ошибка. Админ уже уведомлен!",
#                 show_alert=True
#             )
#         elif event.update.message:
#             await event.update.message.answer("⚠️ Произошла ошибка. Я уже сообщил разработчику.")
#     except Exception:
#         pass  # Если даже это не удалось — просто молчим