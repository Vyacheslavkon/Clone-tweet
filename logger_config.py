import os
import sys

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

log_path = os.getenv("LOG_PATH", "logs")
log_level = os.getenv("LOG_LEVEL", "DEBUG")
rotation = os.getenv("LOG_ROTATION", "50 MB")
retention = os.getenv("LOG_RETENTION", "7 days")


def setup_logging():

    logger.remove()

    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
        "{name}:{function}:{line} - {message}",
        level="DEBUG",
        enqueue=True,
    )

    logger.add(
        f"{log_path}/app.log",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
        "{name}:{function}:{line} - {message}",
        rotation=rotation,
        retention=retention,
        compression="zip",
        enqueue=True,
    )

    logger.add(
        f"{log_path}/errors.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
        "{name}:{function}:{line} - {message}",
        rotation="20 MB",
        retention=retention,
        enqueue=True,
    )
