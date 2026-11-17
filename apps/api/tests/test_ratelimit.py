"""Tests for per-client rate limiting."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from app.config import Settings
from app.lightning.fake import FakeWalletResolver
from app.main import create_app
from app.ratelimit import ClientIdentifier, RateLimiter, retry_after_header
from tests.database import TEST_DATABASE_URL
from tests.fakes.fake_publisher import FakePublisher

ARTISAN = "a" * 64


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


# --- Limiter -----------------------------------------------------------------------


def test_allows_up_to_the_limit_then_says_how_long_to_wait() -> None:
    clock = FakeClock()
    limiter = RateLimiter(clock=clock)

    assert [limiter.hit("create", "1.2.3.4", 3, 60) for _ in range(3)] == [None, None, None]
    clock.now += 15
    assert limiter.hit("create", "1.2.3.4", 3, 60) == pytest.approx(45)


def test_window_slides() -> None:
    clock = FakeClock()
    limiter = RateLimiter(clock=clock)
    for _ in range(2):
        limiter.hit("create", "ip", 2, 60)

    clock.now += 60

    assert limiter.hit("create", "ip", 2, 60) is None


def test_clients_and_buckets_are_counted_separately() -> None:
    limiter = RateLimiter(clock=FakeClock())
    limiter.hit("create", "ip-a", 1, 60)

    assert limiter.hit("create", "ip-b", 1, 60) is None
    assert limiter.hit("confirm", "ip-a", 1, 60) is None
    assert limiter.hit("create", "ip-a", 1, 60) is not None


def test_memory_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.ratelimit.MAX_TRACKED_KEYS", 10)
    clock = FakeClock()
    limiter = RateLimiter(clock=clock)

    for i in range(100):
        clock.now += 1
        limiter.hit("create", f"ip-{i}", 5, 60)

    assert len(limiter._hits) <= 10


@pytest.mark.parametrize(("seconds", "header"), [(0.2, "1"), (44.1, "45"), (60, "60")])
def test_retry_after_is_whole_seconds(seconds: float, header: str) -> None:
    assert retry_after_header(seconds) == header


# --- Client identification ---------------------------------------------------------


def test_forwarded_for_is_ignored_from_untrusted_peers() -> None:
    identify = ClientIdentifier(trusted_proxies=[]).identify

    # Anyone can send this header: without a trusted proxy it must not change the key.
    assert identify("203.0.113.9", "1.1.1.1") == "203.0.113.9"


def test_forwarded_for_is_used_behind_a_trusted_proxy() -> None:
    identify = ClientIdentifier(trusted_proxies=["10.0.0.0/8"]).identify

    assert identify("10.0.0.5", "198.51.100.7") == "198.51.100.7"
    # A client cannot hide behind a spoofed first entry: the rightmost untrusted hop wins.
    assert identify("10.0.0.5", "1.1.1.1, 198.51.100.7, 10.0.0.9") == "198.51.100.7"


def test_invalid_proxy_network_fails_at_startup() -> None:
    with pytest.raises(ValueError):
        ClientIdentifier(trusted_proxies=["not-a-network"])


# --- Routes ------------------------------------------------------------------------


def make_client(**overrides: object) -> TestClient:
    values: dict[str, object] = {
        "database_url": TEST_DATABASE_URL,
        "client_phone_pepper": SecretStr("test-pepper"),
        "nip98_required": False,
        "publish_badge_definition_on_startup": False,
        "rate_limit_create_per_minute": 2,
        "rate_limit_confirm_per_minute": 1,
    }
    values.update(overrides)
    app = create_app(
        Settings(**values),  # type: ignore[arg-type]
        wallets=FakeWalletResolver(),
        publisher=FakePublisher(),
    )
    return TestClient(app)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with make_client() as test_client:
        yield test_client


def create(client: TestClient, **headers: str) -> int:
    response = client.post(
        "/attestation-requests",
        json={"artisan_pubkey": ARTISAN, "title": "Carrelage"},
        headers=headers,
    )
    return response.status_code


def test_too_many_creations_get_429_with_retry_after(client: TestClient) -> None:
    assert [create(client), create(client)] == [201, 201]

    response = client.post(
        "/attestation-requests", json={"artisan_pubkey": ARTISAN, "title": "Carrelage"}
    )

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "rate_limited"
    assert 1 <= int(response.headers["retry-after"]) <= 60


def test_limits_are_per_route(client: TestClient) -> None:
    token = client.post(
        "/attestation-requests", json={"artisan_pubkey": ARTISAN, "title": "Carrelage"}
    ).json()["token"]

    confirmed = client.post(
        f"/attestation-requests/{token}/confirm", json={"client_phone": "771234567"}
    )
    second_confirm = client.post(
        f"/attestation-requests/{token}/confirm", json={"client_phone": "771234567"}
    )

    assert confirmed.status_code == 200
    assert second_confirm.status_code == 429
    # Creation still has budget left: its counter is separate.
    assert create(client) == 201


def test_reads_are_not_limited(client: TestClient) -> None:
    for _ in range(5):
        assert client.get("/health").status_code == 200


def test_spoofed_forwarded_for_does_not_bypass_the_limit(client: TestClient) -> None:
    statuses = [create(client, **{"X-Forwarded-For": f"1.1.1.{i}"}) for i in range(3)]

    assert statuses == [201, 201, 429]


def test_can_be_disabled() -> None:
    with make_client(rate_limit_enabled=False) as client:
        assert [create(client) for _ in range(4)] == [201, 201, 201, 201]


def test_limits_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(rate_limit_create_per_minute=0)
