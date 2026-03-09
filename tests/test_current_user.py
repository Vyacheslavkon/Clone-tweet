import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from application.routes import get_current_user


async def test_current_user(test_session: AsyncSession, first_user):

    api_key = first_user.api_key

    await get_current_user(api_key=api_key, session=test_session)

    assert first_user



async def test_invalid_api_key(test_session: AsyncSession, first_user):

    invalid_key = "invalid"


    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(api_key=invalid_key, session=test_session)


    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "User not found"