import os
import logging
import sys
import aiofiles
import traceback
from contextlib import asynccontextmanager
from typing import Annotated

from alembic.config import Config
from alembic import command
from fastapi import FastAPI, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse
from fastapi import Request, UploadFile
from anyio import to_thread
from application.database import engine, get_db
import application.schemas
from application.models import Tweet, User, Media

ROOT_PATH = os.getcwd()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#STATIC_DIR = os.path.join(ROOT_PATH, "static")
STATIC_DIR = "/application/static"
#TEMPLATES_DIR = os.path.join(ROOT_PATH, "templates")
ROOT_DIR = os.path.dirname(os.path.abspath(BASE_DIR))
alembic_ini = os.path.join(ROOT_PATH, "alembic.ini")
INDEX = os.path.join(STATIC_DIR, "index.html")

schemas = application.schemas

logger = logging.getLogger("Routes")
logging.basicConfig(stream=sys.stdout, level="DEBUG")



def run_upgrade():
    sync_url = (os.getenv('DATABASE_URL_DOCKER').
                replace("postgresql+asyncpg://", "postgresql://"))#new
    alembic_cfg = Config(alembic_ini)
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)#new
    alembic_cfg.set_main_option("script_location", os.path.join(ROOT_DIR, "alembic"))
    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations applied successfully")
    except Exception as e:
        logger.error(f"Error running migrations: {e}")


@asynccontextmanager
async def lifespan(application: FastAPI):

    await to_thread.run_sync(run_upgrade) #new
    logger.info("performing migrations")
    yield

    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/js", StaticFiles(directory=os.path.join(STATIC_DIR, "js")), name="js")
app.mount("/css", StaticFiles(directory=os.path.join(STATIC_DIR, "css")), name="css")




@app.middleware("http")
async def db_error_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        # Это выведет красную ошибку в терминал Docker
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})



@app.get("/api/users/me", response_model=schemas.UserInfo)
async def auth_user(api_key: Annotated[str, Header()],
                    session: AsyncSession = Depends(get_db)):
    query = select(User).where(User.api_key == api_key).options(
            selectinload(User.followers),
            selectinload(User.following))

    result = await session.execute(query)
    user = result.scalars().first()

    if not user:

        raise HTTPException(status_code=404, detail="User not found")

    response = {
        "result": "true",
        "user": user
    }

    return response



@app.post("/api/tweets", response_model=schemas.AddTweet)
async def add_tweet(api_key: Annotated[str, Header()],
                    tweet: schemas.AddTweet, session:
                AsyncSession = Depends(get_db),) -> JSONResponse:

    tweet_data = tweet.model_dump()

    async with session.begin():
        query = select(User).where(User.api_key == api_key)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = user.id
        tweet_data["user_id"] = user_id
        new_tweet = Tweet(**tweet_data)
        session.add(new_tweet)

    response = {
        "result": True,
        "tweet_id": new_tweet.id
    }

    return   JSONResponse(content=response, status_code=201)


@app.post("/api/medias", response_model=schemas.UploadMedia)
async  def upload_media(file: UploadFile, session: AsyncSession = Depends(get_db)):
    file_path = f"static/media/{file.filename}"
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    media_data = dict()
    media_data["path"] = file_path
    new_media = Media(**media_data)
    async with session.begin():
        session.add(new_media)
    return new_media


@app.get("/api/tweets", response_model=schemas.AddTweet)
async def get_tweets(tweet: schemas.AddTweet,
                     session: AsyncSession = Depends(get_db)):
    logger.info("api - get start!")

    res =  await session.execute(select(Tweet)
         .options(joinedload(Tweet.tweet_media))
         .where(Tweet.id == 1))

    response = res.scalars().unique().one()

    return response

@app.post("/api/user", response_model=schemas.UserInfo)
async def add_user(user: schemas.UserInfo,
                   session: AsyncSession = Depends(get_db)):

    new_user = User(**user.model_dump())
    async with session.begin():
        session.add(new_user)

    return JSONResponse(content={"response": "user successfully create!"},
                        status_code=201)


@app.get("/{catchall:path}")
async def serve_frontend(request: Request, catchall: str):
    if catchall.startswith("api/"):
        return JSONResponse(status_code=404, content={"result": False,
                                    "error": "API route not found"})

    file_path = os.path.join(STATIC_DIR, catchall)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)


    return FileResponse(os.path.join(STATIC_DIR, "index.html"))