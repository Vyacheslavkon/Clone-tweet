import pytest
from unittest.mock import AsyncMock, patch
from financial_bot.handlers.common import cmd_start
from financial_bot.states.amount_states import AmountState
from financial_bot.models import UserBot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.keyboard import ReplyKeyboardMarkup


async def test_cmd_start(test_session: AsyncSession):
    message = AsyncMock()
    message.from_user.id = 777
    message.from_user.first_name = "TestUser"
    message.from_user.language_code = "ru"
    message.answer = AsyncMock()


    # Заглушка для i18n (чтобы не упало на функции _())
    with patch("handlers.common._", side_effect=lambda x: x):
        # 2. Впервые вызываем хендлер (регистрация)
        await cmd_start(message, test_session)

        # ПРОВЕРКА 1: Пользователь создался в реальной БД
        query = select(UserBot).where(UserBot.tg_id == 777)
        result = await test_session.execute(query)
        user_in_db = result.scalar_one_or_none()
        assert user_in_db is not None
        assert user_in_db.first_name == "TestUser"

        # ПРОВЕРКА 2: Бот ответил приветствием новичка
        message.answer.assert_called()
        assert "Hello" in message.answer.call_args[0][0]

        # 3. Вызываем хендлер ВТОРОЙ РАЗ (авторизация)
        await cmd_start(message, test_session)

        # ПРОВЕРКА 3: Бот ответил как старому знакомому
        assert "Glad to see you" in message.answer.call_args[0][0]

        args, kwargs = message.answer.call_args
        reply_markup = kwargs.get("reply_markup")

        assert reply_markup.keyboard[0][0].text == "Введите сумму"

        assert isinstance(reply_markup, ReplyKeyboardMarkup)