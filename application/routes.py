import os
import sys
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

import aiofiles
from anyio import to_thread
from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Path,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, JSONResponse
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.staticfiles import StaticFiles

import application.schemas
from alembic import command
from alembic.config import Config
from application.database import engine, get_db
from application.models import FollowLink, Likes, Media, Tweet, User

logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
    "{name}:{function}:{line} - {message}",
)
logger.add("routes_logs.log", rotation="10 MB", level="INFO", compression="zip")

ROOT_PATH = os.getcwd()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR_FOR_MEDIA = os.path.abspath(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
MEDIA_DIR = os.path.join(BASE_DIR, "media")
ROOT_DIR = os.path.dirname(os.path.abspath(BASE_DIR))
alembic_ini = os.path.join(BASE_DIR, "alembic.ini")
ALEMBIC_SCRIPTS = os.path.join(BASE_DIR, "alembic")
INDEX = os.path.join(STATIC_DIR, "index.html")

schemas = application.schemas


def run_upgrade():
    sync_url = os.getenv("DATABASE_URL_DOCKER").replace(
        "postgresql+asyncpg://", "postgresql://"
    )  # new
    alembic_cfg = Config(alembic_ini)
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)  # new
    alembic_cfg.set_main_option("script_location", ALEMBIC_SCRIPTS)
    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations applied successfully")
    except SQLAlchemyError as e:
        logger.error("Error running migrations: %s", e)


@asynccontextmanager
async def lifespan(_: FastAPI):

    await to_thread.run_sync(run_upgrade)  # new

    yield

    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/js", StaticFiles(directory=os.path.join(STATIC_DIR, "js")), name="js")
app.mount("/css", StaticFiles(directory=os.path.join(STATIC_DIR, "css")), name="css")
app.mount("/application/media", StaticFiles(directory=MEDIA_DIR), name="media")


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
        logger.exception("Internal Server Error: %s", e)
        traceback.print_exc()
        raise e


async def get_current_user(
    api_key: Annotated[str, Header()], session: AsyncSession = Depends(get_db)
) -> User:

    query = select(User).where(User.api_key == api_key)
    result = await session.execute(query)
    user = result.scalars().one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


@app.get("/api/users/me", response_model=schemas.UserInfo)
async def auth_user(
    api_key: Annotated[str, Header()], session: AsyncSession = Depends(get_db)
):

    query = (
        select(User)
        .where(User.api_key == api_key)
        .options(selectinload(User.followers), selectinload(User.following))
    )

    result = await session.execute(query)
    user = result.scalars().first()
    if user:

        logger.info("request completed: api/users/me/{}", user.name)
    if not user:
        logger.info("User not found")
        raise HTTPException(status_code=404, detail="User not found")

    # return {"result": "true", "user": user}
    return {"result": True, "user": user}


