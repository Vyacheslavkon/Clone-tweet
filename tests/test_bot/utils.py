from datetime import datetime, timezone, time, timedelta

from financial_bot.handlers.utils import get_week_boundaries, get_month_boundaries
def called_bot(mock_bot, text: str):

    assert any(
        any(m in str(call) for m in ["SendMessage", "EditMessageText"])
        and text in str(call)
        for call in mock_bot.mock_calls
    ), f"Text '{text}'not found in bot responses."


def called_kb(mock_bot, text: str):
    assert any(
        text in str(call) for call in mock_bot.mock_calls
    ), f"Button with text '{text}' not found in bot responses."


def keyboard_check(kb, bot, i18n):

    for name in kb:
        expected_buttons = i18n.gettext(name)
        called_kb(bot, expected_buttons)


def get_expected_timestamps(period: str):

    if period == "day":
        start_day = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
        end_day = datetime.combine(datetime.now(timezone.utc).date(), time.max, tzinfo=timezone.utc)
        return start_day, end_day
    elif period == "week":
        start_day, end_day = get_week_boundaries()
        return start_day, end_day
    else:
        raise ValueError(f"Unknown period: {period}")



def keyboards() -> tuple:

    main_menu = [
        "Add/change data",
        "Generate report",
        "Settings",
        "cancel",
        "Enter amount",
    ]
    buttons = ["monthly planned budget", "limit expense", "savings goal", "cancel"]

    return main_menu, buttons


def kb_reports():

    buttons = ["day", "month", "week", "cancel"]

    return buttons


def kb_history():

    buttons = ["last two weeks", "arbitrary period"]

    return buttons

dict_invalid_data = {
    "hello": "Please enter a valid number.",
    "0": "The amount must be greater than zero.",
    "-200": "The amount must be greater than zero.",
}


comparison_dict = {
    "hello": "Please enter a valid number.",
    "5000": "This amount exceeds your planned budget.",
    "0": "The amount must be greater than zero.",
    "-100": "The amount must be greater than zero.",
}

