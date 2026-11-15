from sqlalchemy import select

from financial_bot.models import UserBot


async def test_session_rolls_back_between_tests_part1(test_session):
    test_session.add(UserBot(tg_id=777, first_name="x", language_code="en"))
    await test_session.commit()


async def test_session_rolls_back_between_tests_part2(test_session):
    result = await test_session.execute(select(UserBot).where(UserBot.tg_id == 777))
    assert result.scalar_one_or_none() is None
