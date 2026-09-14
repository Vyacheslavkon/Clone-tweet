# from openai import APIConnectionError, APIStatusError, RateLimitError

# try:
#
#     # запрос к API
# except RateLimitError:
#     # Закончились деньги или лимиты запросов в минуту
# except APIStatusError as e:
#     # Ошибка на стороне сервера OpenAI (например, 500)


class TruncatedResponseError(Exception):
    """Поднимается, когда ответ от OpenAI был обрезан из-за лимита
    max_completion_tokens (finish_reason == 'length'), а не из-за
    реальной ошибки валидации JSON-структуры."""
    pass
