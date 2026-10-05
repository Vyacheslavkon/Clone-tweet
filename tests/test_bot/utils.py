from datetime import datetime, time, timezone

from financial_bot.handlers.utils import get_week_boundaries


def called_bot_old(mock_bot, text: str):

    assert any(
        any(m in str(call) for m in ["SendMessage", "EditMessageText"])
        and text in str(call)
        for call in mock_bot.mock_calls
    ), f"Text '{text}'not found in bot responses."


def called_kb_old(mock_bot, text: str):
    assert any(
        text in str(call) for call in mock_bot.mock_calls
    ), f"Button with text '{text}' not found in bot responses."


def called_bot(mock_bot, text: str, methods: tuple[str, ...] = ("SendMessage", "EditMessageText")):
    """Проверяет, что среди реально отправленных Telegram-методов есть
    вызов с заданным текстом. Сравнение идёт по точному типу объекта
    метода и его атрибуту .text, а не по строковому представлению вызова."""
    found = any(
        call.args
        and call.args[0].__class__.__name__ in methods
        and getattr(call.args[0], "text", None) == text
        for call in mock_bot.call_args_list

    )
    assert found, f"Text '{text}' not found among {methods} calls."


def called_kb(mock_bot, button_text: str, methods: tuple[str, ...] = ("SendMessage", "EditMessageText")):
    """Проверяет, что среди отправленных методов есть клавиатура,
    содержащая кнопку с заданным текстом."""
    for call in mock_bot.call_args_list:
        if not call.args or call.args[0].__class__.__name__ not in methods:
            continue
        reply_markup = getattr(call.args[0], "reply_markup", None)
        if reply_markup is None:
            continue
        for row in getattr(reply_markup, "inline_keyboard", []) or getattr(reply_markup, "keyboard", []):
            for button in row:
                btn_text = getattr(button, "text", None)
                if btn_text == button_text:
                    return
    assert False, f"Button with text '{button_text}' not found among {methods} calls."



def keyboard_check(kb, bot, i18n):

    for name in kb:
        expected_buttons = i18n.gettext(name)
        called_kb(bot, expected_buttons)


def get_expected_timestamps(period: str):

    if period == "day":
        start_day = datetime.combine(
            datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc
        )
        end_day = datetime.combine(
            datetime.now(timezone.utc).date(), time.max, tzinfo=timezone.utc
        )
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

    return ["day", "month", "week", "Cancel"]


def kb_history():

    return ["last two weeks", "arbitrary period"]


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
