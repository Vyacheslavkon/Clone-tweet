import os
import io
import gettext
import tempfile
import logging
import uuid
import openai

from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram import Bot
from loguru import logger
from pathlib import Path

from services.client import ai_service
from services.schemas import ReceiptAnalysisSchema, ReceiptListAnalysisSchema
from financial_bot.repositories import save_receipt_to_db
from services.utils_pipelines import get_isolated_session, merge_transactions_by_category
from financial_bot.keyboards.inline import get_delete_keyboard
from rapidocr_onnxruntime import RapidOCR

# for check.

#ocr = RapidOCR()
    # det_model_path="/application/ocr_models/ch_PP-OCRv4_det_infer.onnx",
    #
    # # Указываем модель распознавания текста (latin)
    # rec_model_path="/application/ocr_models/ch_PP-OCRv4_rec_infer.onnx",
    #
    # # Путь к словарю символов
    # rec_keys_path="/application/ocr_models/multilingual_dict.txt",





# logging.getLogger("ppocr").setLevel(logging.WARNING)
#
# async def async_process_receipt(chat_id: int, db_user_id: int,
#                                 locale: str, image_bytes: bytes):
#
#     locales_dir = Path(__file__).resolve().parent.parent / "financial_bot" / "locales"
#
#     try:
#         lang = gettext.translation(
#             domain='messages',
#             localedir=str(locales_dir),  # gettext требует строку, а не объект Path
#             languages=[locale],
#             fallback=True
#         )
#     except Exception as e:
#         logger.error(f"Не удалось загрузить локализацию из {locales_dir}: {e}")
#         lang = gettext.NullTranslations()  # Фоллбек на оригинальный текст, если файлы не найдены
#
#     _ = lang.gettext
#
#
#
#     bot_session = AiohttpSession()
#     bot = Bot(
#         token=os.getenv("BOT_TOKEN"),
#         session=bot_session,
#         default=DefaultBotProperties(parse_mode=ParseMode.HTML)
#     )
#
#     session = get_isolated_session()
#     try:
#         #file_io = await bot.download_file(file_path) #(to improve productivity)
#
#         # Создаем временный файл в системной папке /tmp (или AppData в Windows)
#         # suffix=".jpg" нужен, чтобы PaddleOCR понимал формат файла
#         with tempfile.NamedTemporaryFile(delete=True, suffix=".jpg") as temp_file:
#             # 1. Записываем байты во временный файл
#             temp_file.write(image_bytes)
#             temp_file.flush()  # Принудительно сохраняем данные на диск
#
#             # Получаем абсолютный путь к файлу (например, '/tmp/tmp_abc123.jpg')
#             file_path = temp_file.name
#
#             logger.info(f"Начало обработки чека для пользователя {db_user_id}")
#             logger.info("Path for func: {}".format(file_path))
#
#             result, elapse_list = ocr(file_path)
#             logger.info("Data for func: {}".format(result))
#
#         if not result or not result[0]:
#             logger.warning("PaddleOCR не нашел текст на изображении")
#             return {"status": "error", "message": "No text found"}
#
#         logger.info("Type data: {}; Data for func: {}".format(type(result),result))
#         # clear_text = clean_ocr_text(result)
#         # text = merge_ocr_blocks_to_text(clear_text)
#         text = merge_ocr_blocks_to_text(result)
#         clear_text = decode_visual_translit(text)
#         logger.info("Text for AI: {}".format(clear_text))
#
#         analysis_result: ReceiptAnalysisSchema = await ai_service.process_receipt(
#                     text=clear_text,
#                     response_schema=ReceiptAnalysisSchema,
#                     locale=locale
#
#                 )
#
#         await save_receipt_to_db(
#             session=session,
#             user_id=db_user_id,
#             analysis_result=analysis_result,
#             photo_url=None,
#             raw_text=analysis_result.model_dump_json()
#         )
#
#         msg_text = _((
#             f"✅ <b>The check has been processed successfully!</b>\n\n"
#             f"🏬 Description: {analysis_result.description or 'Неизвестно'}\n"
#             f"💰 Amount: {analysis_result.amount} {analysis_result.currency}\n"
#             f"🗂 Category: {analysis_result.category}\n\n"
#             f"🧾 Positions have been added to your detailed statistics."
#         ))
#         await bot.send_message(chat_id=chat_id, text=msg_text)
#
#     except Exception as e:
#         logger.error(f"Error processing check for user {db_user_id}: {e}", exc_info=True)
#
#         await session.rollback()
#
#         await bot.send_message(
#             chat_id=chat_id,
#             text=_("❌ Unfortunately, we couldn't recognize your receipt. Please make sure the photo is clear and try again.")
#         )
#
#     finally:
#         await session.close()
#         await bot_session.close()



