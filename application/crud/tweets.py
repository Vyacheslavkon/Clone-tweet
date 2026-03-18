from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from loguru import logger


from core.models import User, Tweet, Media
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