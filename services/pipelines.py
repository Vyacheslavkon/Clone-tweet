import gettext
import os
import uuid
from collections import Counter
from pathlib import Path

import openai
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from loguru import logger

from financial_bot.keyboards.inline import get_delete_keyboard, get_detailed_report
from financial_bot.repositories import save_receipt_to_db, get_user_by_id, get_user_financial_summary
from services.client import ai_service
from services.schemas import ReceiptListAnalysisSchema, MonthlyAnalysisResponse, WeeklyAnalysisResponse
from services.utils_pipelines import (
    get_isolated_session,
    merge_transactions_by_category,
    CATEGORY_TITLES,
    render_category_tree,
    render_weekly_top,
    render_monthly_tree
)


# for check.

# ocr = RapidOCR()
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


# async def async_process_receipt(chat_id: int, db_user_id: int,
#                                 locale: str, voice_bytes: bytes):
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
#
#         analysis_result: ReceiptListAnalysisSchema = await ai_service.process_voice_message(
#                     voice_bytes=voice_bytes,
#                     response_schema=ReceiptListAnalysisSchema,
#                     locale=locale
#
#                 )
#
#         if not analysis_result.is_shopping_related:
#             joke_text = analysis_result.error_message or _("Unable to recognize the purchase amount.")
#
#             await bot.send_message(chat_id=chat_id, text=f"❌ {joke_text}")
#             logger.info("Обработка отменена ИИ для юзера %s. Шутка: %s", db_user_id, joke_text)
#             return {"status": "cancelled", "message": joke_text}
#
#
#         valid_transactions = [t for t in analysis_result.transactions if t.amount > 0]
#
#         analysis_result.transactions = valid_transactions
#
#         if not analysis_result.transactions:
#             await bot.send_message(chat_id=chat_id, text=_("❌ No transactions found to save."))
#             return {"status": "cancelled", "message": "Empty transactions list"}
#
#
#         final_analysis_result = merge_transactions_by_category(analysis_result)
#
#         message_batch_id = str(uuid.uuid4())
#
#         await save_receipt_to_db(
#             session=session,
#             user_id=db_user_id,
#             analysis_result=final_analysis_result,
#             photo_url=None,
#             batch_id=message_batch_id,
#             raw_text=analysis_result.model_dump_json()
#         )
#
#
#         total_receipt_amount = sum(transaction.amount for transaction in analysis_result.transactions)
#
#         categories_details = []
#         for transaction in analysis_result.transactions:
#
#             icons = {"food": "🍏", "transport": "🚗", "home": "🏠", "entertainment": "🎉", "health": "💊", "other": "📦"}
#             icon = icons.get(transaction.category, "💰")
#
#             # Локализуем название категории (gettext вернет перевод, если он есть в .mo файле)
#             localized_category = _(transaction.category)
#
#             items_lines = []
#             for item in transaction.items:
#                 if item.price > 0:
#                     items_lines.append(f"  • {item.name}: <b>{item.price}</b>")
#                 else:
#                     items_lines.append(f"  • {item.name}")  # Если цена 0.0
#
#             items_str = "\n".join(items_lines)
#             categories_details.append(
#                 f"{icon} <b>{localized_category}</b>: {transaction.amount}\n{items_str}"
#             )
#
#         report_chunks = [
#             _("✅ <b>Expenses successfully recorded!</b>\n"),
#             "\n\n".join(categories_details),
#             "\n" + "─" * 20,
#             _("📊 A total of ... have been recorded: <b>{total_amount}</b>").format(total_amount=total_receipt_amount)
#         ]
#         msg_text = "\n".join(report_chunks)
#
#         localized_button_label = _("❌ cancel appointment")
#
#         await bot.send_message(chat_id=chat_id, text=msg_text,
#                                reply_markup=get_delete_keyboard(batch_id=message_batch_id,
#                                                                 button_text=localized_button_label))
#
#     except openai.OpenAIError as net_err:
#         logger.warning("Сетевой сбой API OpenAI. Отправляем таску на повтор в Celery.")
#         await session.rollback()
#         # Пробрасываем базовый класс, чтобы asyncio.run() выкинул его наружу в таску
#         raise net_err
#
#     except Exception as e:
#         logger.exception("Error processing check for user {user_id}", user_id=db_user_id)
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


