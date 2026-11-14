"""Domain model of an attestation, independent of the Nostr encoding."""

import hashlib
import re
from dataclasses import dataclass

from app.config import Network
from app.lightning import preimage_matches

_HEX64 = re.compile(r"^[0-9a-f]{64}$")

#: Short job title written by the artisan. Kept small: it is public and permanent on relays.
MAX_TITLE_LENGTH = 140


class AttestationError(ValueError):
    """Raised when an attestation is invalid, either before signing or when verifying one."""


def attestation_id(payment_hash: str, artisan_pubkey: str) -> str:
    """Unique ID binding one payment to one artisan.

    Reusing a payment proof for another artisan yields a different ID, which the
    verifier detects (anti-replay, see the threat model in the README).
    """
    return hashlib.sha256(f"{payment_hash}:{artisan_pubkey}".encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Attestation:
    """A paid, client-confirmed job, ready to be signed by the issuer.

    All hex values are lower-case. Construction fails if the proof of payment is
    invalid, so an unpaid job can never be signed.
    """

    #: Artisan's Nostr public key (hex), the badge recipient.
    artisan_pubkey: str
    #: Hex SHA-256 of the Lightning preimage.
    payment_hash: str
    #: Hex preimage revealed by the paid invoice: the proof of payment.
    preimage: str
    #: Keyed hash of the client's phone number (see privacy.hash_client_phone). Never the number.
    client_hash: str
    title: str
    network: Network

    def __post_init__(self) -> None:
        for name in ("artisan_pubkey", "payment_hash", "preimage", "client_hash"):
            if not _HEX64.fullmatch(getattr(self, name)):
                raise AttestationError(f"{name} must be 64 lower-case hex characters")
        if not preimage_matches(self.preimage, self.payment_hash):
            raise AttestationError("preimage does not match payment_hash: job not paid")
        title = self.title.strip()
        if not title or len(title) > MAX_TITLE_LENGTH:
            raise AttestationError(f"title must be 1 to {MAX_TITLE_LENGTH} characters")
        if title != self.title:
            raise AttestationError("title must not have leading or trailing spaces")

    @property
    def id(self) -> str:
        """Attestation ID derived from the payment and the artisan."""
        return attestation_id(self.payment_hash, self.artisan_pubkey)


@dataclass(frozen=True, slots=True)
class VerifiedAttestation:
    """An attestation read back from a signed Nostr event and fully checked."""

    attestation: Attestation
    #: Nostr event ID (hex).
    event_id: str
    issuer_pubkey: str
    #: Unix timestamp at which the issuer signed the event.
    issued_at: int
