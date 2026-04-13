import pytest
from unittest.mock import AsyncMock, patch
from financial_bot.handlers.common import cmd_start
from financial_bot.models import UserBot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.keyboard import ReplyKeyboardMarkup


async def test_cmd_start(create_mock_update, mock_bot, test_i18n, test_user,
                         test_dp, test_session: AsyncSession):

    user_id = 12345
    create_message, _ = create_mock_update

    with test_i18n.context():
        message = create_message(text="/start", user_id=user_id, update_id=10)
        await test_dp.feed_update(mock_bot, message)

        result = await test_session.execute(select(UserBot).where(UserBot.tg_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            assert any(
                any(m in str(call) for m in ["SendMessage", "EditMessageText"])
                and f"Рад вас видеть {user.first_name}! Ваш баланс: 0" in str(call)
                for call in mock_bot.mock_calls
            ), f"Text not found in bot responses."



        # args, kwargs = message.answer.call_args
        # reply_markup = kwargs.get("reply_markup")
        #
        # assert reply_markup.keyboard[0][0].text == "Введите сумму"
        #
        # assert isinstance(reply_markup, ReplyKeyboardMarkup)