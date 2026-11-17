"""Shared pytest fixtures."""

import asyncio
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.config import get_settings
from app.db import Base, create_engine, is_sqlite
from tests.database import TEST_DATABASE_URL
from tests.fakes.fake_wallet import FakeLightningWallet

API_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests on asyncio (anyio's pytest plugin ships with FastAPI)."""
    return "asyncio"


@pytest.fixture
def wallet() -> FakeLightningWallet:
    """A fresh fake wallet per test."""
    return FakeLightningWallet()


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> Iterator[None]:
    """PostgreSQL only: build the schema with the real Alembic migrations, once."""
    if is_sqlite(TEST_DATABASE_URL):
        yield  # each test app creates its own in-memory schema
        return
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL  # read by migrations/env.py
    get_settings.cache_clear()
    try:
        # No alembic.ini: its logging section would disable the loggers tests rely on.
        config = Config()
        config.set_main_option("script_location", str(API_ROOT / "migrations"))
        command.upgrade(config, "head")
        yield
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()


async def _truncate_all_tables() -> None:
    import app.requests.models  # noqa: F401  # register the models on Base.metadata

    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    engine = create_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    await engine.dispose()


@pytest.fixture(autouse=True)
def _empty_database(_migrated_database: None) -> None:
    """PostgreSQL only: every test starts from empty tables, like a new in-memory SQLite."""
    if not is_sqlite(TEST_DATABASE_URL):
        asyncio.run(_truncate_all_tables())
