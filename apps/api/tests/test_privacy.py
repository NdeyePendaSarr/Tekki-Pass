"""Tests for client phone normalization and keyed hashing."""

import pytest

from app.attestations.privacy import hash_client_phone, normalize_phone
from app.config import Settings


@pytest.mark.parametrize(
    "phone",
    ["77 123 45 67", "771234567", "+221 77 123 45 67", "00221771234567", "+221-77-123-45-67"],
)
def test_same_number_normalizes_the_same_way(phone: str) -> None:
    assert normalize_phone(phone) == "221771234567"


@pytest.mark.parametrize("phone", ["", "12", "abc", "+1234567890123456"])
def test_rejects_invalid_numbers(phone: str) -> None:
    with pytest.raises(ValueError, match="phone"):
        normalize_phone(phone)


def test_hash_is_stable_keyed_and_hides_the_number() -> None:
    a = hash_client_phone("77 123 45 67", pepper="pepper-a")

    assert a == hash_client_phone("+221771234567", pepper="pepper-a")
    assert a != hash_client_phone("77 123 45 67", pepper="pepper-b")
    assert "771234567" not in a
    assert len(a) == 64


def test_pepper_is_required() -> None:
    with pytest.raises(ValueError, match="pepper"):
        hash_client_phone("771234567", pepper="")


def test_secrets_are_masked_in_settings() -> None:
    settings = Settings(nostr_issuer_nsec="super-secret", client_phone_pepper="pepper")

    assert "super-secret" not in repr(settings)
    assert "pepper" not in str(settings.client_phone_pepper)
