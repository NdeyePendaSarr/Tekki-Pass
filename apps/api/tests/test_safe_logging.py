"""Request logs: useful (id, route, status, duration) and free of personal data."""

import io
import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.attestations import IssuerKeys
from app.config import Settings
from app.lightning.fake import FakeWalletResolver
from app.main import create_app
from app.observability import JsonFormatter, RequestLogMiddleware
from tests.database import TEST_DATABASE_URL
from tests.fakes.fake_publisher import FakePublisher

PHONE = "77 123 45 67"
#: Every way the phone number could appear once normalized.
PHONE_FORMS = ("77 123 45 67", "771234567", "+221771234567", "221771234567")


@pytest.fixture
def logs() -> Iterator[io.StringIO]:
    """Everything the API's loggers write, formatted exactly as in production."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    app_logger = logging.getLogger("app")
    app_logger.addHandler(handler)
    previous_level = app_logger.level
    app_logger.setLevel(logging.INFO)
    yield stream
    app_logger.removeHandler(handler)
    app_logger.setLevel(previous_level)


def lines(stream: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def request_lines(stream: io.StringIO) -> list[dict[str, Any]]:
    return [entry for entry in lines(stream) if entry["logger"] == "app.http"]


@pytest.fixture
def client() -> Iterator[TestClient]:
    issuer = IssuerKeys.generate()
    settings = Settings(
        database_url=TEST_DATABASE_URL,
        client_phone_pepper=SecretStr("test-pepper"),
        nostr_issuer_nsec=SecretStr(issuer._keys.secret_key().to_hex()),
        nip98_required=False,
        publish_badge_definition_on_startup=False,
    )
    app = create_app(settings, wallets=FakeWalletResolver(), publisher=FakePublisher())
    with TestClient(app) as test_client:
        yield test_client


def test_full_flow_logs_no_token_and_no_phone(client: TestClient, logs: io.StringIO) -> None:
    artisan = IssuerKeys.generate().public_key
    created = client.post(
        "/attestation-requests", json={"artisan_pubkey": artisan, "title": "Carrelage, 9 m²"}
    )
    token = created.json()["token"]
    client.get(f"/attestation-requests/{token}")
    client.post(f"/attestation-requests/{token}/confirm", json={"client_phone": PHONE})
    client.post(f"/dev/attestation-requests/{token}/simulate-payment")
    published = client.post(f"/attestation-requests/{token}/refresh")
    assert published.json()["status"] == "published"

    output = logs.getvalue()
    assert token not in output
    for form in PHONE_FORMS:
        assert form not in output

    routes = [(entry["method"], entry["route"], entry["status"]) for entry in request_lines(logs)]
    assert routes == [
        ("POST", "/attestation-requests", 201),
        ("GET", "/attestation-requests/{token}", 200),
        ("POST", "/attestation-requests/{token}/confirm", 200),
        ("POST", "/dev/attestation-requests/{token}/simulate-payment", 200),
        ("POST", "/attestation-requests/{token}/refresh", 200),
    ]


def test_request_line_has_id_duration_and_nothing_else(
    client: TestClient, logs: io.StringIO
) -> None:
    response = client.get(
        "/health?phone=771234567",
        headers={"Authorization": "Nostr c2VjcmV0", "X-Forwarded-For": "203.0.113.7"},
    )

    [entry] = request_lines(logs)
    assert set(entry) == {
        "time",
        "level",
        "logger",
        "message",
        "request_id",
        "method",
        "route",
        "status",
        "duration_ms",
    }
    assert entry["request_id"] == response.headers["X-Request-ID"]
    assert entry["duration_ms"] >= 0
    output = logs.getvalue()
    for secret in ("771234567", "c2VjcmV0", "203.0.113.7", "testclient"):
        assert secret not in output


def test_unknown_paths_are_not_logged_verbatim(client: TestClient, logs: io.StringIO) -> None:
    assert client.get("/clients/771234567").status_code == 404

    [entry] = request_lines(logs)
    assert entry["route"] == "unmatched"
    assert "771234567" not in logs.getvalue()


def test_a_well_formed_request_id_is_kept(client: TestClient, logs: io.StringIO) -> None:
    response = client.get("/health", headers={"X-Request-ID": "caddy-3f2a9c1e"})

    assert response.headers["X-Request-ID"] == "caddy-3f2a9c1e"
    assert request_lines(logs)[0]["request_id"] == "caddy-3f2a9c1e"


@pytest.mark.parametrize("bad", ["77 123 45 67", "short", "x" * 65, "id;drop"])
def test_any_other_request_id_is_replaced(client: TestClient, logs: io.StringIO, bad: str) -> None:
    response = client.get("/health", headers={"X-Request-ID": bad})

    assert response.headers["X-Request-ID"] != bad
    assert bad not in logs.getvalue()


def test_failures_are_logged_as_500_with_the_request_id(logs: io.StringIO) -> None:
    app = FastAPI()

    @app.get("/boom/{token}")
    def boom(token: str) -> None:
        raise RuntimeError("unexpected")

    app.add_middleware(RequestLogMiddleware)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        assert test_client.get("/boom/secret-token-123").status_code == 500

    [entry] = request_lines(logs)
    assert (entry["route"], entry["status"]) == ("/boom/{token}", 500)
    assert "secret-token-123" not in logs.getvalue()
