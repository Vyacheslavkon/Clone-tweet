from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def test_tweet_feed(
    client: AsyncClient,
    test_session: AsyncSession,
    first_user,
    test_tweet_with_media,
    second_user,
    create_like,
):

    headers = {"api-key": "user"}
    response = await client.get("/api/tweets", headers=headers)

    answer = {
        "result": True,
        "tweets": [
            {
                "id": test_tweet_with_media.id,
                "content": test_tweet_with_media.tweet_data,
                "attachments": [
                    media.path for media in test_tweet_with_media.tweet_media_ids
                ],
                "author": {"id": first_user.id, "name": first_user.name},
                "likes": [{"user_id": second_user.id, "name": second_user.name}],
            }
        ],
    }

    assert response.status_code == 200
    assert response.json() == answer
