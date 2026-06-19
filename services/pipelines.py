import os
import io
import gettext
import tempfile
import logging

from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram import Bot
from loguru import logger
from pathlib import Path

from services.client import ai_service
from services.schemas import ReceiptAnalysisSchema
from financial_bot.repositories import save_receipt_to_db
from services.utils_pipelines import get_isolated_session, merge_ocr_blocks_to_text, decode_visual_translit
from rapidocr_onnxruntime import RapidOCR

ocr = RapidOCR()
    # det_model_path="/application/ocr_models/ch_PP-OCRv4_det_infer.onnx",
    #
    # # Указываем модель распознавания текста (latin)
    # rec_model_path="/application/ocr_models/ch_PP-OCRv4_rec_infer.onnx",
    #
    # # Путь к словарю символов
    # rec_keys_path="/application/ocr_models/multilingual_dict.txt",

#)



logging.getLogger("ppocr").setLevel(logging.WARNING)

async def async_process_receipt(chat_id: int, db_user_id: int,
                                locale: str, image_bytes: bytes):

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
        #file_io = await bot.download_file(file_path) #(to improve productivity)

        # Создаем временный файл в системной папке /tmp (или AppData в Windows)
        # suffix=".jpg" нужен, чтобы PaddleOCR понимал формат файла
        with tempfile.NamedTemporaryFile(delete=True, suffix=".jpg") as temp_file:
            # 1. Записываем байты во временный файл
            temp_file.write(image_bytes)
            temp_file.flush()  # Принудительно сохраняем данные на диск

            # Получаем абсолютный путь к файлу (например, '/tmp/tmp_abc123.jpg')
            file_path = temp_file.name

            logger.info(f"Начало обработки чека для пользователя {db_user_id}")
            logger.info("Path for func: {}".format(file_path))

            result, elapse_list = ocr(file_path)
            logger.info("Data for func: {}".format(result))

        if not result or not result[0]:
            logger.warning("PaddleOCR не нашел текст на изображении")
            return {"status": "error", "message": "No text found"}

        logger.info("Type data: {}; Data for func: {}".format(type(result),result))
        # clear_text = clean_ocr_text(result)
        # text = merge_ocr_blocks_to_text(clear_text)
        text = merge_ocr_blocks_to_text(result)
        clear_text = decode_visual_translit(text)
        logger.info("Text for AI: {}".format(clear_text))

        analysis_result: ReceiptAnalysisSchema = await ai_service.process_receipt(
                    text=clear_text,
                    response_schema=ReceiptAnalysisSchema,
                    locale=locale

                )

        await save_receipt_to_db(
            session=session,
            user_id=db_user_id,
            analysis_result=analysis_result,
            photo_url=None,
            raw_text=analysis_result.model_dump_json()
        )

        msg_text = _((
            f"✅ <b>The check has been processed successfully!</b>\n\n"
            f"🏬 Description: {analysis_result.description or 'Неизвестно'}\n"
            f"💰 Amount: {analysis_result.amount} {analysis_result.currency}\n"
            f"🗂 Category: {analysis_result.category}\n\n"
            f"🧾 Positions have been added to your detailed statistics."
        ))
        await bot.send_message(chat_id=chat_id, text=msg_text)

    except Exception as e:
        logger.error(f"Error processing check for user {db_user_id}: {e}", exc_info=True)

        await session.rollback()

        await bot.send_message(
            chat_id=chat_id,
            text=_("❌ Unfortunately, we couldn't recognize your receipt. Please make sure the photo is clear and try again.")
        )

    finally:
        await session.close()
        await bot_session.close()




# async def async_process_receipt(chat_id: int, db_user_id: int, file_id: str, locale: str):
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
#         #file_io = await bot.download_file(file_path) (to improve productivity)
#         file_io = await bot.download(file_id)
#         image_data_url = process_receipt_to_base64(file_io)
#
#
#         analysis_result: ReceiptAnalysisSchema = await ai_service.analyze_image(
#             image_url=image_data_url,
#             response_schema=ReceiptAnalysisSchema,
#             system_prompt=RECEIPT_SYSTEM_PROMPT
#         )
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