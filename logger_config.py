import os
import sys
import logging

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

log_path = os.getenv("LOG_PATH", "logs")
log_level = os.getenv("LOG_LEVEL", "DEBUG")
rotation = os.getenv("LOG_ROTATION", "50 MB")
retention = os.getenv("LOG_RETENTION", "7 days")
log_filename = os.getenv("LOG_FILENAME", "app.log")

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
        f"{log_path}/{log_filename}",
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

    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            frame, depth = sys._getframe(6), 6
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    # Принудительно направляем всё в Loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
