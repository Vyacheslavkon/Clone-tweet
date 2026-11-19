import logging
import os
import sys

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

log_path = os.getenv("LOG_PATH", "logs")
log_level = os.getenv("LOG_LEVEL", "INFO")
rotation = os.getenv("LOG_ROTATION", "50 MB")
retention = os.getenv("LOG_RETENTION", "7 days")
log_filename = os.getenv("LOG_FILENAME", "app.log")
is_dev = os.getenv("APP_ENV", "dev") == "dev"


def info_only_filter(record):

    return record["level"].no < 40


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame, depth = frame.f_back, depth + 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging():

    logger.remove()

    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
        "{name}:{function}:{line} - {message}",
        level=log_level,
        enqueue=True,
        diagnose=is_dev,
        colorize=True,
    )

    logger.add(
        f"{log_path}/{log_filename}",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
        "{name}:{function}:{line} - {message}",
        filter=info_only_filter,
        rotation=rotation,
        retention=retention,
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )

    logger.add(
        f"{log_path}/errors_{log_filename}.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
        "{name}:{function}:{line} - {message}",
        rotation="20 MB",
        retention=retention,
        enqueue=True,
        backtrace=True,
        diagnose=False,
        serialize=True,
    )

    logger.configure(extra={"component": "app"})

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
