"""Job attestations published as Nostr NIP-58 badge awards (see docs/adr/0002)."""

from app.attestations.models import Attestation, AttestationError, VerifiedAttestation
from app.attestations.nostr import (
    BADGE_IDENTIFIER,
    IssuerKeys,
    build_badge_definition,
    sign_attestation,
    verify_attestation,
)
from app.attestations.privacy import hash_client_phone
from app.attestations.relays import (
    EventPublisher,
    NostrRelayPublisher,
    PublishError,
    PublishResult,
)

__all__ = [
    "BADGE_IDENTIFIER",
    "Attestation",
    "AttestationError",
    "EventPublisher",
    "IssuerKeys",
    "NostrRelayPublisher",
    "PublishError",
    "PublishResult",
    "VerifiedAttestation",
    "build_badge_definition",
    "hash_client_phone",
    "sign_attestation",
    "verify_attestation",
]
