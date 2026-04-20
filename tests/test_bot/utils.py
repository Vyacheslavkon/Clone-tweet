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


# add_data = {
#     "monthly budget": "Enter your estimated monthly budget",
#     "limit expense": "Enter the spending limit amount",
#     "savings goal": "Enter your desired savings amount",
# }

add_data = {
    "бюджет на месяц": "Введите свой предполагаемый ежемесячный бюджет",
    "лимит расходов": "Введите сумму лимита расходов",
    "цель сбережений": "Введите желаемую сумму сбережений",
}

dict_state = {

}