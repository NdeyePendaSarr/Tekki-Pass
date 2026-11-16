"""End-to-end tests of the attestation flow through the HTTP API.

artisan creates a request -> client confirms -> client pays (simulated)
-> refresh -> attestation signed, published and verifiable.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.attestations import IssuerKeys, verify_attestation
from app.config import Settings
from app.lightning.fake import FakeWalletResolver
from app.main import create_app
from tests.fakes.fake_publisher import FakePublisher

PHONE = "77 123 45 67"


@pytest.fixture
def issuer() -> IssuerKeys:
    return IssuerKeys.generate()


@pytest.fixture
def artisan() -> str:
    return IssuerKeys.generate().public_key


@pytest.fixture
def publisher() -> FakePublisher:
    return FakePublisher()


def make_settings(issuer: IssuerKeys | None, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "sqlite+aiosqlite:///:memory:",
        "client_phone_pepper": SecretStr("test-pepper"),
        "nostr_issuer_nsec": SecretStr(issuer._keys.secret_key().to_hex()) if issuer else None,
        "max_attestations_per_client": 2,
        # These tests cover the flow itself; NIP-98 has its own tests in test_nip98.py.
        "nip98_required": False,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


@pytest.fixture
def client(issuer: IssuerKeys, publisher: FakePublisher) -> Iterator[TestClient]:
    app = create_app(make_settings(issuer), wallets=FakeWalletResolver(), publisher=publisher)
    with TestClient(app) as test_client:  # runs the lifespan: creates the SQLite schema
        yield test_client


def create(client: TestClient, artisan: str, title: str = "Carrelage cuisine, 9 m²") -> str:
    response = client.post(
        "/attestation-requests", json={"artisan_pubkey": artisan, "title": title}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["token"])


def test_full_flow_publishes_a_verifiable_attestation(
    client: TestClient, artisan: str, issuer: IssuerKeys, publisher: FakePublisher
) -> None:
    token = create(client, artisan)

    seen = client.get(f"/attestation-requests/{token}").json()
    assert seen["status"] == "awaiting_client"
    assert seen["amount_sat"] == 210

    confirmed = client.post(f"/attestation-requests/{token}/confirm", json={"client_phone": PHONE})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "awaiting_payment"
    assert confirmed.json()["bolt11"].startswith("lnfake")

    unpaid = client.post(f"/attestation-requests/{token}/refresh").json()
    assert unpaid["status"] == "awaiting_payment"

    assert client.post(f"/dev/attestation-requests/{token}/simulate-payment").status_code == 200
    published = client.post(f"/attestation-requests/{token}/refresh").json()
    assert published["status"] == "published"
    assert len(publisher.published) == 1

    verified = verify_attestation(publisher.published[0], issuer.public_key)
    assert verified.attestation.artisan_pubkey == artisan
    assert verified.event_id == published["event_id"]

    listing = client.get(f"/artisans/{artisan}/attestations").json()
    assert [a["event_id"] for a in listing] == [published["event_id"]]
    assert client.get("/issuer").json()["pubkey"] == issuer.public_key


def test_refresh_is_idempotent(client: TestClient, artisan: str, publisher: FakePublisher) -> None:
    token = create(client, artisan)
    client.post(f"/attestation-requests/{token}/confirm", json={"client_phone": PHONE})
    client.post(f"/dev/attestation-requests/{token}/simulate-payment")

    first = client.post(f"/attestation-requests/{token}/refresh").json()
    second = client.post(f"/attestation-requests/{token}/refresh").json()

    assert first == second
    assert len(publisher.published) == 1


def test_responses_never_expose_the_client(client: TestClient, artisan: str) -> None:
    token = create(client, artisan)
    body = client.post(f"/attestation-requests/{token}/confirm", json={"client_phone": PHONE}).text

    assert "client_hash" not in body
    assert "771234567" not in body


def test_cannot_confirm_twice(client: TestClient, artisan: str) -> None:
    token = create(client, artisan)
    client.post(f"/attestation-requests/{token}/confirm", json={"client_phone": PHONE})

    again = client.post(f"/attestation-requests/{token}/confirm", json={"client_phone": PHONE})

    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "invalid_state"


def test_client_cap_limits_collusion(client: TestClient, artisan: str) -> None:
    for _ in range(2):  # cap is 2 in these tests
        token = create(client, artisan)
        ok = client.post(f"/attestation-requests/{token}/confirm", json={"client_phone": PHONE})
        assert ok.status_code == 200

    token = create(client, artisan)
    blocked = client.post(
        f"/attestation-requests/{token}/confirm", json={"client_phone": "+221771234567"}
    )

    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "client_cap_reached"


def test_relay_outage_keeps_the_payment_and_can_be_retried(
    issuer: IssuerKeys, artisan: str
) -> None:
    wallets = FakeWalletResolver()
    down = create_app(make_settings(issuer), wallets=wallets, publisher=FakePublisher(fail=True))
    with TestClient(down) as client:
        token = create(client, artisan)
        client.post(f"/attestation-requests/{token}/confirm", json={"client_phone": PHONE})
        client.post(f"/dev/attestation-requests/{token}/simulate-payment")

        failed = client.post(f"/attestation-requests/{token}/refresh")
        assert failed.status_code == 502
        assert failed.json()["detail"]["code"] == "publication_failed"
        assert client.get(f"/attestation-requests/{token}").json()["status"] == "paid"


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"artisan_pubkey": "not-hex", "title": "ok"}, "artisan_pubkey"),
        ({"artisan_pubkey": "a" * 64, "title": ""}, "title"),
        ({"artisan_pubkey": "a" * 64, "title": "x" * 141}, "title"),
        ({"artisan_pubkey": "a" * 64, "title": "ok", "lightning_address": "nope"}, "lightning"),
    ],
)
def test_create_validates_input(client: TestClient, payload: dict[str, str], field: str) -> None:
    response = client.post("/attestation-requests", json=payload)

    assert response.status_code == 422
    assert field in response.text


def test_invalid_phone_is_rejected(client: TestClient, artisan: str) -> None:
    token = create(client, artisan)

    response = client.post(
        f"/attestation-requests/{token}/confirm", json={"client_phone": "pas un numéro"}
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_phone"


def test_unknown_token_is_404(client: TestClient) -> None:
    response = client.get("/attestation-requests/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "not_found"


def test_missing_secrets_are_reported_as_server_configuration(artisan: str) -> None:
    app = create_app(
        make_settings(None, client_phone_pepper=None),
        wallets=FakeWalletResolver(),
        publisher=FakePublisher(),
    )
    with TestClient(app) as client:
        token = create(client, artisan)
        response = client.post(
            f"/attestation-requests/{token}/confirm", json={"client_phone": PHONE}
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "not_configured"


def test_fake_backend_is_refused_on_mainnet_and_public_relays() -> None:
    with pytest.raises(ValueError, match="only allowed on testnet"):
        Settings(network="mainnet")
    with pytest.raises(ValueError, match="local relays"):
        Settings(nostr_relays=["wss://nos.lol"])


def test_dev_secrets_are_generated_only_when_enabled() -> None:
    assert Settings().with_dev_secrets().nostr_issuer_nsec is None

    filled = Settings(dev_generate_missing_secrets=True).with_dev_secrets()

    assert filled.nostr_issuer_nsec is not None
    assert filled.client_phone_pepper is not None
