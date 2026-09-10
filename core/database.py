from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from core.config import DATABASE_URL_DOCKER, ENGINE_KWARGS

load_dotenv()


bot_engine = create_async_engine(DATABASE_URL_DOCKER, pool_size=20, max_overflow=10, **ENGINE_KWARGS)
bot_session_maker = async_sessionmaker(bind=bot_engine, expire_on_commit=False, class_=AsyncSession)

async def get_bot_db():
    async with bot_session_maker() as session:
        yield session