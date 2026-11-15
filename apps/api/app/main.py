"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.attestations import EventPublisher, IssuerKeys, NostrRelayPublisher
from app.config import Network, Settings, get_settings
from app.db import create_engine, create_schema, create_session_factory, is_sqlite
from app.lightning.fake import FakeWalletResolver
from app.requests.routes import dev_router, router
from app.requests.service import WalletResolver


class HealthResponse(BaseModel):
    """Payload returned by the liveness probe."""

    status: Literal["ok"]
    network: Network


def _wallets_for(settings: Settings) -> WalletResolver:
    if settings.lightning_backend == "fake":
        return FakeWalletResolver()
    raise NotImplementedError(settings.lightning_backend)  # pragma: no cover


def create_app(
    settings: Settings | None = None,
    *,
    wallets: WalletResolver | None = None,
    publisher: EventPublisher | None = None,
) -> FastAPI:
    """Build the application.

    A factory keeps tests isolated: each test passes its own settings and fakes
    instead of mutating the process environment.
    """
    resolved = (settings if settings is not None else get_settings()).with_dev_secrets()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(resolved.database_url)
        if is_sqlite(resolved.database_url):
            await create_schema(engine)  # PostgreSQL schema comes from Alembic migrations
        app.state.session_factory = create_session_factory(engine)
        yield
        await engine.dispose()

    app = FastAPI(title="Tekki-Pass API", version="0.1.0", lifespan=lifespan)
    app.state.settings = resolved
    app.state.wallets = wallets if wallets is not None else _wallets_for(resolved)
    app.state.publisher = (
        publisher
        if publisher is not None
        else NostrRelayPublisher(resolved.nostr_relays, min_acks=resolved.nostr_min_relay_acks)
    )
    nsec = resolved.nostr_issuer_nsec
    app.state.issuer_pubkey = IssuerKeys(nsec.get_secret_value()).public_key if nsec else None

    @app.get("/health", response_model=HealthResponse, tags=["ops"])
    def health() -> HealthResponse:
        """Liveness probe used by Docker and the deployment platform."""
        return HealthResponse(status="ok", network=resolved.network)

    app.include_router(router)
    if isinstance(app.state.wallets, FakeWalletResolver):
        app.include_router(dev_router)

    return app


app = create_app()
