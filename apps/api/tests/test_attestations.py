"""Tests for signing and verifying NIP-58 attestations."""

import hashlib
import json
import secrets

import pytest

from app.attestations import (
    BADGE_IDENTIFIER,
    Attestation,
    AttestationError,
    IssuerKeys,
    build_badge_definition,
    hash_client_phone,
    sign_attestation,
    verify_attestation,
)
from app.attestations.models import attestation_id


def paid_attestation(**overrides: str) -> Attestation:
    """A valid attestation with a real preimage / payment hash pair."""
    preimage = secrets.token_hex(32)
    fields: dict[str, str] = {
        "artisan_pubkey": IssuerKeys.generate().public_key,
        "payment_hash": hashlib.sha256(bytes.fromhex(preimage)).hexdigest(),
        "preimage": preimage,
        "client_hash": hash_client_phone("77 123 45 67", pepper="test-pepper"),
        "title": "Carrelage salle de bain, 12 m²",
        "network": "testnet",
    }
    fields.update(overrides)
    return Attestation(**fields)  # type: ignore[arg-type]  # network is a valid literal


@pytest.fixture
def issuer() -> IssuerKeys:
    return IssuerKeys.generate()


def test_signed_attestation_verifies_and_round_trips(issuer: IssuerKeys) -> None:
    attestation = paid_attestation()

    verified = verify_attestation(sign_attestation(attestation, issuer), issuer.public_key)

    assert verified.attestation == attestation
    assert verified.issuer_pubkey == issuer.public_key
    assert len(verified.event_id) == 64


def test_award_event_follows_nip58_and_hides_the_phone(issuer: IssuerKeys) -> None:
    attestation = paid_attestation()

    event = json.loads(sign_attestation(attestation, issuer))
    tags = {tag[0]: tag[1] for tag in event["tags"]}

    assert event["kind"] == 8
    assert tags["a"] == f"30009:{issuer.public_key}:{BADGE_IDENTIFIER}"
    assert tags["p"] == attestation.artisan_pubkey
    assert tags["attestation"] == attestation.id
    assert "771234567" not in json.dumps(event)


def test_badge_definition_is_addressable(issuer: IssuerKeys) -> None:
    event = json.loads(build_badge_definition(issuer))

    assert event["kind"] == 30009
    assert ["d", BADGE_IDENTIFIER] in event["tags"]


def test_unpaid_job_cannot_become_an_attestation() -> None:
    with pytest.raises(AttestationError, match="not paid"):
        paid_attestation(preimage=secrets.token_hex(32))


@pytest.mark.parametrize("title", ["", "x" * 141, " padded "])
def test_title_is_validated(title: str) -> None:
    with pytest.raises(AttestationError, match="title"):
        paid_attestation(title=title)


def test_rejects_another_issuer(issuer: IssuerKeys) -> None:
    event = sign_attestation(paid_attestation(), IssuerKeys.generate())

    with pytest.raises(AttestationError, match="unknown issuer"):
        verify_attestation(event, issuer.public_key)


def test_rejects_tampered_event(issuer: IssuerKeys) -> None:
    event = json.loads(sign_attestation(paid_attestation(), issuer))
    event["content"] = "Chantier inventé"

    with pytest.raises(AttestationError, match="signature"):
        verify_attestation(json.dumps(event), issuer.public_key)


def test_rejects_proof_replayed_for_another_artisan(issuer: IssuerKeys) -> None:
    original = paid_attestation()
    other_artisan = IssuerKeys.generate().public_key
    # A correctly signed event that reuses the original attestation ID for another artisan.
    forged = issuer.sign(
        8,
        original.title,
        [
            ["a", f"30009:{issuer.public_key}:{BADGE_IDENTIFIER}"],
            ["p", other_artisan],
            ["attestation", original.id],
            ["payment_hash", original.payment_hash],
            ["preimage", original.preimage],
            ["client", original.client_hash],
            ["network", "testnet"],
        ],
    )

    assert attestation_id(original.payment_hash, other_artisan) != original.id
    with pytest.raises(AttestationError, match="replay"):
        verify_attestation(forged, issuer.public_key)


def test_rejects_unknown_network(issuer: IssuerKeys) -> None:
    a = paid_attestation()
    event = issuer.sign(
        8,
        a.title,
        [
            ["a", f"30009:{issuer.public_key}:{BADGE_IDENTIFIER}"],
            ["p", a.artisan_pubkey],
            ["attestation", a.id],
            ["payment_hash", a.payment_hash],
            ["preimage", a.preimage],
            ["client", a.client_hash],
            ["network", "regtest"],
        ],
    )

    with pytest.raises(AttestationError, match="network"):
        verify_attestation(event, issuer.public_key)


def test_rejects_garbage_input(issuer: IssuerKeys) -> None:
    with pytest.raises(AttestationError, match="not a valid Nostr event"):
        verify_attestation("{not json", issuer.public_key)


def test_issuer_secret_is_never_exposed() -> None:
    secret = secrets.token_hex(32)
    keys = IssuerKeys(secret)

    assert secret not in repr(keys)
    with pytest.raises(AttestationError) as excinfo:
        IssuerKeys("nsec1-not-a-key-" + secret[:8])
    assert secret[:8] not in str(excinfo.value)
