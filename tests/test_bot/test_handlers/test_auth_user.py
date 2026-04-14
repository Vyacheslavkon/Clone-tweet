from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.models import UserBot
from tests.test_bot.utils import called_bot, called_kb


async def test_cmd_start_existing_user(create_mock_update, mock_bot, test_i18n, test_user,
                         test_dp, test_session: AsyncSession):

    user_exist = test_user.tg_id
    create_message, _ = create_mock_update

    with test_i18n.context():
        message = create_message(text="/start", user_id=user_exist, update_id=10)
        await test_dp.feed_update(mock_bot, message)
        print("Line data mock bot:", mock_bot.mock_calls)
        result = await test_session.execute(select(UserBot).where(UserBot.tg_id == user_exist))
        user = result.scalar_one_or_none()

        assert user is not None, "The user was not created in the database!"
        text = "Рад вас видеть {}! Ваш баланс: 0".format(user.first_name)

        called_bot(mock_bot, text)

        button_text = "Введите сумму"

        called_kb(mock_bot, button_text)



async def test_cmd_start_new_user(mock_bot, test_session, test_i18n, test_dp, create_mock_update):

    user_not_exist = 123456
    create_message, _ = create_mock_update

    message = create_message(text="/start", user_id=user_not_exist, update_id=10)
    await test_dp.feed_update(mock_bot, message)

    result = await test_session.execute(select(UserBot).where(UserBot.tg_id == user_not_exist))
    user = result.scalar_one_or_none()

    assert user is not None, "The user was not created in the database!"
    text_2 = "Здравствуйте, {}! Рад с вами познакомиться!".format(user.first_name)
    called_bot(mock_bot, text_2)

    button_text = "Введите сумму"

    called_kb(mock_bot, button_text)




