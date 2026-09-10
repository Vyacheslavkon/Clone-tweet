import asyncio
import os

import openai
from dotenv import load_dotenv
from loguru import logger

from services.celery_app import app
from services.pipelines import (async_process_receipt,

                                process_test_1_analysis_financial,
                                notify_user_final_failure)

from services.worker_loop import run_in_worker_loop

load_dotenv()

celery_app = app


@celery_app.task(name="financial_bot.ai.process_receipt_task", rate_limit="2/s")
def process_receipt_task(
    chat_id: int, db_user_id: int, locale: str, image_bytes: bytes
):

    run_in_worker_loop(async_process_receipt(chat_id, db_user_id, locale, image_bytes))


@celery_app.task(name="financial_bot.ai.process_expense_task", bind=True, max_retries=3)
def process_expense_task(
    self, chat_id: int, db_user_id: int, locale: str, voice_file_path: str, status_message_id: int
):
    should_cleanup = True

    try:
        result = run_in_worker_loop(
            async_process_receipt(chat_id, db_user_id, locale, voice_file_path, status_message_id)
        )

        logger.info(
            "Successfully finished process_expense_task for user_id={user_id}",
            user_id=db_user_id,
        )
        return result


    except openai.OpenAIError as exc:
        # Внимание: self.retry() в eager-режиме рекурсивно вызывает всю функцию
        # заново. should_cleanup корректно живёт в своём стек-фрейме на каждом
        # уровне рекурсии — файл удаляется только в САМОМ глубоком вызове,
        # когда retries достигает max_retries.

        current_retry = self.request.retries + 1

        if self.request.retries < self.max_retries:
            should_cleanup = False
            logger.warning(
                "OpenAI API failure. Retry attempt {retry}/{max}. Error: {error_msg}",
                retry=current_retry,
                max=self.max_retries,
                error_msg=str(exc),
            )

            countdown = 2**self.request.retries
            raise self.retry(exc=exc, countdown=countdown)

        logger.error(
            "Max retries exceeded for user_id={user_id}, chat_id={chat_id}. Giving up.",
            user_id=db_user_id, chat_id=chat_id,
        )
        run_in_worker_loop(notify_user_final_failure(chat_id, status_message_id, locale, db_user_id))
        raise



    except Exception:
        logger.exception("Critical unhandled error in the task for user_id={user_id}", user_id=db_user_id)
        raise

    finally:
        if should_cleanup and voice_file_path and os.path.exists(voice_file_path):
            try:
                os.remove(voice_file_path)
            except OSError as cleanup_err:
                logger.warning(
                    "Failed to remove temp audio file {path}: {error}",
                    path=voice_file_path, error=cleanup_err,
                )



@celery_app.task(name="financial_bot.ai.process_analysis_expense_task", bind=True, max_retries=3)
def process_analysis_expense_task(
    self,  user_id: int, chat_id: int, days: int
):

    try:
        result = run_in_worker_loop(
           process_test_1_analysis_financial(user_id, chat_id, days)
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