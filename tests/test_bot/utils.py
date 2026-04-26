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


def keyboards() -> tuple:

    main_menu = [
        "Add/change data",
        "Generate report",
        "Settings",
        "cancel",
        "Enter amount",
    ]
    buttons = ["monthly budget", "limit expense", "savings goal", "cancel"]

    return main_menu, buttons


dict_invalid_data = {
    "hello": "Please enter a valid number.",
    "0": "The amount must be greater than zero.",
    "-200": "The amount must be greater than zero.",
}


comparison_dict = {
    "hello": "Please enter a valid number.",
    "5000": "This amount exceeds your total budget.",
    "0": "The amount must be greater than zero.",
    "-100": "The amount must be greater than zero.",
}
