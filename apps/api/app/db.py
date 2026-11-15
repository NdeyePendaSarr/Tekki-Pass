"""Database access: async SQLAlchemy engine, sessions and the declarative base.

PostgreSQL in Docker and production (schema managed by Alembic), SQLite for
local runs without Docker and for tests (schema created on startup).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Base class of all ORM models."""


def async_database_url(url: str) -> str:
    """Use the async driver for plain postgresql:// URLs (as given by docker-compose)."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url.removeprefix(prefix)
    return url


def is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def create_engine(url: str) -> AsyncEngine:
    """Create the engine. In-memory SQLite shares one connection so data survives requests."""
    url = async_database_url(url)
    if url.startswith("sqlite") and ":memory:" in url:
        return create_async_engine(
            url, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    return create_async_engine(url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False: objects stay readable after commit, for building responses.
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_schema(engine: AsyncEngine) -> None:
    """Create tables directly (SQLite only: PostgreSQL goes through Alembic migrations)."""
    import app.requests.models  # noqa: F401  # register the models on Base.metadata

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """One session per unit of work, rolled back on error."""
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
