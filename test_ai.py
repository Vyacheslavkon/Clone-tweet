import asyncio
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI


async def test_openai_connection():
    # Загружаем переменные из .env файла
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    print("Проверяем настройки...")
    print(f"Base URL: {base_url}")
    print(
        f"API Key загружен: {'Да' if api_key else 'Нет'} (начинается на: {api_key[:7] if api_key else '---'})"
    )

    if not api_key or not base_url:
        print(
            "❌ Ошибка: Проверьте, что OPENAI_API_KEY и OPENAI_BASE_URL заполнены в .env!"
        )
        return

    # Инициализируем асинхронный клиент
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    try:
        print("\nОтправляем тестовый запрос к gpt-4o-mini...")

        # Делаем простой запрос
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": "Привет! Если ты видишь это сообщение, ответь словом 'Работает!'",
                }
            ],
            timeout=10.0,  # Таймаут 10 секунд, чтобы скрипт не завис вечно при проблемах с сетью
        )

        # Выводим ответ нейросети
        response_text = completion.choices[0].message.content
        print(f"\n🎉 Ответ от ИИ: {response_text}")

    except Exception as e:
        print(f"\n❌ Произошла ошибка при запросе: {e}")
        print(
            "Возможные причины: не активирован ключ, нулевой баланс на шлюзе или не запущен VPN (если шлюз требует его с вашего текущего IP)."
        )

    finally:
        # Закрываем сессию клиента
        await client.close()


if __name__ == "__main__":
    # Запускаем асинхронный скрипт
    asyncio.run(test_openai_connection())

"""
from pydantic import BaseModel, Field
from typing import List, Optional

class ReceiptItem(BaseModel):
    "Схема для одной позиции (товара) в чеке"
    name: str = Field(description="Название товара или услуги")
    price: float = Field(description="Цена за одну единицу товара")
    quantity: float = Field(description="Количество купленного товара")
    total: float = Field(description="Общая стоимость этой позиции (цена * количество)")

class ReceiptSchema(BaseModel):
    "Главная схема распознанного чека"
    store_name: Optional[str] = Field(None, description="Название магазина или организации")
    date: Optional[str] = Field(None, description="Дата покупки в формате ДД.ММ.ГГГГ")
    items: List[ReceiptItem] = Field(description="Список всех товаров в чеке")
    total_amount: float = Field(description="Итоговая сумма к оплате по всему чеку")

-__________________________________________________

from aiogram import Router, F
from aiogram.types import Message
from services.ai import AIService
from schemas.receipt import ReceiptSchema

ai_router = Router()

@ai_router.message(F.photo)
async def process_receipt_photo(message: Message, ai_service: AIService):
    # 1. Берем самое качественное фото из отправленных
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    
    # 2. Формируем прямую ссылку на фото для OpenAI
    file_url = f"https://telegram.org{message.bot.token}/{file.file_path}"
    
    await message.answer("🔄 Считываю данные с чека, секунду...")
    
    try:
        # 3. Вызываем наш асинхронный метод со строгой схемой ответа
        receipt: ReceiptSchema = await ai_service.analyze_image(
            image_url=file_url,
            response_schema=ReceiptSchema,
            prompt="Найди на изображении чек. Извлеки название магазина, дату, все купленные товары с ценами и итоговую сумму."
        )
        
        # 4. На выходе мы имеем чистый Python-объект!
        text = (
            f"🛒 **Магазин:** {receipt.store_name or 'Не определен'}\n"
            f"📅 **Дата:** {receipt.date or 'Не определена'}\n"
            f"💰 **Итого:** {receipt.total_amount} руб.\n\n"
            f"Позиций в чеке: {len(receipt.items)}"
        )
        await message.answer(text, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer("❌ Не удалось распознать чек. Попробуйте сделать фото четче.")

"""