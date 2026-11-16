"""NIP-98 HTTP Auth: the artisan proves ownership of their Nostr key on each request.

Spec: https://github.com/nostr-protocol/nips/blob/master/98.md

The client sends `Authorization: Nostr <base64 of a signed event>` where the event is:
    kind 27235, content "",
    ["u", <absolute request URL>], ["method", <HTTP method>],
    ["payload", <hex SHA-256 of the request body>]   (required here when there is a body)

Without this, anyone could create attestation requests in an artisan's name.
Signature checks use nostr-sdk (no home-made crypto); this module only applies
the NIP-98 rules on top.
"""

import base64
import hashlib
import hmac
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import nostr_sdk

HTTP_AUTH_KIND = 27235
#: NIP-98 recommends a "reasonable window"; 60 s tolerates phone clock drift.
MAX_CLOCK_SKEW_SECONDS = 60
#: An auth event is a few hundred bytes; refuse anything absurd before decoding it.
MAX_HEADER_LENGTH = 8192
_SCHEME = "Nostr "


class Nip98Error(Exception):
    """Authentication failure. `code` is stable for the front end, `status` is the HTTP status."""

    def __init__(self, code: str, message: str, status: int = 401) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass(slots=True)
class ReplayCache:
    """Remembers recently used auth events so a captured header cannot be replayed.

    In memory: enough for a single API process. Entries expire after twice the
    clock-skew window, after which the timestamp check rejects the event anyway.
    """

    ttl_seconds: int = 2 * MAX_CLOCK_SKEW_SECONDS
    _seen: dict[str, float] = field(default_factory=dict)

    def check_and_remember(self, event_id: str, now: float) -> bool:
        """Return False if the event was already used, else remember it and return True."""
        self._seen = {eid: t for eid, t in self._seen.items() if now - t < self.ttl_seconds}
        if event_id in self._seen:
            return False
        self._seen[event_id] = now
        return True


def _single_tags(tags: list[list[str]]) -> dict[str, str]:
    values: dict[str, str] = {}
    for tag in tags:
        if len(tag) < 2:
            continue
        if tag[0] in values:
            raise Nip98Error("invalid_auth", f"duplicate {tag[0]!r} tag")
        values[tag[0]] = tag[1]
    return values


@dataclass(slots=True)
class Nip98Verifier:
    """Verifies NIP-98 Authorization headers.

    `accepted_url_prefixes` are the public bases the client may sign against, e.g.
    "https://tekki-pass.example/api" when calls go through the web proxy: the API
    itself only sees its internal URL, so it compares against prefix + path.
    """

    accepted_url_prefixes: Sequence[str]
    replay_cache: ReplayCache = field(default_factory=ReplayCache)
    clock: Callable[[], float] = time.time

    def verify(self, header: str | None, method: str, path: str, body: bytes) -> str:
        """Check the header and return the authenticated public key (hex).

        Raises:
            Nip98Error: with a stable `code` on any failed check.
        """
        if not header:
            raise Nip98Error("auth_required", "missing NIP-98 Authorization header")
        if len(header) > MAX_HEADER_LENGTH or not header.startswith(_SCHEME):
            raise Nip98Error("invalid_auth", "Authorization must use the Nostr scheme")
        try:
            event_json = base64.b64decode(header[len(_SCHEME) :], validate=True).decode()
            event = nostr_sdk.Event.from_json(event_json)
        except Exception as exc:  # bad base64, bad UTF-8, or nostr-sdk's own parse errors
            raise Nip98Error("invalid_auth", "Authorization is not a Nostr event") from exc

        if not bool(event.verify()):
            raise Nip98Error("invalid_auth", "invalid signature")
        if int(event.kind().as_u16()) != HTTP_AUTH_KIND:
            raise Nip98Error("invalid_auth", "wrong event kind")
        now = self.clock()
        if abs(now - int(event.created_at().as_secs())) > MAX_CLOCK_SKEW_SECONDS:
            raise Nip98Error("invalid_auth", "auth event expired or from the future")

        tags = _single_tags([[str(v) for v in tag.to_vec()] for tag in event.tags()])
        if tags.get("method", "").upper() != method.upper():
            raise Nip98Error("invalid_auth", "signed method does not match")
        expected_urls = {prefix.rstrip("/") + path for prefix in self.accepted_url_prefixes}
        if tags.get("u", "") not in expected_urls:
            raise Nip98Error("invalid_auth", "signed URL does not match")
        if body:
            digest = hashlib.sha256(body).hexdigest()
            if not hmac.compare_digest(tags.get("payload", "").lower(), digest):
                raise Nip98Error("invalid_auth", "signed payload does not match the body")

        # Last, so a rejected event never fills the cache.
        if not self.replay_cache.check_and_remember(str(event.id().to_hex()), now):
            raise Nip98Error("invalid_auth", "auth event already used")
        return str(event.author().to_hex())
