import pytest
from unittest.mock import AsyncMock
from financial_bot.handlers.transactions import (go_back,
                                                 new_amount, process_amount_input,
                                                 type_amount, category_amount,
                                                 end_with_message,end_with_callback,
                                                 save_to_db_and_finish)

from financial_bot.states.amount_states import AmountState


# @pytest.mark.asyncio
# async def test_process_name():
#     # 1. Создаем мок сообщения
#     message = AsyncMock()
#     message.text = "Иван"
#
#     # 2. Создаем мок состояния FSM
#     state = AsyncMock()
#
#     # 3. Вызываем хендлер
#     await process_name(message, state)
#
#     # 4. ПРОВЕРКИ:
#     # Проверяем, что данные "Иван" были переданы в update_data
#     state.update_data.assert_called_with(name="Иван")
#
#     # Проверяем, что состояние изменилось на Form.age
#     state.set_state.assert_called_with(Form.age)
#
#     # Проверяем, что бот отправил правильный текст
#     message.answer.assert_called_with("Сколько тебе лет?")






