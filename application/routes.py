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
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, MissingGreenlet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import application.schemas
from application.database import get_db
from application.models import FollowLink, Likes, Media, Tweet, User
from config import MEDIA_DIR

schemas = application.schemas

router = APIRouter(prefix="/api", tags=["All"])


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
    logger.info("User {} identified.", user.name)
    return user


@router.get("/users/me", response_model=schemas.UserInfo)
async def auth_user(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):

    query_user = (
        select(User)
        .where(User.id == current_user.id)
        .options(selectinload(User.followers), selectinload(User.following))
    )

    result = await session.execute(query_user)
    user = result.scalars().first()

    return {"result": True, "user": user}


@router.post("/tweets", response_model=schemas.AddTweet)
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
    async with session.begin_nested() if session.in_transaction() else session.begin():
        session.add(new_media)
    response = {"media_id": new_media.id}
    logger.info("Image: {} saved successful.", new_media.id)

    return response


@router.post("/user", response_model=schemas.AddUser)
async def add_user(user: schemas.AddUser, session: AsyncSession = Depends(get_db)):

    new_user = User(**user.model_dump())
    async with session.begin():
        session.add(new_user)

    return JSONResponse(
        content={"response": "user successfully create!"}, status_code=201
    )


@router.delete("/tweets/{tweet_id}", response_model=schemas.ResultTrue)
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


@router.get("/tweets", response_model=schemas.GetTweets)
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


@router.get("/users/{id}", response_model=schemas.UserInfo)
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


@router.post("/tweets/{id}/likes", response_model=schemas.ResultTrue)
async def post_like(
    id: Annotated[int, Path()],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tweet = await session.get(Tweet, id)  # Самый быстрый способ найти по PK
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")

    new_like = Likes(user_id=current_user.id, tweet_id=id)
    session.add(new_like)
    user_name = current_user.name
    try:
        await session.commit()
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

    like_query = select(Likes).where(
        Likes.user_id == current_user.id, Likes.tweet_id == id
    )
    result = await session.execute(like_query)
    like = result.scalars().one_or_none()

    if not like:
        logger.warning("User: {}  Entry does not exist.", user_name)
        raise HTTPException(status_code=404, detail="Entry does not exist.")

    await session.delete(like)
    try:
        await session.commit()
        logger.info("User: {} Unlike tweet {}", user_name, id)
    except IntegrityError:
        await session.rollback()
        logger.warning("User: {}  Unable to delete object.", user_name)
        raise HTTPException(status_code=400, detail="Unable to delete object.")

    return {"result": True}


@router.post("/users/{id}/follow", response_model=schemas.ResultTrue)
async def following(
    id: Annotated[int, Path()],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    new_subscription = FollowLink(follower_id=current_user.id, followed_id=id)
    user_name = current_user.name
    session.add(new_subscription)
    try:
        await session.commit()
        logger.info("User: {}. New entry added.", user_name)
    except IntegrityError as e:
        await session.rollback()
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

    query_follow = select(FollowLink).where(
        FollowLink.followed_id == id, FollowLink.follower_id == current_user.id
    )

    result = await session.execute(query_follow)

    follow = result.scalars().one_or_none()

    if not follow:
        logger.warning("Entry does not exist. Send request user {}", current_user.name)
        raise HTTPException(status_code=400, detail="Entry does not exist.")

    await session.delete(follow)

    await session.commit()
    logger.info(
        "User: {}. The user's id = {} subscription has been canceled",
        current_user.name,
        id,
    )

    return {"result": True}
