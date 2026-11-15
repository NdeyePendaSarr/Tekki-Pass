"""In-memory `LightningWallet` with invoices settled on demand.

Used by the tests and by the "fake" Lightning backend for local development and
demos before the real wallet is wired (docs/adr/0005). Refused on mainnet by
the settings. It mimics the real protocol: each invoice gets a random 32-byte
preimage and `payment_hash = sha256(preimage)`, so proof-of-payment checks
behave exactly as they will with a real wallet.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.lightning import Invoice, InvoiceNotFoundError, PaymentStatus


@dataclass(slots=True)
class _Entry:
    invoice: Invoice
    preimage: str
    paid: bool = False


class FakeLightningWallet:
    """Fake wallet whose invoices are settled by calling `mark_paid`."""

    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}

    async def create_invoice(
        self, amount_sat: int, memo: str, expiry_seconds: int = 3600
    ) -> Invoice:
        if amount_sat <= 0:
            raise ValueError("amount_sat must be positive")
        preimage = secrets.token_bytes(32)
        payment_hash = hashlib.sha256(preimage).hexdigest()
        invoice = Invoice(
            # Deliberately fake encoding: never mistakable for a real BOLT 11 string.
            bolt11=f"lnfake{amount_sat}n1{payment_hash[:16]}",
            payment_hash=payment_hash,
            amount_sat=amount_sat,
            memo=memo,
            expires_at=datetime.now(UTC) + timedelta(seconds=expiry_seconds),
        )
        self._entries[payment_hash] = _Entry(invoice=invoice, preimage=preimage.hex())
        return invoice

    async def check_payment(self, payment_hash: str) -> PaymentStatus:
        entry = self._entry(payment_hash)
        if entry.paid:
            return PaymentStatus(paid=True, preimage=entry.preimage)
        return PaymentStatus(paid=False)

    def mark_paid(self, payment_hash: str) -> None:
        """Simulate the client paying the invoice."""
        self._entry(payment_hash).paid = True

    def _entry(self, payment_hash: str) -> _Entry:
        try:
            return self._entries[payment_hash]
        except KeyError:
            raise InvoiceNotFoundError(payment_hash) from None


class FakeWalletResolver:
    """Same fake wallet for every artisan (the "fake" backend in development)."""

    def __init__(self, wallet: FakeLightningWallet | None = None) -> None:
        self.wallet = wallet if wallet is not None else FakeLightningWallet()

    def wallet_for(self, lightning_address: str | None) -> FakeLightningWallet:
        return self.wallet
