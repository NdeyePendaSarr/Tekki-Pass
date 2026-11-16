"""Tests for the badge definition (NIP-58 kind 30009) and its publication."""

import json
import logging
import os

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from app.attestations import (
    BADGE_IDENTIFIER,
    IssuerKeys,
    NostrRelayPublisher,
    build_badge_definition,
)
from app.attestations.definition import publish_badge_definition, publish_badge_definition_safely
from app.config import Settings
from app.lightning.fake import FakeWalletResolver
from app.main import create_app
from tests.fakes.fake_publisher import FakePublisher

TEST_RELAY = os.environ.get("NOSTR_TEST_RELAY_URL")


def tags_of(event_json: str) -> dict[str, str]:
    return {tag[0]: tag[1] for tag in json.loads(event_json)["tags"]}


def make_settings(issuer: IssuerKeys | None, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "sqlite+aiosqlite:///:memory:",
        "nostr_issuer_nsec": SecretStr(issuer._keys.secret_key().to_hex()) if issuer else None,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


# --- Event content -----------------------------------------------------------------


def test_definition_is_addressable_and_matches_the_awards() -> None:
    issuer = IssuerKeys.generate()

    event = json.loads(build_badge_definition(issuer))

    assert event["kind"] == 30009
    assert event["pubkey"] == issuer.public_key
    # Awards point to "30009:<issuer>:<d tag>": the d tag must be the shared identifier.
    assert tags_of(json.dumps(event))["d"] == BADGE_IDENTIFIER
    assert tags_of(json.dumps(event))["name"] == "Chantier attesté Tekki-Pass"


def test_image_is_optional() -> None:
    issuer = IssuerKeys.generate()

    assert "image" not in tags_of(build_badge_definition(issuer))
    with_image = build_badge_definition(issuer, "https://tekki-pass.example/badge.png")
    assert tags_of(with_image)["image"] == "https://tekki-pass.example/badge.png"


def test_image_url_must_be_https() -> None:
    with pytest.raises(ValidationError):
        Settings(badge_image_url="http://insecure.example/badge.png")


# --- Publication -------------------------------------------------------------------


@pytest.mark.anyio
async def test_publish_sends_the_signed_definition() -> None:
    issuer = IssuerKeys.generate()
    publisher = FakePublisher()

    result = await publish_badge_definition(issuer, publisher)

    assert len(publisher.published) == 1
    assert json.loads(publisher.published[0])["id"] == result.event_id


@pytest.mark.anyio
async def test_relay_outage_is_logged_not_raised(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        result = await publish_badge_definition_safely(
            IssuerKeys.generate(), FakePublisher(fail=True)
        )

    assert result is None
    assert "badge definition not published" in caplog.text


# --- API startup -------------------------------------------------------------------


def test_api_publishes_the_definition_at_startup() -> None:
    issuer = IssuerKeys.generate()
    publisher = FakePublisher()
    app = create_app(make_settings(issuer), wallets=FakeWalletResolver(), publisher=publisher)

    with TestClient(app):
        pass  # shutdown waits for the background publication

    assert len(publisher.published) == 1
    event = json.loads(publisher.published[0])
    assert event["kind"] == 30009
    assert event["pubkey"] == issuer.public_key


def test_api_starts_even_if_relays_are_down() -> None:
    app = create_app(
        make_settings(IssuerKeys.generate()),
        wallets=FakeWalletResolver(),
        publisher=FakePublisher(fail=True),
    )

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200


@pytest.mark.parametrize(
    "settings_kwargs",
    [{"publish_badge_definition_on_startup": False}, {}],
    ids=["disabled", "no-issuer-key"],
)
def test_nothing_is_published_when_disabled_or_without_key(
    settings_kwargs: dict[str, object],
) -> None:
    issuer = IssuerKeys.generate() if settings_kwargs else None
    publisher = FakePublisher()
    app = create_app(
        make_settings(issuer, **settings_kwargs), wallets=FakeWalletResolver(), publisher=publisher
    )

    with TestClient(app):
        pass

    assert publisher.published == []


@pytest.mark.skipif(TEST_RELAY is None, reason="NOSTR_TEST_RELAY_URL not set")
@pytest.mark.anyio
async def test_definition_is_accepted_by_a_real_relay() -> None:
    assert TEST_RELAY is not None
    issuer = IssuerKeys.generate()

    result = await publish_badge_definition(issuer, NostrRelayPublisher([TEST_RELAY], min_acks=1))

    assert len(result.accepted) == 1
