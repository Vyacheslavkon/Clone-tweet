import pytest
from aiogram.types import Message, Chat, User
from datetime import datetime
from sqlalchemy import select

from financial_bot.models import Transactions  # Ваша модель SQLAlchemy


@pytest.mark.asyncio
async def test_add_income_to_db(test_dp, mock_bot, test_session):
    # 1. Создаем имитацию сообщения от пользователя
    chat = Chat(id=1, type="private")
    user = User(id=1, is_bot=False, first_name="TestUser")

    message = Message(
        message_id=1,
        date=datetime.now(),
        chat=chat,
        from_user=user,
        text="1000 Salary"  # Допустим, бот парсит это
    )

    # 2. Передаем сообщение в диспетчер
    await test_dp.feed_update(mock_bot, update={"message": message})

    # 3. Проверяем, что в ТЕСТОВОЙ базе появилась запись
    # (Поскольку в conftest у вас стоит rollback, данные после теста исчезнут)
    result = await test_session.execute(
        select(Transactions).where(Transactions.user_id == 1)
    )
    transaction = result.scalar_one_or_none()

    assert transaction is not None
    assert transaction.amount == 1000
    assert transaction.category == "Salary"

    # 4. Проверяем, что бот ответил пользователю (вызвал метод API)
    mock_bot.send_message.assert_called()
