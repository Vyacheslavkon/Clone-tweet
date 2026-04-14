
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