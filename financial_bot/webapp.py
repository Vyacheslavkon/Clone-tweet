import asyncio
import os
import secrets
from contextlib import asynccontextmanager

from aiogram.exceptions import TelegramNetworkError
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request
from loguru import logger

from financial_bot.bootstrap import build_runtime
from logger_config import setup_logging

WEBHOOK_BASE_URL = os.environ["WEBHOOK_BASE_URL"]
WEBHOOK_PATH = os.environ["WEBHOOK_PATH"]
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

async def register_webhook(bot, url: str, secret: str) -> None:
    delay = 2
    while True:
        try:
            await bot.set_webhook(
                url=url,
                secret_token=secret,
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=False,
            )
            logger.info("Webhook registered: {url}", url=url)
            return
        except TelegramNetworkError as e:
            logger.warning("set_webhook failed ({err}), retry in {d}s", err=e, d=delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)


def _log_task_result(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception():
        logger.error("Webhook registration failed: {e}", e=task.exception())


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    rt = build_runtime()
    app.state.rt = rt

    app.state.webhook_task = asyncio.create_task(
        register_webhook(rt.bot, f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}", WEBHOOK_SECRET)
    )

    app.state.webhook_task.add_done_callback(_log_task_result)

    rt.scheduler.start()
    try:
        yield
    finally:
        app.state.webhook_task.cancel()
        try:
            await app.state.webhook_task
        except asyncio.CancelledError:
            pass
        rt.scheduler.shutdown(wait=False)
        await rt.close()


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     setup_logging()
#     rt = build_runtime()
#     app.state.rt = rt
#
#     await rt.bot.set_webhook(
#         url=f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}",
#         secret_token=WEBHOOK_SECRET,
#         allowed_updates=["message", "callback_query"],
#         drop_pending_updates=False,
#     )
#     logger.info("Webhook registered: {url}", url=f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}")
#
#     rt.scheduler.start()
#     try:
#         yield
#     finally:
#         rt.scheduler.shutdown(wait=False)
#         await rt.close()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.post(WEBHOOK_PATH)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    if not secrets.compare_digest(
        x_telegram_bot_api_secret_token or "", WEBHOOK_SECRET
    ):
        raise HTTPException(status_code=403)

    rt = request.app.state.rt
    update = Update.model_validate(await request.json(), context={"bot": rt.bot})

    try:
        await rt.dp.feed_update(rt.bot, update)
    except Exception:  # noqa: PIE786 otherwise Telegram retries a poison update forever
        logger.exception(
            "Unhandled error while processing update_id={uid}", uid=update.update_id
        )

    return {"ok": True}



@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
