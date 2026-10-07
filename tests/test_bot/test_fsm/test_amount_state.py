import uuid
from unittest.mock import AsyncMock

from redis import RedisError
from sqlalchemy import select

from financial_bot.filters import DeleteTransactionCallback
from financial_bot.models import Transactions
from financial_bot.repositories import create_user
from financial_bot.schemas import CreateUser
from financial_bot.states.amount_states import AmountState
from tests.test_bot.utils import called_bot, called_kb


async def test_full_transaction_flow(
    test_dp,
    mock_bot,
    create_mock_update,
    test_session,
    test_i18n,
    test_user,
    cache_service,
):

    create_message, create_callback = create_mock_update
    user_id = 12345

    state = test_dp.fsm.get_context(bot=mock_bot, user_id=user_id, chat_id=user_id)
    await state.set_state(AmountState.waiting_for_amount)

    msg_step1 = create_message(text="500", user_id=user_id, update_id=1)
    await test_dp.feed_update(mock_bot, msg_step1)

    expected_text_step1 = test_i18n.gettext("Select type:")
    called_bot(mock_bot, expected_text_step1)

    buttons_type = ["Income", "Expense", "Back", "Cancel"]
    for text in buttons_type:
        expected_button_type = test_i18n.gettext(text)
        called_kb(mock_bot, expected_button_type)
    mock_bot.reset_mock()

    cb_step2 = create_callback(data="type_expense", user_id=user_id, update_id=2)
    await test_dp.feed_update(mock_bot, cb_step2)

    expected_text_step2 = test_i18n.gettext("Select category")
    expected_button_cat = test_i18n.gettext("Food")
    called_bot(mock_bot, expected_text_step2)
    called_kb(mock_bot, expected_button_cat)

    buttons_cat = [
        "Food",
        "Home",
        "Entertainment",
        "Transport",
        "Health",
        "Back",
        "Cancel",
    ]
    for text in buttons_cat:
        expected_button_cat = test_i18n.gettext(text)
        called_kb(mock_bot, expected_button_cat)
    mock_bot.reset_mock()

    cb_step3 = create_callback(data="cat_food", user_id=user_id, update_id=3)
    await test_dp.feed_raw_update(mock_bot, cb_step3)

    expected_text_step3 = test_i18n.gettext("Write a comment")
    called_bot(mock_bot, expected_text_step3)

    buttons_desc = ["Skip description", "Back", "Cancel"]
    for text in buttons_desc:
        expected_button_desc = test_i18n.gettext(text)
        called_kb(mock_bot, expected_button_desc)

    mock_bot.reset_mock()

    msg_step4 = create_message(text="lunch in a cafe", user_id=user_id, update_id=4)
    await test_dp.feed_raw_update(mock_bot, msg_step4)

    expected_text_step4 = test_i18n.gettext("Data saved successfully!")
    called_bot(mock_bot, expected_text_step4)
    result = await test_session.execute(select(Transactions))

    record = result.scalar_one()
    assert record.amount == 500
    assert record.type == "expense"
    assert record.category == "food"
    assert record.description == "lunch in a cafe"
    assert record.batch_id is not None  # new

    exp_text = test_i18n.gettext("❌ cancel operation")
    called_kb(mock_bot, exp_text)


async def test_cancel_transaction(
    test_dp, mock_bot, create_mock_update, test_session, test_i18n
):
    _, create_callback = create_mock_update
    user_id = 12345

    state = test_dp.fsm.get_context(bot=mock_bot, user_id=user_id, chat_id=user_id)
    await state.set_state(AmountState.waiting_for_type)
    await state.update_data(amount=500.0)

    cb_cancel = create_callback(data="cancel", user_id=user_id, update_id=10)
    await test_dp.feed_update(mock_bot, cb_cancel)

    expected_text = test_i18n.gettext("Action canceled. Returning to main menu...")
    called_bot(mock_bot, expected_text)

    current_state = await state.get_state()
    assert current_state is None, "The condition did not reset after cancellation"

    result = await test_session.execute(select(Transactions))
    records = result.scalars().all()
    assert len(records) == 0, (
        "The entry appeared in the database even though " "the transaction was canceled"
    )


async def test_back(test_dp, mock_bot, create_mock_update, test_i18n):

    _, create_callback = create_mock_update
    user_id = 12345

    state = test_dp.fsm.get_context(bot=mock_bot, user_id=user_id, chat_id=user_id)
    await state.set_state(AmountState.waiting_for_type)
    await state.update_data(amount=500.0)

    cb_back = create_callback(data="back", user_id=user_id, update_id=10)
    await test_dp.feed_update(mock_bot, cb_back)

    expected_text1 = test_i18n.gettext("Please enter the amount!")
    called_bot(mock_bot, expected_text1)

    current_state_amount = await state.get_state()

    await state.set_state(AmountState.waiting_for_cat)
    await state.update_data(type="expense")

    cb_back = create_callback(data="back", user_id=user_id, update_id=10)
    await test_dp.feed_update(mock_bot, cb_back)

    expected_text2 = test_i18n.gettext("Select type")
    called_bot(mock_bot, expected_text2)

    current_state_type = await state.get_state()

    await state.set_state(AmountState.waiting_for_description)
    await state.update_data(category="food")

    cb_back = create_callback(data="back", user_id=user_id, update_id=10)
    await test_dp.feed_update(mock_bot, cb_back)

    expected_text3 = test_i18n.gettext("Select category")
    called_bot(mock_bot, expected_text3)

    current_state_cat = await state.get_state()

    assert current_state_amount == AmountState.waiting_for_amount
    assert current_state_type == AmountState.waiting_for_type
    assert current_state_cat == AmountState.waiting_for_cat


