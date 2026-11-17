"""Tests for the liveness endpoint."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.database import TEST_DATABASE_URL


def test_health_reports_ok_and_network() -> None:
    settings = Settings(network="testnet", database_url=TEST_DATABASE_URL)
    with TestClient(create_app(settings)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "network": "testnet"}


def test_network_defaults_to_testnet() -> None:
    assert Settings().network == "testnet"
