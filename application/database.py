import os

from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

database_url = os.getenv("DATABASE_URL_DOCKER")

if database_url is None:
    raise ValueError("DATABASE_URL_DOCKER is not set in environment variables")
engine = create_async_engine(database_url, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session
