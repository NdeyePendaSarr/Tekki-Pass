"""Tests for the public issuer endpoint used by the verification page."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app


def issuer_info(**settings: object) -> dict[str, object]:
    app = create_app(Settings(database_url="sqlite+aiosqlite:///:memory:", **settings))  # type: ignore[arg-type]
    with TestClient(app) as client:
        response = client.get("/issuer")
    assert response.status_code == 200
    return dict(response.json())


def test_relays_default_to_the_publishing_relays() -> None:
    info = issuer_info(nostr_relays=["ws://localhost:7777"])

    assert info["relays"] == ["ws://localhost:7777"]


def test_public_relays_override_internal_addresses() -> None:
    # In Docker the API publishes to ws://relay:8080, which a browser cannot reach.
    info = issuer_info(nostr_relays=["ws://relay:8080"], public_relays=["ws://localhost:7777"])

    assert info["relays"] == ["ws://localhost:7777"]


def test_public_relays_are_validated() -> None:
    with pytest.raises(ValidationError, match="relay URL"):
        Settings(public_relays=["http://not-a-relay.example"])
