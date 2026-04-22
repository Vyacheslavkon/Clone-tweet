from financial_bot.states.add_data_states import AddDataState


def called_bot(mock_bot, text: str) -> bool:

    assert any(
        any(m in str(call) for m in ["SendMessage", "EditMessageText"])
        and text in str(call)
        for call in mock_bot.mock_calls
    ), f"Text '{text}'not found in bot responses."



def called_kb(mock_bot, text: str) -> bool:
    assert any(
        text in str(call) for call in mock_bot.mock_calls
    ), f"Кнопка с текстом '{text}' не найдена в ответах бота."


dict_invalid_data = {
    "hello": "Please enter a valid number.",
    "0": "The amount must be greater than zero.",
    "-200": "The amount must be greater than zero."
}

# comparison_dict = {
#     "hello": "**Пожалуйста, введите корректное число.**\\nНапример: 500 или 100.50",
#     "5000": "**Эта сумма превышает ваш общий бюджет.**",
#     "0": "**Сумма должна быть больше нуля.**",
#     "-100": "**Сумма должна быть больше нуля.**",
# }

comparison_dict = {
    "hello": "Please enter a valid number.",
    "5000": "This amount exceeds your total budget.",
    "0": "The amount must be greater than zero.",
    "-100": "The amount must be greater than zero.",
}