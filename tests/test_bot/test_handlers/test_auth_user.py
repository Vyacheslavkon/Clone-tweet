from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import MagicMock

from financial_bot.models import UserBot
from tests.test_bot.utils import called_bot, keyboard_check, keyboards
from financial_bot.handlers.common import global_error_handler

main_menu, _ = keyboards()


async def test_cmd_start_existing_user(
    create_mock_update,
    mock_bot,
    test_i18n,
    test_user,
    test_dp,
    test_session: AsyncSession,
):

    user_exist = test_user.tg_id
    create_message, _ = create_mock_update

    message = create_message(text="/start", user_id=user_exist, update_id=10)
    await test_dp.feed_update(mock_bot, message)
    result = await test_session.execute(
        select(UserBot).where(UserBot.tg_id == user_exist)
    )
    user = result.scalar_one_or_none()

    assert user is not None, "The user was not created in the database!"

    template = test_i18n.gettext("Glad to see you {name}! Your balance: 0")
    expected_text = template.format(name=user.first_name)
    called_bot(mock_bot, expected_text)

    keyboard_check(main_menu, mock_bot, test_i18n)


async def test_cmd_start_new_user(
    mock_bot, test_session, test_i18n, test_dp, create_mock_update
):

    user_not_exist = 123456
    create_message, _ = create_mock_update

    message = create_message(text="/start", user_id=user_not_exist, update_id=10)
    await test_dp.feed_update(mock_bot, message)

    result = await test_session.execute(
        select(UserBot).where(UserBot.tg_id == user_not_exist)
    )
    user = result.scalar_one_or_none()

    assert user is not None, "The user was not created in the database!"

    template = test_i18n.gettext("Hello, {name}! Glad to meet you!")
    expected_text = template.format(name=user.first_name)
    called_bot(mock_bot, expected_text)

    keyboard_check(main_menu, mock_bot, test_i18n)





async def test_global_error_handler_with_message(mock_bot, create_mock_update, test_user):

    update, _ = create_mock_update

    mock_update = update(text="some text",update_id=test_user.tg_id, user_id=1)


    # 3. Имитируем событие ошибки (ErrorEvent)
    mock_exception = ValueError("Тестовая ошибка <with_html_unsafe_tags>")

    # Мокаем сам ErrorEvent
    mock_event = MagicMock()
    mock_event.exception = mock_exception
    mock_event.update = mock_update

    # 4. Вызываем обработчик
    # Передаем заглушку для gettext (_), если используется интернационализация логов
    await global_error_handler(mock_event)

    # 5. Проверяем, что админу ушло сообщение
    mock_bot.send_message.assert_called_once()
    call_kwargs = mock_bot.send_message.call_args.kwargs

    #assert call_kwargs["chat_id"] == admin_id  # Убедитесь, что admin_id доступен в тесте
    assert "Критическая ошибка!" in call_kwargs["text"]
    assert "Ivan Ivanov" in call_kwargs["text"]
    assert "12345" in call_kwargs["text"]

    # 6. Проверяем, что пользователю ушел ответ в чат
    # Метод message.answer внутри вызывает bot.send_message
    # Проверим, что был второй вызов send_message (для юзера)
    assert mock_bot.send_message.call_count == 2