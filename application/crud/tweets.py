from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select
from loguru import logger
from sqlalchemy.orm import selectinload

from application.models import User, Tweet, Media, FollowLink
from application.schemas import AddTweet


async def created_tweet(session: AsyncSession, user: User,
                        tweet: AddTweet, tweet_data) -> Tweet:
    async with session.begin_nested() if session.in_transaction() else session.begin():
        tweet_data["user_id"] = user.id
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
            logger.info("Added media. User: {}", user.name)

        await session.commit()
        return new_tweet


async def save_media(session: AsyncSession, media: Media):

    async with session.begin_nested() if session.in_transaction() else session.begin():
        session.add(media)


async def get_tweet(session: AsyncSession, tweet_id: int, user: User) -> Tweet:
    query = (
        select(Tweet).where(Tweet.user_id == user.id, Tweet.id == tweet_id)
        .options(selectinload(Tweet.tweet_media_ids))
    )

    result_tweet = await session.execute(query)
    tweet = result_tweet.scalars().first()

    return tweet


async def get_tweet_by_id(session: AsyncSession, tweet_id: int) -> Tweet | None:

    tweet = await session.get(Tweet, tweet_id)

    return tweet


async def del_tweet(session: AsyncSession, tweet: Tweet):

    try:
        await session.delete(tweet)
        await session.commit()

    except IntegrityError:
        await session.rollback()
        logger.error("DB IntegrityError during tweet deletion")
        raise


async def get_tweets_all(session: AsyncSession, user: User) :

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
                        .where(User.id == user.id)
                        .scalar_subquery()
                    )
                )
            )
        )
    )

    result_query = await session.execute(stmt)
    tweets = result_query.scalars().unique().all()

    return tweets