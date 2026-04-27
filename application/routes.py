import os
import pathlib
import uuid
from typing import Annotated

import aiofiles
from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Path,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import IntegrityError, MissingGreenlet
from sqlalchemy.ext.asyncio import AsyncSession

import application.schemas
from application.crud.followers import create_follow, del_follow, get_follow
from application.crud.likes import create_like, del_like, get_like
from application.crud.tweets import (
    created_tweet,
    del_tweet,
    get_tweet,
    get_tweet_by_id,
    get_tweets_all,
    save_media,
)
from application.crud.users import (
    create_user,
    get_profile,
    get_user,
    get_user_by_api_key,
)
from application.models import Media, User
from core.config import MEDIA_DIR
from core.database import get_db

schemas = application.schemas

router = APIRouter(prefix="/api", tags=["All"])


async def get_current_user(
    api_key: Annotated[str, Header()], session: AsyncSession = Depends(get_db)
) -> User:

    user = await get_user_by_api_key(session, api_key)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    logger.info("User {} identified.", user.name)
    return user


@router.get("/users/me", response_model=schemas.UserInfo)
async def auth_user(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):

    user = await get_user(session, current_user)

    return {"result": True, "user": user}


@router.post("/tweets", response_model=schemas.AddTweet)
async def add_tweet(
    tweet: schemas.AddTweet,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    logger.info("Request completed: api/post/tweet")
    tweet_data = tweet.model_dump(exclude={"tweet_media_ids"})

    new_tweet = await created_tweet(session, current_user, tweet, tweet_data)

    logger.info("Tweet successfully saved. User: {}", current_user.name)
    response = {"result": True, "tweet_id": new_tweet.id}
    return JSONResponse(content=response, status_code=201)


@router.post("/medias", response_model=schemas.UploadMedia)
async def upload_media(file: UploadFile, session: AsyncSession = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is missing")

    file_path = (
        pathlib.Path(MEDIA_DIR) / f"{uuid.uuid4()}{pathlib.Path(file.filename).suffix}"
    )

    async with aiofiles.open(str(file_path), "wb") as out_file:
        content = await file.read()
        await out_file.write(content)
    media_data = dict()
    media_data["path"] = str(file_path)
    new_media = Media(**media_data)

    await save_media(session, new_media)
    response = {"media_id": new_media.id}
    logger.info("Image: {} saved successful.", new_media.id)

    return response


@router.post("/user", response_model=schemas.AddUser)
async def add_user(
    user: schemas.AddUser, session: AsyncSession = Depends(get_db)
) -> User:

    new_user = User(**user.model_dump())

    await create_user(session, new_user)

    return new_user


@router.delete("/tweets/{tweet_id}", response_model=schemas.ResultTrue)
async def delete_tweet(
    tweet_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    tweet = await get_tweet(session, tweet_id, current_user)

    if not tweet:

        logger.warning("attempted unauthorized deletion! User:{}", current_user.name)
        raise HTTPException(status_code=400, detail="Cannot be deleted")

    for media in tweet.tweet_media_ids:
        if os.path.exists(media.path):
            os.remove(media.path)
            logger.info("File {} deleted from disk", media.path)

    try:
        await del_tweet(session, tweet)
    except Exception as e:  # noqa
        logger.warning("User: {}  Entry does not exist.", current_user.name)
        raise HTTPException(status_code=400, detail=f"Entry does not exist.{e}")

    return {"result": True}


@router.get("/tweets", response_model=schemas.GetTweets)
async def get_tweets(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):

    tweets = await get_tweets_all(session, current_user)
    logger.info("User {}. The tweet feed is loaded", current_user.name)

    return schemas.GetTweets.model_validate({"tweets": tweets})


@router.get("/users/{id}", response_model=schemas.UserInfo)
async def get_profile_with_id(
    id: Annotated[int, Path()],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):

    user = await get_profile(session, id)
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


@router.post("/tweets/{id}/likes", response_model=schemas.ResultTrue)
async def post_like(
    id: Annotated[int, Path()],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tweet = await get_tweet_by_id(session, id)
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")

    user_name = current_user.name
    try:
        await create_like(session, current_user, id)
        logger.warning("User {}. Like created!", user_name)

    except (IntegrityError, MissingGreenlet):
        await session.rollback()
        logger.warning("User {}. Like already exists!", user_name)
        raise HTTPException(status_code=400, detail="Like already exists")

    return {"result": True}


@router.delete("/tweets/{id}/likes", response_model=schemas.ResultTrue)
async def delete_like(
    id: Annotated[int, Path()],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    user_name = current_user.name

    like = await get_like(session, current_user, id)

    if not like:
        logger.warning("User: {}  Entry does not exist.", user_name)
        raise HTTPException(status_code=404, detail="Entry does not exist.")

    try:

        await del_like(session, like)
        logger.info("User: {} Unlike tweet {}", user_name, id)
    except IntegrityError:

        logger.warning("User: {}  Unable to delete object.", user_name)
        raise HTTPException(status_code=400, detail="Unable to delete object.")

    return {"result": True}


@router.post("/users/{id}/follow", response_model=schemas.ResultTrue)
async def following(
    id: Annotated[int, Path()],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    user_name = current_user.name

    try:
        await create_follow(session, current_user, id)

        logger.info("User: {}. New entry added.", user_name)
    except IntegrityError as e:

        if "unique" in str(e).lower():
            logger.warning("Duplicate follow attempt by {}", user_name)
            raise HTTPException(status_code=400, detail="Already following.")

        raise HTTPException(status_code=404, detail="Target user not found.")

    return {"result": True}


@router.delete("/users/{id}/follow", response_model=schemas.ResultTrue)
async def delete_follow(
    id: Annotated[int, Path()],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    follow = await get_follow(session, current_user, id)

    if not follow:
        logger.warning("Entry does not exist. Send request user {}", current_user.name)
        raise HTTPException(status_code=400, detail="Entry does not exist.")

    await del_follow(session, follow)
    logger.info(
        "User: {}. The user's id = {} subscription has been canceled",
        current_user.name,
        id,
    )

    return {"result": True}
