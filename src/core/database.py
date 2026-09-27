from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.settings import settings

async_engine = create_async_engine(
    url=settings.db_url,
    pool_pre_ping=True,
)

session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
)
