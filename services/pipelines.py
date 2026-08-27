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
from redis.asyncio import Redis

from financial_bot.keyboards.inline import get_delete_keyboard, get_detailed_report
from financial_bot.repositories import save_receipt_to_db, get_user_by_id, get_user_financial_summary
from services.client import ai_service
from services.analysis_cache import FinancialCacheService
from services.schemas import ReceiptListAnalysisSchema, MonthlyAnalysisResponse, WeeklyAnalysisResponse
from services.utils_pipelines import (
    get_isolated_session,
    merge_transactions_by_category,
    CATEGORY_TITLES,
    render_category_tree,
    render_weekly_top,
    render_monthly_tree
)

redis_url = os.getenv("ANALYSIS_CACHE_REDIS")
if not redis_url:
    raise ValueError("CRITICAL: ANALYSIS_CACHE_REDIS environment variable is not set!")

#cache_service = AnalysisCacheService(redis_url=redis_url)


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

        try:
            async with Redis.from_url(redis_url, decode_responses=True, max_connections=5) as task_redis_client:
                cache_service = FinancialCacheService(redis_client=task_redis_client)
                await cache_service.invalidate_user_cache(user_id=db_user_id)
                logger.info("Successfully invalidated cache from Celery task for user: %s", db_user_id)
        except Exception as e:

            logger.error("Non-critical error: Failed to invalidate cache in Celery task: %s", e)


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
        # 1. ПЫТАЕМСЯ ВЗЯТЬ ДАННЫЕ ИЗ КЭША REDIS

        async with Redis.from_url(redis_url, decode_responses=True, max_connections=5) as task_redis_client:
            cache_service = FinancialCacheService(redis_client=task_redis_client)
            analysis_result = await cache_service.get_cached_analysis(user.id, days, response_schema)

            if analysis_result:
                logger.info("🚀 [CACHE HIT] OpenAI report successfully retrieved from cache for user. {}".format(user.id))
            else:
                logger.info("⏳ [CACHE MISS] There is no cache. We are sending a heavy request to OpenAI for the user. {}".format(user.id))

                analysis_result = await ai_service.analysis_financial(
                    summary_data=data,
                    response_schema=response_schema,
                    days=days,
                    actual_days=actual_days,
                    locale=locale
                )

                await cache_service.set_analysis_cache(user.id, days, analysis_result)


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