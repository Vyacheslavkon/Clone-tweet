import os
import time
import traceback
from contextlib import asynccontextmanager

import uvicorn
from anyio import to_thread
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from loguru import logger
from starlette.staticfiles import StaticFiles

from core.database import engine
from application.routes import router
from core.config import CSS_DIR, JS_DIR, MEDIA_DIR, STATIC_DIR
from logger_config import setup_logging
from migrations import utils


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


@app.get("/{catchall:path}")
async def serve_frontend(_: Request, catchall: str):
    if catchall.startswith("api/"):
        return JSONResponse(
            status_code=404, content={"result": False, "error": "API route not found"}
        )

    file_path = os.path.join(STATIC_DIR, catchall)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)

    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == "__main__":

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
