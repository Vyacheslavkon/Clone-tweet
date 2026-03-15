import uvicorn
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from application.database import engine
from anyio import to_thread
from migrations import utils
from logger_config import setup_logging
from starlette.staticfiles import StaticFiles
from loguru import logger
import time

from config import STATIC_DIR, MEDIA_DIR, CSS_DIR, JS_DIR
from application.routes import router


@asynccontextmanager
async def lifespan(_: FastAPI):

    await to_thread.run_sync(utils.run_upgrade)  # new

    yield

    await engine.dispose()

setup_logging()

app = FastAPI(lifespan=lifespan)
app.include_router(router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/js", StaticFiles(directory=str(JS_DIR)), name="js")
app.mount("/css", StaticFiles(directory=str(CSS_DIR)), name="css")
app.mount("/application/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

@app.middleware("http")
async def db_error_middleware(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.debug(
            "Request {} {} completed in {:.4f} s",
            request.method,
            request.url.path,
            process_time,
        )
        return response
    except Exception as e:  # noqa
        logger.exception("Internal Server Error: {}", e)
        traceback.print_exc()
        raise e



if __name__ == "__main__":

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
