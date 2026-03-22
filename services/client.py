# import openai
# from typing import List, Dict
# from .schemas import AIResponse
#
# class AIService:
#     def __init__(self, api_key: str, model: str = "gpt-4-turbo"):
#         self.client = openai.AsyncOpenAI(api_key=api_key)
#         self.model = model
#
#     async def get_chat_completion(
#         self,
#         messages: List[Dict[str, str]],
#         temperature: float = 0.7
#     ) -> AIResponse:
#         """
#         Принимает список сообщений в формате OpenAI и возвращает объект ответа.
#         Никакой логики БД здесь нет!
#         """
#         try:
#             response = await self.client.chat.completions.create(
#                 model=self.model,
#                 messages=messages,
#                 temperature=temperature
#             )
#             content = response.choices[0].message.content
#             return AIResponse(content=content, tokens_used=response.usage.total_tokens)
#         except Exception as e:
#             # Логируем и выбрасываем свое исключение
#             raise ConnectionError(f"AI Service error: {e}")
