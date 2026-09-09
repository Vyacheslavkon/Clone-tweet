import asyncio
import os
import logging

from loguru import logger

_worker_loop: asyncio.AbstractEventLoop | None = None


def get_worker_loop() -> asyncio.AbstractEventLoop:
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
        logger.info(
            "New worker event loop created: pid=%s, loop_id=%s",
            os.getpid(), id(_worker_loop),
        )
    return _worker_loop


def run_in_worker_loop(coro):
    loop = get_worker_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        _cleanup_pending_tasks(loop)


def _cleanup_pending_tasks(loop: asyncio.AbstractEventLoop) -> None:
    """Защитная сетка: если корутина где-то создала фоновую задачу через
    create_task() и не дождалась её явно, эта задача осталась бы висеть
    в loop между вызовами тасков. Явно отменяем всё незавершённое."""
    pending = {t for t in asyncio.all_tasks(loop=loop) if not t.done()}
    if not pending:
        return

    logger.warning("Found %d unfinished task(s) after run, cancelling.", len(pending))
    for task in pending:
        task.cancel()
    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))


def close_worker_loop() -> None:
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        return

    _cleanup_pending_tasks(_worker_loop)
    _worker_loop.close()
    logger.info("Worker event loop closed: pid=%s", os.getpid())