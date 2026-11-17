"""Tests for the demo data endpoint (fake backend only)."""

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.attestations import IssuerKeys, verify_attestation
from app.attestations.privacy import normalize_phone
from app.config import Settings
from app.lightning.fake import FakeWalletResolver
from app.main import create_app
from app.requests.demo import DEMO_JOBS, demo_client_phone
from tests.database import TEST_DATABASE_URL
from tests.fakes.fake_publisher import FakePublisher


@pytest.fixture
def issuer() -> IssuerKeys:
    return IssuerKeys.generate()


@pytest.fixture
def publisher() -> FakePublisher:
    return FakePublisher()


def make_client(issuer: IssuerKeys, publisher: FakePublisher, **overrides: object) -> TestClient:
    values: dict[str, object] = {
        "database_url": TEST_DATABASE_URL,
        "client_phone_pepper": SecretStr("test-pepper"),
        "nostr_issuer_nsec": SecretStr(issuer._keys.secret_key().to_hex()),
        "publish_badge_definition_on_startup": False,
    }
    values.update(overrides)
    app = create_app(
        Settings(**values),  # type: ignore[arg-type]
        wallets=FakeWalletResolver(),
        publisher=publisher,
    )
    return TestClient(app)


@pytest.fixture
def client(issuer: IssuerKeys, publisher: FakePublisher) -> Iterator[TestClient]:
    with make_client(issuer, publisher) as test_client:
        yield test_client


def test_seed_publishes_verifiable_attestations(
    client: TestClient, issuer: IssuerKeys, publisher: FakePublisher
) -> None:
    moussa = IssuerKeys.generate().public_key

    response = client.post(f"/dev/artisans/{moussa}/seed-demo")

    assert response.status_code == 201, response.text
    assert [r["status"] for r in response.json()] == ["published"] * len(DEMO_JOBS)
    assert [r["title"] for r in response.json()] == list(DEMO_JOBS)
    assert len(publisher.published) == len(DEMO_JOBS)
    for event_json in publisher.published:
        assert (
            verify_attestation(event_json, issuer.public_key).attestation.artisan_pubkey == moussa
        )


def test_seeded_jobs_appear_on_the_public_page(client: TestClient) -> None:
    moussa = IssuerKeys.generate().public_key
    client.post(f"/dev/artisans/{moussa}/seed-demo")

    listing = client.get(f"/artisans/{moussa}/attestations").json()

    assert sorted(a["title"] for a in listing) == sorted(DEMO_JOBS)


def test_seed_can_run_again_without_hitting_the_client_cap(client: TestClient) -> None:
    moussa = IssuerKeys.generate().public_key

    statuses = [client.post(f"/dev/artisans/{moussa}/seed-demo").status_code for _ in range(3)]

    assert statuses == [201, 201, 201]
    assert len(client.get(f"/artisans/{moussa}/attestations").json()) == 3 * len(DEMO_JOBS)


def test_seed_needs_the_issuer_key(publisher: FakePublisher) -> None:
    app = create_app(
        Settings(
            database_url=TEST_DATABASE_URL,
            client_phone_pepper=SecretStr("test-pepper"),
            publish_badge_definition_on_startup=False,
        ),
        wallets=FakeWalletResolver(),
        publisher=publisher,
    )
    with TestClient(app) as client:
        response = client.post(f"/dev/artisans/{'a' * 64}/seed-demo")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "not_configured"


def test_invalid_pubkey_is_rejected(client: TestClient) -> None:
    assert client.post("/dev/artisans/not-a-key/seed-demo").status_code == 422


def test_demo_phones_are_valid_and_distinct() -> None:
    phones = {demo_client_phone() for _ in range(20)}

    assert len(phones) == 20
    assert all(normalize_phone(p).startswith("22170") for p in phones)


def test_published_events_never_contain_a_phone_number(
    client: TestClient, publisher: FakePublisher
) -> None:
    client.post(f"/dev/artisans/{IssuerKeys.generate().public_key}/seed-demo")

    for event_json in publisher.published:
        assert "+22170" not in event_json
        assert "22170" not in json.loads(event_json)["content"]