async def async_process_receipt(
    chat_id: int, db_user_id: int, locale: str, voice_bytes: bytes
):

    locales_dir = Path(__file__).resolve().parent.parent / "financial_bot" / "locales"

    try:
        lang = gettext.translation(
            domain="messages",
            localedir=str(locales_dir),  # gettext требует строку, а не объект Path
            languages=[locale],
            fallback=True,
        )
    except Exception as e:  # noqa: PIE786
        logger.error(
            "Не удалось загрузить локализацию из {locales}: {error}",
            locales=locales_dir,
            error=e,
        )

        lang = gettext.NullTranslations()

    _ = lang.gettext

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("The BOT_TOKEN environment variable is not set!")

    bot_session = AiohttpSession()
    bot = Bot(
        token=token,
        session=bot_session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    session = get_isolated_session()
    try:

        analysis_result: ReceiptListAnalysisSchema = (
            await ai_service.process_voice_message(
                voice_bytes=voice_bytes,
                response_schema=ReceiptListAnalysisSchema,
                locale=locale,
            )
        )

        if not analysis_result.is_shopping_related:
            joke_text = analysis_result.error_message or _(
                "Unable to recognize the purchase amount."
            )

            await bot.send_message(chat_id=chat_id, text=f"❌ {joke_text}")
            logger.info(
                "Processing cancelled by AI for user %s. Joke: %s",
                db_user_id,
                joke_text,
            )
            return {"status": "cancelled", "message": joke_text}

        valid_transactions = [t for t in analysis_result.transactions if t.amount > 0]

        analysis_result.transactions = valid_transactions

        if not analysis_result.transactions:
            await bot.send_message(
                chat_id=chat_id, text=_("❌ No transactions found to save.")
            )
            return {"status": "cancelled", "message": "Empty transactions list"}

        final_analysis_result = merge_transactions_by_category(analysis_result)

        message_batch_id = str(uuid.uuid4())

        await save_receipt_to_db(
            session=session,
            user_id=db_user_id,
            analysis_result=final_analysis_result,
            photo_url=None,
            raw_text=analysis_result.model_dump_json(),
            batch_id=message_batch_id,
        )

        income_txs = [t for t in analysis_result.transactions if t.type == "income"]
        expense_txs = [t for t in analysis_result.transactions if t.type == "expense"]

        total_income = sum(t.amount for t in income_txs)
        total_expense = sum(t.amount for t in expense_txs)

        icons = {
            "food": "🍏",
            "transport": "🚗",
            "home": "🏠",
            "entertainment": "🎉",
            "health": "💊",
            "other": "📦",
            "salary": "💼",
            "bonus": "📈",
            "gift": "🎁",
            "deal": "🤝",
        }

        report_chunks = [_("✅ <b>Operations successfully recorded!</b>\n")]

        if income_txs:
            report_chunks.append(_("💰 <b>Received Income:</b>"))
            income_details = []
            for tx in income_txs:
                icon = icons.get(tx.category, "💵")
                description = tx.description or ""
                category = description.capitalize()
                localized_category = _(category)

                items_lines = []
                for item in tx.items:
                    items_lines.append(f"  • {item.name}: <b>{item.price}</b>")
                items_str = "\n" + "\n".join(items_lines) if items_lines else ""

                # desc_str = f" ({tx.description})" if tx.description else ""
                # income_details.append(f"{icon} {localized_category}{desc_str}: <b>+{tx.amount}</b>{items_str}")

                # desc_str = f" ({tx.description})" if tx.description else ""
                income_details.append(
                    f"{icon} {localized_category}: <b>+{tx.amount}</b>{items_str}"
                )

            report_chunks.append("\n".join(income_details))

        if income_txs and expense_txs:
            report_chunks.append(" ")

        if expense_txs:
            report_chunks.append(_("📉 <b>Spent Expenses:</b>"))
            expense_details = []
            for tx in expense_txs:
                icon = icons.get(tx.category, "📦")
                category = tx.category.capitalize()
                # localized_category = _(tx.category)
                localized_category = _(category)

                items_lines = []
                for item in tx.items:
                    if item.price > 0:
                        items_lines.append(f"  • {item.name}: <b>{item.price}</b>")
                    else:
                        items_lines.append(f"  • {item.name}")

                items_str = "\n".join(items_lines)

                expense_details.append(
                    _("{icon} {category}: <b>-{amount}</b>\n{items}").format(
                        icon=icon,
                        category=localized_category,
                        amount=tx.amount,
                        items=items_str,
                    )
                )
            report_chunks.append("\n".join(expense_details))

        report_chunks.append("\n" + "─" * 20)

        meta_lines = []
        if total_income > 0:
            meta_lines.append(
                _("Total Income: <b>+{total_amount}</b>").format(
                    total_amount=total_income
                )
            )
        if total_expense > 0:
            meta_lines.append(
                _("Total Expenses: <b>-{total_amount}</b>").format(
                    total_amount=total_expense
                )
            )

        report_chunks.append("\n".join(meta_lines))
        msg_text = "\n".join(report_chunks)

        if income_txs and not expense_txs:
            localized_button_label = _("❌ cancel income")
        elif expense_txs and not income_txs:
            localized_button_label = _("❌ cancel expense")
        else:
            localized_button_label = _("❌ cancel operation")

        await bot.send_message(
            chat_id=chat_id,
            text=msg_text,
            reply_markup=get_delete_keyboard(
                batch_id=message_batch_id, button_text=localized_button_label
            ),
        )

    except openai.OpenAIError as net_err:
        logger.warning("OpenAI API network failure. Retrying the task in Celery.")
        await session.rollback()

        raise net_err

    except Exception:  # noqa: PIE786
        logger.exception(
            "Error processing check for user {user_id}", user_id=db_user_id
        )

        await session.rollback()

        await bot.send_message(
            chat_id=chat_id,
            text=_(
                "❌ Unfortunately, we couldn't recognize your receipt. Please make sure the photo is clear and try again."
            ),
        )

    finally:
        await session.close()
        await bot_session.close()




async def process_test_analysis_financial(
        locale: str,
        data: dict,
        chat_id: int,
        days: int,
        actual_days: int
):
    locales_dir = Path(__file__).resolve().parent.parent / "financial_bot" / "locales"

    try:
        lang = gettext.translation(
            domain="messages",
            localedir=str(locales_dir),
            languages=[locale],
            fallback=True,
        )
    except Exception as e:  # noqa: PIE786
        logger.error(
            "Не удалось загрузить локализацию из {locales}: {error}",
            locales=locales_dir,
            error=e,
        )
        lang = gettext.NullTranslations()

    _ = lang.gettext

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("The BOT_TOKEN environment variable is not set!")

    bot_session = AiohttpSession()
    bot = Bot(
        token=token,
        session=bot_session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    try:
        # Автоматический выбор схемы на основе переданных дней
        response_schema = WeeklyAnalysisResponse if days == 7 else MonthlyAnalysisResponse

        analysis_result = await ai_service.analysis_financial(
            summary_data=data,
            response_schema=response_schema,
            days=days,
            actual_days=actual_days
        )

        currency = data.get("user_config", {}).get("currency", "руб.")

        # Шапка отчета (общая для недели и месяца)
        lines = [
            _("📊 <b>Comprehensive financial analysis</b>\n"),
            _("💰 <b>Total Income:</b> {income} {curr}").format(
                income=data.get('total_income', 0.0), curr=currency),
            _("🛒 <b>Total Expense:</b> {expense} {curr}").format(
                expense=data.get('total_amount', 0.0), curr=currency),
            _("⚖️ <b>Net Balance:</b> {balance} {curr}\n").format(
                balance=data.get('net_balance', 0.0), curr=currency),
        ]

        budget_status = getattr(analysis_result, "budget_status", None) or getattr(analysis_result,
                                                                                   "weekly_balance_status", None)
        if budget_status:
            lines.append(_("📈 <b>Budget status:</b> {status}").format(status=budget_status))

        budget_usage_percent = getattr(analysis_result, "budget_usage_percent", None)
        if budget_usage_percent is not None:
            lines.append(_("📊 <b>Budget used:</b> {percent}%\n").format(percent=round(budget_usage_percent, 1)))
        else:
            lines.append("")

        lines.extend([
            "{summary}\n".format(summary=analysis_result.summary),
        ])

        # === БЛОК СТРУКТУРЫ ТРАТ (Classified Items) ===
        # Разделяем вывод товаров по типам важности, как они классифицированы моделью в classified_items
        essentials = [item for item in analysis_result.classified_items if item.expense_type == "essential"]
        discretionary = [item for item in analysis_result.classified_items if item.expense_type == "discretionary"]

        lines.append(_("🎯 <b>Categorizing top expenses by importance:</b>"))

        if essentials:
            lines.append(_("\n🟢 <u>Necessary :</u>"))
            for item in essentials:
                cat = CATEGORY_TITLES.get(item.original_category,
                                          _("📦 {org_cat}").format(org_cat=item.original_category))
                lines.append(_(" • <b>{el}</b> ({cat})").format(el=item.name, cat=cat))

        if discretionary:
            lines.append(_("\n🟡 <u>Secondary :</u>"))
            for item in discretionary:
                cat = CATEGORY_TITLES.get(item.original_category, f"📦 {item.original_category}")
                lines.append(_(" • <b>{el}</b> ({cat})").format(el=item.name, cat=cat))

        # === БЛОК УМНЫХ РЕКОМЕНДАЦИЙ (Разделение вывода для недели и месяца) ===
        if analysis_result.recommendations:
            lines.append(_("\n💡 <b>Optimization recommendations:</b>"))

            for i, rec in enumerate(analysis_result.recommendations, 1):
                if days == 7:
                    # Недельный вывод (использует target_item)
                    lines.append(
                        _("\n{num}. <b>{target}</b>\n"
                          "└ {reason}\n"
                          "└ <i>Possible savings: {saving}</i>").format(
                            num=i,
                            target=getattr(rec, "target_item", _("Optimization")),
                            reason=rec.reason,
                            saving=rec.potential_saving
                        )
                    )
                else:
                    # Месячный вывод (использует target_habit_pattern и frequency_metric)
                    lines.append(
                        _("\n{num}. <b>{target}</b> — <b>{freq}</b>\n"
                          "└ {reason}\n"
                          "└ <i>Possible savings: {saving}</i>").format(
                            num=i,
                            target=getattr(rec, "target_habit_pattern", _("Optimization")),
                            freq=getattr(rec, "frequency_metric", ""),
                            reason=rec.reason,
                            saving=rec.potential_saving
                        )
                    )

        msg_text = "\n".join(lines)

        await bot.send_message(
            chat_id=chat_id,
            text=msg_text,
            parse_mode=ParseMode.HTML
        )

    except TelegramAPIError as tg_err:
        logger.error("Ошибка отправки аналитики в Telegram для chat_id {}: {}".format(chat_id, tg_err))
    except Exception as e:  # noqa
        logger.exception("Критическая ошибка при генерации AI-аналитики для chat_id {}".format(chat_id))
        try:
            error_msg = _("❌ <b>An error occurred while generating the report.</b>\nPlease try again later.")
            await bot.send_message(
                chat_id=chat_id,
                text=error_msg,
                parse_mode=ParseMode.HTML
            )
        except Exception as send_err:
            logger.error("Не удалось отправить сообщение об ошибке пользователю: {}".format(send_err))
    finally:
        await bot_session.close()





async def process_test_1_analysis_financial(
        user_id: int,
        chat_id: int,
        days: int,
):
    session = get_isolated_session()

    user = await get_user_by_id(session, user_id)
    locale = user.language_code

    locales_dir = Path(__file__).resolve().parent.parent / "financial_bot" / "locales"

    try:
        lang = gettext.translation(
            domain="messages",
            localedir=str(locales_dir),
            languages=[locale],
            fallback=True,
        )
    except Exception as e:  # noqa: PIE786
        logger.error(
            "Не удалось загрузить локализацию из {locales}: {error}",
            locales=locales_dir,
            error=e,
        )
        lang = gettext.NullTranslations()

    _ = lang.gettext

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("The BOT_TOKEN environment variable is not set!")

    bot_session = AiohttpSession()
    bot = Bot(
        token=token,
        session=bot_session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


    data = await get_user_financial_summary(session, user.id, days, user)

    if not data:

        msg_text = _("You don't have enough transactions for analysis yet. We need more data! 🧾")
        await bot.send_message(chat_id=chat_id,
                               text=msg_text,
                               parse_mode=ParseMode.HTML
                             )

        return

    min_items_required = 5 if days == 7 else 12

    actual_items_count = len(data.get("top_items", []))

    if actual_items_count < min_items_required:

        msg_text =  _("🧾 *Not enough data for deep analysis!* \n"
              "You have too few expenses logged for this period. "
              "Keep logging your expenditures via voice, and I will prepare a smart audit soon! 🤖")

        await bot.send_message(
            chat_id=chat_id,
            text=msg_text,
            parse_mode=ParseMode.HTML
        )

        return

    actual_days = data["days_period"]

    try:

        response_schema = WeeklyAnalysisResponse if days == 7 else MonthlyAnalysisResponse

        analysis_result = await ai_service.analysis_financial(
            summary_data=data,
            response_schema=response_schema,
            days=days,
            actual_days=actual_days,
            locale=locale
        )

        currency = data.get("user_config", {}).get("currency", "руб.")

        # Шапка отчета (общая для недели и месяца)
        lines = [
            _("📊 <b>Comprehensive financial analysis</b>\n"),
            _("💰 <b>Total Income:</b> {income} {curr}").format(
                income=data.get('total_income', 0.0), curr=currency),
            _("🛒 <b>Total Expense:</b> {expense} {curr}").format(
                expense=data.get('total_amount', 0.0), curr=currency),
            _("⚖️ <b>Net Balance:</b> {balance} {curr}\n").format(
                balance=data.get('net_balance', 0.0), curr=currency),
        ]

        budget_status = getattr(analysis_result, "budget_status", None) or getattr(analysis_result,
                                                                                   "weekly_balance_status", None)
        if budget_status:
            lines.append(_("📈 <b>Budget status:</b> {status}").format(status=budget_status))

        budget_usage_percent = getattr(analysis_result, "budget_usage_percent", None)
        if budget_usage_percent is not None:
            lines.append(_("📊 <b>Budget used:</b> {percent}%\n").format(percent=round(budget_usage_percent, 1)))
        else:
            lines.append("")

        lines.extend([
            "{summary}\n".format(summary=analysis_result.summary),
        ])


        lines.append(_("🎯 <b>Categorizing top expenses by importance:</b>"))

        if days == 7:
            lines.extend(render_weekly_top(data, _))

        else:

            lines.extend(render_monthly_tree(data, _))


        # === БЛОК УМНЫХ РЕКОМЕНДАЦИЙ (Разделение вывода для недели и месяца) ===
        if analysis_result.recommendations:
            lines.append(_("\n💡 <b>Optimization recommendations:</b>"))

            for i, rec in enumerate(analysis_result.recommendations, 1):
                if days == 7:
                    # Недельный вывод (использует target_item)
                    lines.append(
                        _("\n{num}. <b>{target}</b>\n"
                          "└ {reason}\n"
                          "└ <i>Possible savings: {saving}</i>").format(
                            num=i,
                            target=getattr(rec, "target_item", _("Optimization")),
                            reason=rec.reason,
                            saving=rec.potential_saving
                        )
                    )
                else:
                    # Месячный вывод (использует target_habit_pattern и frequency_metric)
                    lines.append(
                        _("\n{num}. <b>{target}</b> — <b>{freq}</b>\n"
                          "└ {reason}\n"
                          "└ <i>Possible savings: {saving}</i>").format(
                            num=i,
                            target=getattr(rec, "target_habit_pattern", _("Optimization")),
                            freq=getattr(rec, "frequency_metric", ""),
                            reason=rec.reason,
                            saving=rec.potential_saving
                        )
                    )

        msg_text = "\n".join(lines)

        await bot.send_message(
            chat_id=chat_id,
            text=msg_text,
            parse_mode=ParseMode.HTML,
            reply_markup= get_detailed_report(days, _)
        )

    except TelegramAPIError as tg_err:
        logger.error("Ошибка отправки аналитики в Telegram для chat_id {}: {}".format(chat_id, tg_err))
    except Exception as e:  # noqa
        logger.exception("Критическая ошибка при генерации AI-аналитики для chat_id {}".format(chat_id))
        try:
            error_msg = _("❌ <b>An error occurred while generating the report.</b>\nPlease try again later.")
            await bot.send_message(
                chat_id=chat_id,
                text=error_msg,
                parse_mode=ParseMode.HTML
            )
        except Exception as send_err:
            logger.error("Не удалось отправить сообщение об ошибке пользователю: {}".format(send_err))
    finally:
        await bot_session.close()