"""Tests for NIP-98 authentication of artisans."""

import base64
import hashlib
import json
import time
from collections.abc import Iterator

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.attestations import IssuerKeys
from app.auth import Nip98Error, Nip98Verifier
from app.config import Settings
from app.lightning.fake import FakeWalletResolver
from app.main import create_app
from tests.database import TEST_DATABASE_URL
from tests.fakes.fake_publisher import FakePublisher

API = "http://localhost:8000"
PROXY = "http://localhost:3000/api"
PATH = "/attestation-requests"

# Any key pair can sign NIP-98 events; IssuerKeys is our typed wrapper around nostr-sdk.
Keys = IssuerKeys


def auth_header(
    keys: Keys,
    *,
    url: str = API + PATH,
    method: str = "POST",
    body: bytes = b"",
    kind: int = 27235,
    payload: str | None = None,
    nonce: str | None = None,
) -> str:
    tags = [["u", url], ["method", method]]
    if nonce is not None:
        # Extra tags are allowed by NIP-98; a nonce makes two requests in the same second differ.
        tags.append(["nonce", nonce])
    if body or payload is not None:
        tags.append(
            ["payload", payload if payload is not None else hashlib.sha256(body).hexdigest()]
        )
    event_json = keys.sign(kind, "", tags)
    return "Nostr " + base64.b64encode(event_json.encode()).decode()


@pytest.fixture
def verifier() -> Nip98Verifier:
    return Nip98Verifier([API, PROXY])


# --- Verifier ----------------------------------------------------------------------


def test_valid_header_returns_the_signer(verifier: Nip98Verifier) -> None:
    keys = Keys.generate()
    body = b'{"title":"Carrelage"}'

    signer = verifier.verify(auth_header(keys, body=body), "POST", PATH, body)

    assert signer == keys.public_key


def test_url_signed_through_the_web_proxy_is_accepted(verifier: Nip98Verifier) -> None:
    keys = Keys.generate()

    assert (
        verifier.verify(auth_header(keys, url=PROXY + PATH), "POST", PATH, b"") == keys.public_key
    )


@pytest.mark.parametrize(
    ("header_kwargs", "message"),
    [
        ({"url": "https://evil.example" + PATH}, "URL"),
        ({"url": API + "/other"}, "URL"),
        ({"method": "GET"}, "method"),
        ({"kind": 1}, "kind"),
        ({"payload": "00" * 32}, "payload"),
    ],
)
def test_rejects_events_signed_for_something_else(
    verifier: Nip98Verifier, header_kwargs: dict[str, object], message: str
) -> None:
    header = auth_header(Keys.generate(), body=b"{}", **header_kwargs)  # type: ignore[arg-type]

    with pytest.raises(Nip98Error, match=message) as excinfo:
        verifier.verify(header, "POST", PATH, b"{}")
    assert excinfo.value.code == "invalid_auth"


def test_rejects_a_missing_header(verifier: Nip98Verifier) -> None:
    with pytest.raises(Nip98Error) as excinfo:
        verifier.verify(None, "POST", PATH, b"")
    assert excinfo.value.code == "auth_required"


@pytest.mark.parametrize(
    "header", ["Bearer abc", "Nostr not-base64!!", "Nostr " + base64.b64encode(b"{}").decode()]
)
def test_rejects_malformed_headers(verifier: Nip98Verifier, header: str) -> None:
    with pytest.raises(Nip98Error) as excinfo:
        verifier.verify(header, "POST", PATH, b"")
    assert excinfo.value.code == "invalid_auth"


def test_rejects_a_tampered_event(verifier: Nip98Verifier) -> None:
    keys = Keys.generate()
    event = json.loads(base64.b64decode(auth_header(keys).removeprefix("Nostr ")))
    event["tags"][1] = ["method", "DELETE"]
    tampered = "Nostr " + base64.b64encode(json.dumps(event).encode()).decode()

    with pytest.raises(Nip98Error, match=r"signature|not a Nostr event"):
        verifier.verify(tampered, "DELETE", PATH, b"")


def test_rejects_old_events() -> None:
    later = Nip98Verifier([API], clock=lambda: time.time() + 120)

    with pytest.raises(Nip98Error, match="expired"):
        later.verify(auth_header(Keys.generate()), "POST", PATH, b"")


def test_rejects_a_replayed_header(verifier: Nip98Verifier) -> None:
    header = auth_header(Keys.generate())
    verifier.verify(header, "POST", PATH, b"")

    with pytest.raises(Nip98Error, match="already used"):
        verifier.verify(header, "POST", PATH, b"")


# --- Route -------------------------------------------------------------------------


def make_client(*, required: bool) -> TestClient:
    settings = Settings(
        database_url=TEST_DATABASE_URL,
        client_phone_pepper=SecretStr("test-pepper"),
        nip98_required=required,
        nip98_url_prefixes=[API],
    )
    return TestClient(
        create_app(settings, wallets=FakeWalletResolver(), publisher=FakePublisher()),
        base_url=API,
    )


@pytest.fixture
def strict_client() -> Iterator[TestClient]:
    with make_client(required=True) as client:
        yield client


def post_request(
    client: TestClient, keys: Keys, signer: Keys | None, **header_kwargs: object
) -> httpx.Response:
    body = json.dumps({"artisan_pubkey": keys.public_key, "title": "Carrelage cuisine"}).encode()
    headers = {"content-type": "application/json"}
    if signer is not None:
        headers["authorization"] = auth_header(signer, body=body, **header_kwargs)  # type: ignore[arg-type]
    return client.post(PATH, content=body, headers=headers)


def test_signed_request_by_the_artisan_is_created(strict_client: TestClient) -> None:
    artisan = Keys.generate()

    response = post_request(strict_client, artisan, signer=artisan)

    assert response.status_code == 201, response.text


def test_unsigned_request_is_refused_when_required(strict_client: TestClient) -> None:
    response = post_request(strict_client, Keys.generate(), signer=None)

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "auth_required"


def test_cannot_create_a_request_in_someone_elses_name(strict_client: TestClient) -> None:
    response = post_request(strict_client, Keys.generate(), signer=Keys.generate())

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "auth_pubkey_mismatch"


def test_body_changed_after_signing_is_refused(strict_client: TestClient) -> None:
    artisan = Keys.generate()

    response = post_request(strict_client, artisan, signer=artisan, payload="00" * 32)

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_auth"


def test_optional_mode_still_rejects_a_bad_header() -> None:
    with make_client(required=False) as client:
        unsigned = post_request(client, Keys.generate(), signer=None)
        forged = post_request(client, Keys.generate(), signer=Keys.generate())

    assert unsigned.status_code == 201
    assert forged.status_code == 403


def test_auth_is_required_by_default() -> None:
    assert Settings().nip98_required is True
