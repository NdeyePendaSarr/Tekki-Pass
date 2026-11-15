"""Tests for publishing attestations to Nostr relays.

The tests marked `needs_relay` publish to a real relay given by
NOSTR_TEST_RELAY_URL (a local nostr-rs-relay in CI). They are skipped when it
is not set, and never touch public relays.
"""

import json
import os
from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.attestations import (
    EventPublisher,
    IssuerKeys,
    NostrRelayPublisher,
    PublishError,
    build_badge_definition,
)
from app.attestations.relays import is_local_relay, validate_relay_url
from app.config import Settings
from tests.fakes.fake_publisher import FakePublisher

TEST_RELAY = os.environ.get("NOSTR_TEST_RELAY_URL")
needs_relay = pytest.mark.skipif(TEST_RELAY is None, reason="NOSTR_TEST_RELAY_URL not set")


@pytest.mark.parametrize(
    "url", ["wss://nos.lol", "ws://localhost:7777", "ws://127.0.0.1:8080", "ws://relay:8080"]
)
def test_accepts_tls_relays_and_local_dev_relays(url: str) -> None:
    assert validate_relay_url(url) == url


@pytest.mark.parametrize(
    "url", ["ws://nos.lol", "https://nos.lol", "nos.lol", "wss://", "ftp://relay:21"]
)
def test_rejects_unsafe_or_malformed_relay_urls(url: str) -> None:
    with pytest.raises(ValueError, match="relay URL"):
        validate_relay_url(url)


def test_publisher_validates_its_configuration() -> None:
    with pytest.raises(ValueError, match="at least one relay"):
        NostrRelayPublisher([])
    with pytest.raises(ValueError, match="min_acks"):
        NostrRelayPublisher(["wss://nos.lol"], min_acks=2)


def test_default_settings_only_publish_locally() -> None:
    # Safe default: a developer can never push fake attestations to public relays.
    settings = Settings()

    assert all(is_local_relay(url) for url in settings.nostr_relays)
    assert not is_local_relay("wss://nos.lol")


def test_settings_reject_inconsistent_relay_config() -> None:
    with pytest.raises(ValidationError, match="cannot exceed"):
        Settings(nostr_relays=["wss://nos.lol"], nostr_min_relay_acks=2)
    with pytest.raises(ValidationError, match="relay URL"):
        Settings(nostr_relays=["ws://nos.lol"], nostr_min_relay_acks=1)


def test_publishers_satisfy_the_protocol() -> None:
    assert isinstance(FakePublisher(), EventPublisher)
    assert isinstance(NostrRelayPublisher(["wss://nos.lol"], min_acks=1), EventPublisher)


@pytest.mark.anyio
async def test_fake_publisher_records_events() -> None:
    publisher = FakePublisher()
    event = build_badge_definition(IssuerKeys.generate())

    result = await publisher.publish(event)

    assert result.event_id == json.loads(event)["id"]
    assert publisher.published == [event]


@needs_relay
@pytest.mark.anyio
async def test_publishes_to_a_real_relay() -> None:
    assert TEST_RELAY is not None
    event = build_badge_definition(IssuerKeys.generate())

    result = await NostrRelayPublisher([TEST_RELAY], min_acks=1).publish(event)

    assert result.event_id == json.loads(event)["id"]
    assert len(result.accepted) == 1


@needs_relay
@pytest.mark.anyio
async def test_fails_when_too_few_relays_accept() -> None:
    assert TEST_RELAY is not None
    # Nothing listens on port 9: only one of the two required acknowledgements arrives.
    publisher = NostrRelayPublisher(
        [TEST_RELAY, "ws://localhost:9"], min_acks=2, timeout=timedelta(seconds=2)
    )

    with pytest.raises(PublishError, match="only 1 of 2"):
        await publisher.publish(build_badge_definition(IssuerKeys.generate()))
