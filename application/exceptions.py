from loguru import logger
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse




async def global_exception_handler(request: Request, exc: Exception):
    # Ваша логика (Error ID, логирование и т.д.)
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )

def setup_exception_handlers(app: FastAPI):
    # Регистрируем обработчик без декоратора
    app.add_exception_handler(Exception, global_exception_handler)
