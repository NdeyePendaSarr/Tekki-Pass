"""Per-client rate limiting (threat model: "Request flooding").

A sliding-window counter in memory: enough for the single API process of the MVP.
With several processes or servers, each one would count separately; a shared store
(Redis) would then be needed.

The client is identified by IP address. Behind a reverse proxy (the web app's /api
proxy, the hosting platform), every request comes from the proxy's IP, so the real
client IP is read from X-Forwarded-For, but only when the direct peer is a trusted
proxy. Otherwise anyone could send a fake header to escape the limit.
"""

import ipaddress
import math
import time
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

#: Hard cap on remembered clients, so a flood of distinct IPs cannot exhaust memory.
MAX_TRACKED_KEYS = 50_000


@dataclass(slots=True)
class RateLimiter:
    """Allows at most `limit` hits per `window_seconds` for each (bucket, client) pair."""

    clock: Callable[[], float] = time.monotonic
    _hits: dict[tuple[str, str], deque[float]] = field(default_factory=dict)

    def hit(self, bucket: str, client: str, limit: int, window_seconds: float) -> float | None:
        """Record a hit. Return None if allowed, else the seconds to wait before retrying."""
        now = self.clock()
        key = (bucket, client)
        timestamps = self._hits.get(key)
        if timestamps is None:
            if len(self._hits) >= MAX_TRACKED_KEYS:
                self._prune(now, window_seconds)
            timestamps = self._hits[key] = deque()
        while timestamps and now - timestamps[0] >= window_seconds:
            timestamps.popleft()
        if len(timestamps) >= limit:
            return window_seconds - (now - timestamps[0])
        timestamps.append(now)
        return None

    def _prune(self, now: float, window_seconds: float) -> None:
        """Forget clients with no recent hit; if still full, forget the oldest ones."""
        self._hits = {k: v for k, v in self._hits.items() if v and now - v[-1] < window_seconds}
        overflow = len(self._hits) - MAX_TRACKED_KEYS // 2
        if overflow > 0:
            oldest = sorted(self._hits, key=lambda k: self._hits[k][-1])[:overflow]
            for k in oldest:
                del self._hits[k]


def retry_after_header(seconds: float) -> str:
    """Retry-After value in whole seconds, at least 1."""
    return str(max(1, math.ceil(seconds)))


@dataclass(frozen=True, slots=True)
class ClientIdentifier:
    """Finds the client IP, trusting X-Forwarded-For only from the given proxy networks."""

    trusted_proxies: Sequence[str] = ()

    def __post_init__(self) -> None:
        # Fail at startup on a malformed network rather than on the first request.
        for network in self.trusted_proxies:
            ipaddress.ip_network(network, strict=False)

    def _is_trusted(self, peer: str) -> bool:
        try:
            address = ipaddress.ip_address(peer)
        except ValueError:
            return False
        return any(
            address in ipaddress.ip_network(net, strict=False) for net in self.trusted_proxies
        )

    def identify(self, peer: str | None, forwarded_for: str | None) -> str:
        """Return the client IP.

        X-Forwarded-For lists "client, proxy1, proxy2". Walking from the right and
        skipping trusted proxies gives the first address we did not add ourselves.
        """
        peer = peer or "unknown"
        if not forwarded_for or not self._is_trusted(peer):
            return peer
        hops = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]
        for hop in reversed(hops):
            if not self._is_trusted(hop):
                return hop
        return hops[0] if hops else peer
