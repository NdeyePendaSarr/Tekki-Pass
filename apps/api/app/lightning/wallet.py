"""Interface between the API and the artisan's self-custodial Lightning wallet.

The rest of the code depends only on `LightningWallet`, never on a vendor SDK.
Swapping SDKs (see docs/adr/0001) then means writing one new adapter class.

A paid Lightning invoice reveals a *preimage* whose SHA-256 equals the
invoice's *payment hash*. That pair is the cryptographic proof of payment
attached to each attestation.
"""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


class InvoiceNotFoundError(LookupError):
    """Raised when a payment hash does not match any invoice known to the wallet."""


@dataclass(frozen=True, slots=True)
class Invoice:
    """A BOLT 11 invoice the client pays to attest a job."""

    #: Encoded invoice shown to the payer (QR code / deep link).
    bolt11: str
    #: Hex-encoded SHA-256 of the preimage; identifies the payment.
    payment_hash: str
    amount_sat: int
    memo: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class PaymentStatus:
    """Result of a payment lookup.

    Invariant: `preimage` is present if and only if the invoice is paid.
    """

    paid: bool
    #: Hex-encoded 32-byte preimage, revealed only once the invoice is settled.
    preimage: str | None = None

    def __post_init__(self) -> None:
        if self.paid and self.preimage is None:
            raise ValueError("a paid invoice must carry its preimage")
        if not self.paid and self.preimage is not None:
            raise ValueError("an unpaid invoice cannot have a preimage")


@runtime_checkable
class LightningWallet(Protocol):
    """Operations the API needs from a Lightning wallet.

    Methods are async because every real implementation talks to a node or
    a service over the network.
    """

    async def create_invoice(
        self, amount_sat: int, memo: str, expiry_seconds: int = 3600
    ) -> Invoice:
        """Create an invoice payable to the artisan's wallet."""
        ...

    async def check_payment(self, payment_hash: str) -> PaymentStatus:
        """Return whether the invoice is paid and, if so, its preimage.

        Raises:
            InvoiceNotFoundError: if the payment hash is unknown.
        """
        ...


def preimage_matches(preimage_hex: str, payment_hash_hex: str) -> bool:
    """Check that `sha256(preimage) == payment_hash` (the proof of payment).

    Uses a constant-time comparison. Returns False on malformed hex input
    instead of raising, so callers treat every mismatch the same way.
    """
    try:
        digest = hashlib.sha256(bytes.fromhex(preimage_hex)).hexdigest()
    except ValueError:
        return False
    return hmac.compare_digest(digest, payment_hash_hex.lower())
