import gettext
import os
import uuid
from pathlib import Path
import openai
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.keyboards.inline import get_delete_keyboard, get_detailed_report
from financial_bot.highload_bot import get_shared_bot
from financial_bot.repositories import save_receipt_to_db, get_user_by_id, get_user_financial_summary
from services.client import ai_service
from services.analysis_cache import get_worker_cache_service
from services.schemas import ReceiptListAnalysisSchema, MonthlyAnalysisResponse, WeeklyAnalysisResponse
from services.utils_pipelines import (
    #get_isolated_session,
    merge_transactions_by_category,
    render_receipt_report,
    get_translator,
    _reply,
    render_analysis_report
)
from core.db_worker import get_isolated_session


redis_url = os.getenv("ANALYSIS_CACHE_REDIS")
if not redis_url:
    raise ValueError("CRITICAL: ANALYSIS_CACHE_REDIS environment variable is not set!")


async def process_test_1_analysis_financial(
        user_id: int,
        chat_id: int,
        days: int,
):
    bot = get_shared_bot()
    session = get_isolated_session()

    try:
        user = await get_user_by_id(session, user_id)
        locale = user.language_code
        data = await get_user_financial_summary(session, user.id, days, user)
    finally:
        await session.close()

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

    response_schema = WeeklyAnalysisResponse if days == 7 else MonthlyAnalysisResponse

    cache_service = get_worker_cache_service()

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
    #new solution
    try:
        msg_text = render_analysis_report(data, analysis_result, days, _)
        await bot.send_message(
            chat_id=chat_id,
            text=msg_text,
            reply_markup=get_detailed_report(days, _)
    )
    except TelegramAPIError as tg_err:
        logger.error(f"Error sending analytics to Telegram for chat_id {chat_id}: {tg_err}")

    except Exception as e:
        logger.exception(f"Critical error rendering/sending AI analytics for chat_id {chat_id}: {e}")

        try:
            await bot.send_message(chat_id=chat_id, text=_("❌ <b>An error occurred.</b>\nPlease try again later."))

        except Exception:
            pass



async def async_process_receipt(
        chat_id: int,
        db_user_id: int,
        locale: str,
        voice_file_path: str,
        status_message_id: int = None
):

    _ = get_translator(locale)
    bot = get_shared_bot()
    session: AsyncSession | None = None

    try:

        if not os.path.exists(voice_file_path):
            raise FileNotFoundError("Audio file missing: {}".format(voice_file_path))

        with open(voice_file_path, "rb") as f:
            voice_bytes = f.read()


        analysis_result = await ai_service.process_voice_message(
            voice_bytes=voice_bytes,
            response_schema=ReceiptListAnalysisSchema,
            locale=locale,
        )


        if not analysis_result.is_shopping_related:
            joke_text = analysis_result.error_message or _("Unable to recognize the purchase amount.")

            await _reply(bot, chat_id, status_message_id, f"❌ {joke_text}")

            return {"status": "cancelled", "message": joke_text}

        analysis_result.transactions = [t for t in analysis_result.transactions if t.amount > 0]

        if not analysis_result.transactions:
            await _reply(bot, chat_id, status_message_id, _("❌ No transactions found to save."))

            return {"status": "cancelled", "message": "Empty transactions list"}

        final_analysis_result = merge_transactions_by_category(analysis_result)
        message_batch_id = str(uuid.uuid4())

        session = get_isolated_session()

        await save_receipt_to_db(
            session=session,
            user_id=db_user_id,
            analysis_result=final_analysis_result,
            photo_url=None,
            raw_text=analysis_result.model_dump_json(),
            batch_id=message_batch_id,
        )

        await session.commit()


        try:
            cache_service = get_worker_cache_service()
            await cache_service.invalidate_user_cache(user_id=db_user_id)
        except Exception as cache_err:
            logger.error("Failed to invalidate cache: {error}", error=cache_err)


        msg_text, localized_button_label = render_receipt_report(analysis_result, _)

        await _reply(
            bot, chat_id, status_message_id, msg_text,
            reply_markup=get_delete_keyboard(batch_id=message_batch_id, button_text=localized_button_label),
        )
        return {"status": "success", "batch_id": message_batch_id}


    except openai.OpenAIError as net_err:
        logger.warning("OpenAI API network failure. Retrying the task in Celery.")
        if session:
            await session.rollback()
        raise

    except Exception:
        logger.exception("Error processing check for user {user_id}", user_id=db_user_id)
        if session:
            await session.rollback()

        await _reply(
            bot, chat_id, status_message_id,
            _("❌ Unfortunately, we couldn't recognize your receipt. Please try again."),
        )
        raise


    finally:
        if session:
            await session.close()



async def notify_user_final_failure(chat_id: int, status_message_id: int, locale: str, db_user_id: int):

    _ = get_translator(locale)
    bot = get_shared_bot()

    text = _("❌ We couldn't process your receipt after several attempts. Please try again later.")

    try:
        if status_message_id:
            await bot.edit_message_text(chat_id=chat_id, message_id=status_message_id, text=text)
        else:
            await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logger.error(
            "Failed to notify user {user_id} about final failure: {error}",
            user_id=db_user_id, error=e,
        )