import asyncio

from loguru import logger

from financial_bot.bootstrap import build_runtime
from logger_config import setup_logging


async def main() -> None:
    setup_logging()
    rt = build_runtime()
    try:
        rt.scheduler.start()
        await rt.dp.start_polling(rt.bot)
    except Exception as e:  # noqa: PIE786 - top-level boundary
        logger.critical("Critical error in bot core: {error}", error=e, exc_info=True)
    finally:
        rt.scheduler.shutdown(wait=False)
        await rt.close()


if __name__ == "__main__":
    asyncio.run(main())
