"""Publication of signed attestations to public Nostr relays.

Publishing to several independent relays is what lets proofs survive
Tekki-Pass (docs/adr/0002). A publication only counts as done when at least
`min_acks` relays have accepted the event.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Protocol, runtime_checkable
from urllib.parse import urlsplit

import nostr_sdk

from app.attestations.models import AttestationError

#: Plain ws:// is only accepted for relays on the local machine or the Docker network.
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class PublishError(RuntimeError):
    """Raised when too few relays accepted the event."""


@dataclass(frozen=True, slots=True)
class PublishResult:
    """Outcome of one publication."""

    event_id: str
    #: Relay URLs that acknowledged the event.
    accepted: tuple[str, ...]
    #: Relay URL -> reason, for relays that refused it or could not be reached.
    rejected: Mapping[str, str] = field(default_factory=dict)


@runtime_checkable
class EventPublisher(Protocol):
    """Publishes a signed Nostr event (JSON)."""

    async def publish(self, event_json: str) -> PublishResult:
        """Send the event; raise PublishError if not enough relays accepted it."""
        ...


def validate_relay_url(url: str) -> str:
    """Return the URL if it is a usable relay address.

    Requires wss:// (TLS), except ws:// for local development relays, and a
    Docker service name without dots (e.g. "ws://relay:8080").

    Raises:
        ValueError: for any other URL.
    """
    parts = urlsplit(url)
    host = parts.hostname or ""
    is_local = host in _LOCAL_HOSTS or (host != "" and "." not in host)
    if parts.scheme == "wss" and host:
        return url
    if parts.scheme == "ws" and is_local:
        return url
    raise ValueError(f"relay URL must use wss:// (ws:// only for local relays): {url!r}")


class NostrRelayPublisher:
    """Publishes events with nostr-sdk to a fixed list of relays."""

    def __init__(
        self, relays: Sequence[str], min_acks: int = 2, timeout: timedelta = timedelta(seconds=10)
    ) -> None:
        if not relays:
            raise ValueError("at least one relay is required")
        if not 1 <= min_acks <= len(relays):
            raise ValueError("min_acks must be between 1 and the number of relays")
        self._relays = tuple(validate_relay_url(url) for url in relays)
        self._min_acks = min_acks
        self._timeout = timeout

    async def publish(self, event_json: str) -> PublishResult:
        try:
            event = nostr_sdk.Event.from_json(event_json)
        except Exception as exc:
            raise AttestationError("not a valid Nostr event") from exc

        # One short-lived client per publication: simple and enough for MVP volumes.
        client = nostr_sdk.Client()
        try:
            for url in self._relays:
                await client.add_relay(nostr_sdk.RelayUrl.parse(url))
            await client.connect(self._timeout)
            output = await client.send_event(event, ok_timeout=self._timeout)
        finally:
            await client.shutdown()

        result = PublishResult(
            event_id=str(output.id.to_hex()),
            accepted=tuple(sorted(str(url) for url in output.success)),
            rejected={str(url): str(reason) for url, reason in output.failed.items()},
        )
        if len(result.accepted) < self._min_acks:
            raise PublishError(
                f"only {len(result.accepted)} of {self._min_acks} required relays accepted "
                f"event {result.event_id}: {dict(result.rejected)}"
            )
        return result
