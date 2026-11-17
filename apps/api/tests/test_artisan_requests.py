"""Tests for the artisan dashboard listing (GET /artisans/{pubkey}/requests)."""

import json
import secrets
from collections.abc import Iterator

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.attestations import IssuerKeys
from app.config import Settings
from app.lightning.fake import FakeWalletResolver
from app.main import create_app
from tests.fakes.fake_publisher import FakePublisher
from tests.test_nip98 import API, auth_header

Keys = IssuerKeys


def make_client(**overrides: object) -> TestClient:
    values: dict[str, object] = {
        "database_url": "sqlite+aiosqlite:///:memory:",
        "client_phone_pepper": SecretStr("test-pepper"),
        "publish_badge_definition_on_startup": False,
        "nip98_url_prefixes": [API],
    }
    values.update(overrides)
    app = create_app(
        Settings(**values),  # type: ignore[arg-type]
        wallets=FakeWalletResolver(),
        publisher=FakePublisher(),
    )
    return TestClient(app, base_url=API)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with make_client() as test_client:
        yield test_client


def create(client: TestClient, artisan: Keys, title: str) -> str:
    body = json.dumps({"artisan_pubkey": artisan.public_key, "title": title}).encode()
    response = client.post(
        "/attestation-requests",
        content=body,
        headers={
            "content-type": "application/json",
            "authorization": auth_header(artisan, url=API + "/attestation-requests", body=body),
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["token"])


def list_requests(client: TestClient, owner: Keys, signer: Keys | None) -> httpx.Response:
    path = f"/artisans/{owner.public_key}/requests"
    headers = {}
    if signer is not None:
        headers["authorization"] = auth_header(
            signer, url=API + path, method="GET", nonce=secrets.token_hex(8)
        )
    return client.get(path, headers=headers)


def test_artisan_sees_only_their_requests_newest_first(client: TestClient) -> None:
    moussa, other = Keys.generate(), Keys.generate()
    first = create(client, moussa, "Carrelage cuisine")
    second = create(client, moussa, "Pose de faïence")
    create(client, other, "Peinture salon")

    response = list_requests(client, moussa, signer=moussa)

    assert response.status_code == 200
    rows = response.json()
    assert [r["token"] for r in rows] == [second, first]
    assert {r["status"] for r in rows} == {"awaiting_client"}
    assert "client_hash" not in response.text


def test_status_follows_the_flow(client: TestClient) -> None:
    moussa = Keys.generate()
    token = create(client, moussa, "Carrelage cuisine")
    client.post(f"/attestation-requests/{token}/confirm", json={"client_phone": "771234567"})

    rows = list_requests(client, moussa, signer=moussa).json()

    assert rows[0]["status"] == "awaiting_payment"
    assert rows[0]["bolt11"].startswith("lnfake")


def test_unsigned_listing_is_refused_even_when_nip98_is_optional() -> None:
    # The list contains client links: it must never be readable without the artisan's key.
    with make_client(nip98_required=False) as client:
        response = list_requests(client, Keys.generate(), signer=None)

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "auth_required"


def test_cannot_list_someone_elses_requests(client: TestClient) -> None:
    moussa = Keys.generate()
    create(client, moussa, "Carrelage cuisine")

    response = list_requests(client, moussa, signer=Keys.generate())

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "auth_pubkey_mismatch"


def test_empty_list_for_a_new_artisan(client: TestClient) -> None:
    newcomer = Keys.generate()

    response = list_requests(client, newcomer, signer=newcomer)

    assert response.status_code == 200
    assert response.json() == []


def test_listing_is_rate_limited() -> None:
    moussa = Keys.generate()
    with make_client(rate_limit_list_per_minute=2) as client:
        statuses = [list_requests(client, moussa, signer=moussa).status_code for _ in range(3)]

    assert statuses == [200, 200, 429]


def test_identical_signed_reads_in_the_same_second_are_replays(client: TestClient) -> None:
    # Without a nonce, two GETs signed in the same second are the same event: the second
    # one is refused as a replay. The web app adds a random nonce tag to every signature.
    moussa = Keys.generate()
    path = f"/artisans/{moussa.public_key}/requests"
    header = auth_header(moussa, url=API + path, method="GET")

    first = client.get(path, headers={"authorization": header})
    replay = client.get(path, headers={"authorization": header})

    assert (first.status_code, replay.status_code) == (200, 401)


def test_invalid_pubkey_is_rejected(client: TestClient) -> None:
    assert client.get("/artisans/not-a-key/requests").status_code == 422
