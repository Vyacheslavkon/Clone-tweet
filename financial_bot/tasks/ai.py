import asyncio

import openai
from dotenv import load_dotenv
from loguru import logger

from services.celery_app import app
from services.pipelines import async_process_receipt, process_analysis_financial, process_test_analysis_financial

load_dotenv()

celery_app = app


@celery_app.task(name="financial_bot.ai.process_receipt_task", rate_limit="2/s")
def process_receipt_task(
    chat_id: int, db_user_id: int, locale: str, image_bytes: bytes
):

    asyncio.run(async_process_receipt(chat_id, db_user_id, locale, image_bytes))


# @celery_app.task(name="financial_bot.ai.process_expense_task", rate_limit="2/s")
# def process_expense_task(chat_id: int, db_user_id: int, locale: str, voice_bytes: bytes):
#
#     asyncio.run(async_process_receipt(chat_id, db_user_id, locale, voice_bytes))


@celery_app.task(name="financial_bot.ai.process_expense_task", bind=True, max_retries=3)
def process_expense_task(
    self, chat_id: int, db_user_id: int, locale: str, voice_bytes: bytes
):

    try:
        result = asyncio.run(
            async_process_receipt(chat_id, db_user_id, locale, voice_bytes)
        )

        logger.info(
            "Successfully finished process_expense_task for user_id={user_id}",
            user_id=db_user_id,
        )
        return result

    except openai.OpenAIError as exc:

        current_retry = self.request.retries + 1

        logger.warning(
            "OpenAI API failure. Retry attempt {retry}/3. Error: {error_msg}",
            retry=current_retry,
            error_msg=str(exc),
        )


        countdown = 2**self.request.retries


        raise self.retry(exc=exc, countdown=countdown)

    except Exception as e:
        logger.error("Critical unhandled error in the task: {error}", error=e)
        raise e



@celery_app.task(name="financial_bot.ai.process_analysis_expense_task", bind=True, max_retries=3)
def process_analysis_expense_task(
    self, chat_id: int,  locale: str, data: dict, user_id: int, days: int, actual_days: int
):

    try:
        result = asyncio.run(
           process_test_analysis_financial(locale, data, chat_id, days, actual_days)
        )# test

        logger.info(
            "Successfully finished process_expense_analysis_task for user_id={user_id}",
            user_id=user_id,
        )
        return result

    except openai.OpenAIError as exc:

        current_retry = self.request.retries + 1

        logger.warning(
            "OpenAI API failure. Retry attempt {retry}/3. Error: {error_msg}",
            retry=current_retry,
            error_msg=str(exc),
        )


        countdown = 2**self.request.retries


        raise self.retry(exc=exc, countdown=countdown)

    except Exception as e:
        logger.error("Critical unhandled error in the task: {error}", error=e)
        raise e