"""
Async database engine and session factory.

Every repository gets its DB session through the `get_db` dependency
below -- nothing constructs a Session or Engine on its own. This is
the one place connection pooling and session lifecycle are decided.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,  # detects and replaces dead connections instead of raising mid-request
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # lets response models read attributes after commit without a refetch
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields one session per request.

    Always closes the session when the request finishes, whether it
    finished cleanly or raised -- this is what prevents connection
    leaks under load.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
