"""Tests for the liveness endpoint."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_reports_ok_and_network() -> None:
    client = TestClient(create_app(Settings(network="mainnet")))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "network": "mainnet"}


def test_network_defaults_to_testnet() -> None:
    assert Settings().network == "testnet"
