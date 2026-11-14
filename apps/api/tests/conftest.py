"""Shared pytest fixtures."""

import pytest

from tests.fakes.fake_wallet import FakeLightningWallet


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests on asyncio (anyio's pytest plugin ships with FastAPI)."""
    return "asyncio"


@pytest.fixture
def wallet() -> FakeLightningWallet:
    """A fresh fake wallet per test."""
    return FakeLightningWallet()
