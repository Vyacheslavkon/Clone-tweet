from financial_bot.schemas import AddData
from financial_bot.states.generate_report import GenerateReport
from tests.test_bot.utils import (
    called_bot,
    comparison_dict,
    dict_invalid_data,
    keyboard_check,
    kb_reports,
)


async def test_report_period(test_dp, create_mock_update, mock_bot, test_i18n, test_user):

    create_message, _ = create_mock_update
    user_id = 12345

    text = test_i18n.gettext("Generate report")
    msg_first = create_message(text=text, user_id=user_id, update_id=1)
    await test_dp.feed_update(mock_bot, msg_first)
    expected_text = test_i18n.gettext("please, select period")
    called_bot(mock_bot, expected_text)

    buttons = kb_reports()

    keyboard_check(buttons, mock_bot, test_i18n)

    state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
    current_state = await state.get_state()
    assert current_state == GenerateReport.waiting_for_period.state