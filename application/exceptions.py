from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger


async def global_exception_handler(request: Request, exc: Exception):

    logger.error("Unhandled error: {}", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


def setup_exception_handlers(app: FastAPI):
    # Регистрируем обработчик без декоратора
    app.add_exception_handler(Exception, global_exception_handler)
