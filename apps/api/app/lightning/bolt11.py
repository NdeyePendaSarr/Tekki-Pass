"""Read the fields the API needs from a BOLT 11 invoice.

Spec: https://github.com/lightning/bolts/blob/master/11-payment-encoding.md

Only what the API checks is decoded: network, amount, payment hash, timestamp and
expiry. The bech32 checksum is verified, so a mistyped or truncated invoice is
rejected. The node signature is not checked: the proof of payment that matters to
the API is `sha256(preimage) == payment_hash`, checked when the invoice is paid.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_GENERATOR = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)

#: Signature: 65 bytes = 104 five-bit words, at the end of the data part.
_SIGNATURE_WORDS = 104
_TIMESTAMP_WORDS = 7
_TAG_PAYMENT_HASH = _CHARSET.index("p")
_TAG_EXPIRY = _CHARSET.index("x")
_DEFAULT_EXPIRY_SECONDS = 3600

#: Currency prefix of the human-readable part, by network ("bcrt" before "bc").
_PREFIXES = {"bcrt": "regtest", "bc": "mainnet", "tbs": "signet", "tb": "testnet"}
_HRP = re.compile(r"^ln(bcrt|bc|tbs|tb)(?:(\d+)([munp]?))?$")
#: Millisatoshis per unit: 1 BTC = 10^11 msat.
_MSAT_PER_UNIT = {"": 10**11, "m": 10**8, "u": 10**5, "n": 10**2}

#: Longer strings are refused before any work (real invoices are under 2 000 chars).
MAX_INVOICE_LENGTH = 7089


class InvalidInvoiceError(ValueError):
    """The string is not a well-formed BOLT 11 invoice."""


@dataclass(frozen=True, slots=True)
class DecodedInvoice:
    #: "mainnet", "testnet", "signet" or "regtest".
    network: str
    #: None for "any amount" invoices.
    amount_msat: int | None
    payment_hash: str
    created_at: datetime
    expires_at: datetime


def decode(invoice: str) -> DecodedInvoice:
    """Decode a BOLT 11 invoice, or raise InvalidInvoiceError."""
    if len(invoice) > MAX_INVOICE_LENGTH:
        raise InvalidInvoiceError("invoice too long")
    if invoice != invoice.lower() and invoice != invoice.upper():
        raise InvalidInvoiceError("mixed case")
    invoice = invoice.lower().removeprefix("lightning:")
    hrp, separator, data_part = invoice.rpartition("1")
    if not separator or not hrp:
        raise InvalidInvoiceError("no bech32 separator")
    try:
        words = [_CHARSET.index(char) for char in data_part]
    except ValueError:
        raise InvalidInvoiceError("invalid bech32 character") from None
    if _polymod(_hrp_expand(hrp) + words) != 1:
        raise InvalidInvoiceError("bad checksum")
    words = words[:-6]  # checksum
    if len(words) < _TIMESTAMP_WORDS + _SIGNATURE_WORDS:
        raise InvalidInvoiceError("invoice too short")

    network, amount_msat = _parse_hrp(hrp)
    tagged = words[_TIMESTAMP_WORDS:-_SIGNATURE_WORDS]
    timestamp = _to_int(words[:_TIMESTAMP_WORDS])

    payment_hash: str | None = None
    expiry = _DEFAULT_EXPIRY_SECONDS
    position = 0
    while position < len(tagged):
        if position + 3 > len(tagged):
            raise InvalidInvoiceError("truncated tagged field")
        tag = tagged[position]
        length = tagged[position + 1] * 32 + tagged[position + 2]
        value = tagged[position + 3 : position + 3 + length]
        if len(value) != length:
            raise InvalidInvoiceError("truncated tagged field")
        position += 3 + length
        if tag == _TAG_PAYMENT_HASH:
            # The spec says to skip p fields of the wrong length; two valid ones are invalid.
            if length != 52:
                continue
            if payment_hash is not None:
                raise InvalidInvoiceError("more than one payment hash")
            payment_hash = _to_bytes(value)[:32].hex()
        elif tag == _TAG_EXPIRY:
            expiry = _to_int(value)

    if payment_hash is None:
        raise InvalidInvoiceError("no payment hash")
    created_at = datetime.fromtimestamp(timestamp, UTC)
    return DecodedInvoice(
        network=network,
        amount_msat=amount_msat,
        payment_hash=payment_hash,
        created_at=created_at,
        expires_at=created_at + timedelta(seconds=expiry),
    )


def _parse_hrp(hrp: str) -> tuple[str, int | None]:
    match = _HRP.fullmatch(hrp)
    if match is None:
        raise InvalidInvoiceError("unknown currency prefix")
    currency, amount, multiplier = match.groups()
    network = _PREFIXES[currency]
    if amount is None:
        return network, None
    if amount.startswith("0"):
        raise InvalidInvoiceError("amount with leading zero")
    if multiplier == "p":
        # Pico-bitcoin: 0.1 msat, so the amount must be a multiple of 10.
        if int(amount) % 10:
            raise InvalidInvoiceError("sub-millisatoshi amount")
        return network, int(amount) // 10
    return network, int(amount) * _MSAT_PER_UNIT[multiplier]


def _to_int(words: list[int]) -> int:
    value = 0
    for word in words:
        value = value * 32 + word
    return value


def _to_bytes(words: list[int]) -> bytes:
    """Regroup 5-bit words into bytes, dropping the trailing padding bits."""
    accumulator = bits = 0
    out = bytearray()
    for word in words:
        accumulator = (accumulator << 5) | word
        bits += 5
        if bits >= 8:
            bits -= 8
            out.append((accumulator >> bits) & 0xFF)
    return bytes(out)


def _hrp_expand(hrp: str) -> list[int]:
    return [ord(char) >> 5 for char in hrp] + [0] + [ord(char) & 31 for char in hrp]


def _polymod(values: list[int]) -> int:
    checksum = 1
    for value in values:
        top = checksum >> 25
        checksum = ((checksum & 0x1FFFFFF) << 5) ^ value
        for i, generator in enumerate(_GENERATOR):
            if (top >> i) & 1:
                checksum ^= generator
    return checksum
