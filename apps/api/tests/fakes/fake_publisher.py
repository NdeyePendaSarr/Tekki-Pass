"""In-memory `EventPublisher` for tests. Never used by production code."""

import json

from app.attestations import PublishError, PublishResult


class FakePublisher:
    """Records published events; can simulate a relay outage."""

    def __init__(self, *, fail: bool = False) -> None:
        self.published: list[str] = []
        self._fail = fail

    async def publish(self, event_json: str) -> PublishResult:
        event_id = str(json.loads(event_json)["id"])
        if self._fail:
            raise PublishError(f"only 0 of 2 required relays accepted event {event_id}")
        self.published.append(event_json)
        return PublishResult(event_id=event_id, accepted=("wss://fake.relay",))