async def test_manual_transaction_can_be_deleted_via_inline_button(
    test_dp,
    mock_bot,
    create_mock_update,
    test_session,
    test_i18n,
    test_user,
    cache_service,
):
    create_message, create_callback = create_mock_update
    user_id = test_user.tg_id

    state = test_dp.fsm.get_context(bot=mock_bot, user_id=user_id, chat_id=user_id)
    await state.set_state(AmountState.waiting_for_amount)

    await test_dp.feed_update(mock_bot, create_message("300", user_id, 1))
    await test_dp.feed_update(mock_bot, create_callback("type_expense", user_id, 2))
    await test_dp.feed_raw_update(mock_bot, create_callback("cat_food", user_id, 3))
    await test_dp.feed_raw_update(mock_bot, create_message("coffee", user_id, 4))

    result = await test_session.execute(select(Transactions))
    record = result.scalar_one()
    batch_id = record.batch_id
    assert batch_id is not None

    mock_bot.reset_mock()

    delete_callback_data = DeleteTransactionCallback(batch_id=batch_id).pack()
    cb_delete = create_callback(delete_callback_data, user_id, 5)

    await test_dp.feed_update(mock_bot, cb_delete)

    result_after = await test_session.execute(select(Transactions))
    assert result_after.scalar_one_or_none() is None

    expected_text = test_i18n.gettext(
        "❌ The record has been cancelled and removed from the database."
    )
    called_bot(mock_bot, expected_text)


async def test_cannot_delete_other_users_transaction(
    test_dp, mock_bot, create_mock_update, test_session, test_user, cache_service
):
    create_message, create_callback = create_mock_update

    other_batch_id = str(uuid.uuid4())
    transaction = Transactions(
        user_id=test_user.id,
        amount=100,
        type="expense",
        category="food",
        batch_id=other_batch_id,
    )
    test_session.add(transaction)
    await test_session.flush()

    attacker_tg_id = 99999
    attacker_data = {
        "tg_id": attacker_tg_id,
        "language_code": "ru",
        "first_name": "Attacker",
    }
    await create_user(test_session, CreateUser(**attacker_data))
    await test_session.flush()

    cb_data = DeleteTransactionCallback(batch_id=other_batch_id).pack()
    cb = create_callback(cb_data, attacker_tg_id, 1)
    await test_dp.feed_update(mock_bot, cb)

    result = await test_session.execute(
        select(Transactions).where(Transactions.batch_id == other_batch_id)
    )
    assert result.scalar_one_or_none() is not None


async def test_delete_survives_cache_invalidation_failure(
    test_dp, mock_bot, create_mock_update, test_session, test_user, cache_service
):
    create_message, create_callback = create_mock_update

    batch_id = str(uuid.uuid4())
    transaction = Transactions(
        user_id=test_user.id,
        amount=100,
        type="expense",
        category="food",
        batch_id=batch_id,
    )
    test_session.add(transaction)
    await test_session.flush()

    cache_service.invalidate_user_cache = AsyncMock(side_effect=RedisError("down"))

    cb_data = DeleteTransactionCallback(batch_id=batch_id).pack()
    cb = create_callback(cb_data, test_user.tg_id, 1)
    await test_dp.feed_update(mock_bot, cb)

    result = await test_session.execute(
        select(Transactions).where(Transactions.batch_id == batch_id)
    )
    assert result.scalar_one_or_none() is None


async def test_double_click_delete_shows_not_found(
    test_dp,
    mock_bot,
    create_mock_update,
    test_session,
    test_user,
    cache_service,
    test_i18n,
):
    create_message, create_callback = create_mock_update

    batch_id = str(uuid.uuid4())
    transaction = Transactions(
        user_id=test_user.id,
        amount=100,
        type="expense",
        category="food",
        batch_id=batch_id,
    )
    test_session.add(transaction)
    await test_session.flush()

    cb_data = DeleteTransactionCallback(batch_id=batch_id).pack()

    await test_dp.feed_update(mock_bot, create_callback(cb_data, test_user.tg_id, 1))
    print("MOCK DATA first:", mock_bot.mock_calls)
    result_after_first = await test_session.execute(
        select(Transactions).where(Transactions.batch_id == batch_id)
    )
    assert result_after_first.scalar_one_or_none() is None

    mock_bot.reset_mock()

    await test_dp.feed_update(mock_bot, create_callback(cb_data, test_user.tg_id, 2))

    expected_error_text = test_i18n.gettext("Record not found.")

    assert (
        mock_bot.called
    ), "The bot did not receive a single method call for the second click!"

    alert_was_sent = False

    for call in mock_bot.call_args_list:

        if call.args and call.args[0].__class__.__name__ == "AnswerCallbackQuery":
            method_object = call.args[0]

            if method_object.text == expected_error_text:
                alert_was_sent = True
                assert (
                    method_object.show_alert is True
                ), "The show_alert flag must be True for the pop-up window!"
                break

    assert (
        alert_was_sent
    ), f"A pop-up alert with the text '{expected_error_text}' was not sent via AnswerCallbackQuery!"