@app.post("/api/tweets", response_model=schemas.AddTweet)
async def add_tweet(
    tweet: schemas.AddTweet,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    logger.info("Request completed: api/post/tweet")
    tweet_data = tweet.model_dump(exclude={"tweet_media_ids"})
    async with session.begin_nested() if session.in_transaction() else session.begin():

        tweet_data["user_id"] = current_user.id
        new_tweet = Tweet(**tweet_data)
        session.add(new_tweet)
        await session.flush()

        if tweet.tweet_media_ids:
            update_query = (
                update(Media)
                .where(Media.id.in_(tweet.tweet_media_ids))
                .values(tweet_id=new_tweet.id)
            )
            await session.execute(update_query)
            logger.info("Added media. User: {}", current_user.name)

        await session.commit()
        logger.info("Tweet successfully saved. User: {}", current_user.name)
    response = {"result": True, "tweet_id": new_tweet.id}
    return JSONResponse(content=response, status_code=201)


@app.post("/api/medias", response_model=schemas.UploadMedia)
async def upload_media(file: UploadFile, session: AsyncSession = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is missing")

    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(MEDIA_DIR, unique_name)

    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)
    media_data = dict()
    media_data["path"] = file_path
    new_media = Media(**media_data)
    async with session.begin():
        session.add(new_media)
    response = {"media_id": new_media.id}
    logger.info("Image: %s saved successful.", new_media.id)

    return response


@app.post("/api/user", response_model=schemas.AddUser)
async def add_user(user: schemas.AddUser, session: AsyncSession = Depends(get_db)):

    new_user = User(**user.model_dump())
    async with session.begin():
        session.add(new_user)

    return JSONResponse(
        content={"response": "user successfully create!"}, status_code=201
    )


@app.delete("/api/tweets/{tweet_id}", response_model=schemas.ResultTrue)
async def delete_tweet(
    tweet_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    query_tweet = (
        select(Tweet)
        .where(Tweet.user_id == current_user.id, Tweet.id == tweet_id)
        .options(selectinload(Tweet.tweet_media_ids))
    )

    result_tweet = await session.execute(query_tweet)
    tweet = result_tweet.scalars().first()

    if not tweet:

        logger.warning("attempted unauthorized deletion! User:{}", current_user.name)
        raise HTTPException(status_code=400, detail="Cannot be deleted")

    for media in tweet.tweet_media_ids:
        if os.path.exists(media.path):
            os.remove(media.path)
            logger.info("File {} deleted from disk", media.path)

    await session.delete(tweet)
    try:
        await session.commit()

        logger.info("User {} delete tweet: id = {}", current_user.name, tweet_id)
    except IntegrityError:
        await session.rollback()
        logger.warning("User: {}  Entry does not exist.", current_user.name)
        raise HTTPException(status_code=400, detail="Entry does not exist.")

    return {"result": True}


@app.get("/api/tweets", response_model=schemas.GetTweets)
async def get_tweets(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Tweet)
        .options(
            selectinload(Tweet.author),
            selectinload(Tweet.tweet_media_ids),
            selectinload(Tweet.likes),
        )
        .where(
            Tweet.user_id.in_(
                select(FollowLink.followed_id).where(
                    FollowLink.follower_id
                    == (
                        select(User.id)
                        .where(User.id == current_user.id)
                        .scalar_subquery()
                    )
                )
            )
        )
    )

    result_query = await session.execute(stmt)
    tweets = result_query.scalars().unique().all()
    logger.info("User {}. The tweet feed is loaded", current_user.name)

    return schemas.GetTweets.model_validate({"tweets": tweets})


@app.get("/api/users/{id}", response_model=schemas.UserInfo)
async def get_profile_with_id(
    id: Annotated[int, Path()],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):

    query_user = (
        select(User)
        .where(User.id == id)
        .options(selectinload(User.followers), selectinload(User.following))
    )

    result = await session.execute(query_user)
    user = result.scalars().one_or_none()

    if not user:

        logger.warning(
            "User with id {} not found. Request completed by user {}", current_user.name
        )
        raise HTTPException(status_code=400, detail="Bad request!")

    logger.info(
        "Completed request user {} on profile user {} successfully.",
        current_user.name,
        user.name,
    )

    return {"result": True, "user": user}


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


@app.post("/api/tweets/{id}/likes", response_model=schemas.ResultTrue)
async def post_like(
    id: Annotated[int, Path()],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    new_like = Likes(user_id=current_user.id, tweet_id=id)
    session.add(new_like)

    try:
        await session.commit()
        logger.warning("User {}. Like created!", current_user.name)
    except IntegrityError:
        await session.rollback()
        logger.warning("User {}. Like already exists!", current_user.name)
        raise HTTPException(status_code=400, detail="Like already exists")

    return {"result": True}


@app.delete("/api/tweets/{id}/likes", response_model=schemas.ResultTrue)
async def delete_like(
    id: Annotated[int, Path()],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):

    like_query = select(Likes).where(
        Likes.user_id == current_user.id, Likes.tweet_id == id
    )
    result = await session.execute(like_query)
    like = result.scalars().one_or_none()

    await session.delete(like)
    try:
        await session.commit()
        logger.info("User: {} Unlike tweet {}", current_user.name, id)
    except IntegrityError:
        await session.rollback()
        logger.warning("User: {}  Entry does not exist.", current_user.name)
        raise HTTPException(status_code=400, detail="Entry does not exist.")

    return {"result": True}


@app.post("/api/users/{id}/follow", response_model=schemas.ResultTrue)
async def following(
    id: Annotated[int, Path()],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    new_subscription = FollowLink(follower_id=current_user.id, followed_id=id)

    session.add(new_subscription)
    try:
        await session.commit()
        logger.info("User: {}. New entry added.", current_user.name)
    except IntegrityError as e:
        await session.rollback()
        logger.warning("The entry already exists. Error: {}", e)
        raise HTTPException(status_code=400, detail="The entry already exists.")

    return {"result": True}


@app.delete("/api/users/{id}/follow", response_model=schemas.ResultTrue)
async def delete_follow(
    id: Annotated[int, Path()],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    query_follow = select(FollowLink).where(
        FollowLink.followed_id == id, FollowLink.follower_id == current_user.id
    )

    result = await session.execute(query_follow)

    follow = result.scalars().one_or_none()

    await session.delete(follow)
    try:
        await session.commit()
        logger.info(
            "User: {}. The user's id = {} subscription has been canceled",
            current_user.name,
            id,
        )
    except IntegrityError as e:
        await session.rollback()
        logger.warning("Entry does not exist. Error: {}", e)
        raise HTTPException(status_code=400, detail="Entry does not exist.")

    return {"result": True}
