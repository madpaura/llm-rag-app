"""
Async database configuration for better multi-user performance.
Uses SQLAlchemy async engine with connection pooling.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import structlog

from .config import get_settings

logger = structlog.get_logger()
settings = get_settings()


def get_async_database_url() -> str:
    """Convert sync database URL to async URL."""
    url = settings.DATABASE_URL
    if url.startswith("sqlite:///"):
        # SQLite async requires aiosqlite
        return url.replace("sqlite:///", "sqlite+aiosqlite:///")
    elif url.startswith("postgresql://"):
        # PostgreSQL async requires asyncpg
        return url.replace("postgresql://", "postgresql+asyncpg://")
    elif url.startswith("mysql://"):
        # MySQL async requires aiomysql
        return url.replace("mysql://", "mysql+aiomysql://")
    return url


# Create async engine with connection pooling
async_engine = create_async_engine(
    get_async_database_url(),
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=False,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async database session context manager."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async database dependency for FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_async_db():
    """Initialize async database tables."""
    from .database import Base
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Async database tables created successfully")


async def close_async_db():
    """Close async database connections."""
    await async_engine.dispose()
    logger.info("Async database connections closed")