async def async_process_receipt(chat_id: int, db_user_id: int,
                                locale: str, voice_bytes: bytes):

    locales_dir = Path(__file__).resolve().parent.parent / "financial_bot" / "locales"

    try:
        lang = gettext.translation(
            domain='messages',
            localedir=str(locales_dir),  # gettext требует строку, а не объект Path
            languages=[locale],
            fallback=True
        )
    except Exception as e:
        logger.error(f"Не удалось загрузить локализацию из {locales_dir}: {e}")
        lang = gettext.NullTranslations()  # Фоллбек на оригинальный текст, если файлы не найдены

    _ = lang.gettext



    bot_session = AiohttpSession()
    bot = Bot(
        token=os.getenv("BOT_TOKEN"),
        session=bot_session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    session = get_isolated_session()
    try:

        analysis_result: ReceiptListAnalysisSchema = await ai_service.process_voice_message(
                    voice_bytes=voice_bytes,
                    response_schema=ReceiptListAnalysisSchema,
                    locale=locale

                )

        if not analysis_result.is_shopping_related:
            joke_text = analysis_result.error_message or _("Unable to recognize the purchase amount.")

            await bot.send_message(chat_id=chat_id, text=f"❌ {joke_text}")
            logger.info("Обработка отменена ИИ для юзера %s. Шутка: %s", db_user_id, joke_text)
            return {"status": "cancelled", "message": joke_text}


        valid_transactions = [t for t in analysis_result.transactions if t.amount > 0]

        analysis_result.transactions = valid_transactions

        if not analysis_result.transactions:
            await bot.send_message(chat_id=chat_id, text=_("❌ No transactions found to save."))
            return {"status": "cancelled", "message": "Empty transactions list"}


        final_analysis_result = merge_transactions_by_category(analysis_result)

        message_batch_id = str(uuid.uuid4())

        await save_receipt_to_db(
            session=session,
            user_id=db_user_id,
            analysis_result=final_analysis_result,
            photo_url=None,
            batch_id=message_batch_id,
            raw_text=analysis_result.model_dump_json()
        )


        total_receipt_amount = sum(transaction.amount for transaction in analysis_result.transactions)

        categories_details = []
        for transaction in analysis_result.transactions:

            icons = {"food": "🍏", "transport": "🚗", "home": "🏠", "entertainment": "🎉", "health": "💊", "other": "📦"}
            icon = icons.get(transaction.category, "💰")

            # Локализуем название категории (gettext вернет перевод, если он есть в .mo файле)
            localized_category = _(transaction.category)

            items_lines = []
            for item in transaction.items:
                if item.price > 0:
                    items_lines.append(f"  • {item.name}: <b>{item.price}</b>")
                else:
                    items_lines.append(f"  • {item.name}")  # Если цена 0.0

            items_str = "\n".join(items_lines)
            categories_details.append(
                f"{icon} <b>{localized_category}</b>: {transaction.amount}\n{items_str}"
            )

        report_chunks = [
            _("✅ <b>Expenses successfully recorded!</b>\n"),
            "\n\n".join(categories_details),
            "\n" + "─" * 20,
            _("📊 A total of ... have been recorded: <b>{total_amount}</b>").format(total_amount=total_receipt_amount)
        ]
        msg_text = "\n".join(report_chunks)

        localized_button_label = _("❌ cancel appointment")

        await bot.send_message(chat_id=chat_id, text=msg_text,
                               reply_markup=get_delete_keyboard(batch_id=message_batch_id,
                                                                button_text=localized_button_label))

    except openai.OpenAIError as net_err:
        logger.warning("Сетевой сбой API OpenAI. Отправляем таску на повтор в Celery.")
        await session.rollback()
        # Пробрасываем базовый класс, чтобы asyncio.run() выкинул его наружу в таску
        raise net_err

    except Exception as e:
        logger.exception("Error processing check for user {user_id}", user_id=db_user_id)

        await session.rollback()

        await bot.send_message(
            chat_id=chat_id,
            text=_("❌ Unfortunately, we couldn't recognize your receipt. Please make sure the photo is clear and try again.")
        )

    finally:
        await session.close()
        await bot_session.close()


