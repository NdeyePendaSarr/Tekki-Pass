"""FastAPI application entry point."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.config import Network, Settings, get_settings


class HealthResponse(BaseModel):
    """Payload returned by the liveness probe."""

    status: Literal["ok"]
    network: Network


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application.

    A factory keeps tests isolated: each test passes its own settings
    instead of mutating the process environment.
    """
    resolved = settings if settings is not None else get_settings()
    app = FastAPI(title="Tekki-Pass API", version="0.1.0")

    @app.get("/health", response_model=HealthResponse, tags=["ops"])
    def health() -> HealthResponse:
        """Liveness probe used by Docker and the deployment platform."""
        return HealthResponse(status="ok", network=resolved.network)

    return app


app = create_app()
