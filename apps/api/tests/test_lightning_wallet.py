"""Contract tests for the `LightningWallet` interface, run against the fake."""

import hashlib

import pytest

from app.lightning import InvoiceNotFoundError, LightningWallet, PaymentStatus, preimage_matches
from tests.fakes.fake_wallet import FakeLightningWallet


def test_fake_satisfies_the_protocol(wallet: FakeLightningWallet) -> None:
    assert isinstance(wallet, LightningWallet)


@pytest.mark.anyio
async def test_new_invoice_is_unpaid(wallet: FakeLightningWallet) -> None:
    invoice = await wallet.create_invoice(amount_sat=210, memo="Carrelage cuisine")

    status = await wallet.check_payment(invoice.payment_hash)

    assert invoice.amount_sat == 210
    assert status == PaymentStatus(paid=False)


@pytest.mark.anyio
async def test_paid_invoice_reveals_a_valid_preimage(wallet: FakeLightningWallet) -> None:
    invoice = await wallet.create_invoice(amount_sat=210, memo="Carrelage cuisine")
    wallet.mark_paid(invoice.payment_hash)

    status = await wallet.check_payment(invoice.payment_hash)

    assert status.paid
    assert status.preimage is not None
    assert preimage_matches(status.preimage, invoice.payment_hash)


@pytest.mark.anyio
async def test_unknown_payment_hash_raises(wallet: FakeLightningWallet) -> None:
    with pytest.raises(InvoiceNotFoundError):
        await wallet.check_payment("00" * 32)


@pytest.mark.anyio
async def test_amount_must_be_positive(wallet: FakeLightningWallet) -> None:
    with pytest.raises(ValueError, match="positive"):
        await wallet.create_invoice(amount_sat=0, memo="x")


def test_preimage_matches_rejects_wrong_or_malformed_input() -> None:
    preimage = "11" * 32
    payment_hash = hashlib.sha256(bytes.fromhex(preimage)).hexdigest()

    assert preimage_matches(preimage, payment_hash.upper())
    assert not preimage_matches("22" * 32, payment_hash)
    assert not preimage_matches("not-hex", payment_hash)


@pytest.mark.parametrize(("paid", "preimage"), [(True, None), (False, "11" * 32)])
def test_payment_status_enforces_preimage_invariant(paid: bool, preimage: str | None) -> None:
    with pytest.raises(ValueError, match="preimage"):
        PaymentStatus(paid=paid, preimage=preimage)
