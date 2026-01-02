"""
Database Connection

Async SQLAlchemy connection for Neon PostgreSQL.
"""

from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import NullPool

from config.settings import settings


# Lazy initialization - don't create engine at module load
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker] = None


def get_engine() -> AsyncEngine:
    """Get or create the async engine (lazy initialization)."""
    global _engine
    
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
            poolclass=NullPool,  # Better for serverless
        )
    
    return _engine


def get_session_factory() -> async_sessionmaker:
    """Get or create the session factory."""
    global _session_factory
    
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
    
    return _session_factory


# Alias for backward compatibility
def AsyncSessionLocal():
    """Get a new session from the factory."""
    return get_session_factory()()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.
    
    Usage:
        async with get_async_session() as session:
            # do database operations
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Initialize database tables.
    
    Note: In production, use Alembic migrations instead.
    """
    from database.models import Base
    
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    global _engine, _session_factory
    
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None


@asynccontextmanager
async def get_db_context():
    """
    Context manager for database sessions.
    
    Usage:
        async with get_db_context() as db:
            result = await db.execute(select(User))
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

