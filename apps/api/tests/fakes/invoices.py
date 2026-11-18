"""Build BOLT 11 invoices for tests (unsigned: the API never checks the signature)."""

import time

_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_GENERATOR = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
_PREFIX = {"mainnet": "lnbc", "testnet": "lntb", "regtest": "lnbcrt"}


def make_invoice(
    payment_hash: str, amount_sat: int, *, network: str = "mainnet", expiry: int = 1800
) -> str:
    """A well-formed invoice of `amount_sat` (written in nano-bitcoin: 1 sat = 10n)."""
    hrp = f"{_PREFIX[network]}{amount_sat * 10}n"
    words = _int_words(int(time.time()), 7)
    words += _field("p", _bytes_to_words(bytes.fromhex(payment_hash)))
    words += _field("x", _int_words(expiry, 2))
    words += [0] * 104  # signature placeholder
    checksum = _polymod(_hrp_expand(hrp) + words + [0] * 6) ^ 1
    words += [(checksum >> 5 * (5 - i)) & 31 for i in range(6)]
    return hrp + "1" + "".join(_CHARSET[w] for w in words)


def _field(tag: str, data: list[int]) -> list[int]:
    return [_CHARSET.index(tag), len(data) // 32, len(data) % 32, *data]


def _int_words(value: int, count: int) -> list[int]:
    return [(value >> 5 * (count - 1 - i)) & 31 for i in range(count)]


def _bytes_to_words(data: bytes) -> list[int]:
    accumulator = bits = 0
    words: list[int] = []
    for byte in data:
        accumulator = (accumulator << 8) | byte
        bits += 8
        while bits >= 5:
            bits -= 5
            words.append((accumulator >> bits) & 31)
    if bits:
        words.append((accumulator << (5 - bits)) & 31)
    return words


def _hrp_expand(hrp: str) -> list[int]:
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _polymod(values: list[int]) -> int:
    checksum = 1
    for value in values:
        top = checksum >> 25
        checksum = ((checksum & 0x1FFFFFF) << 5) ^ value
        for i, generator in enumerate(_GENERATOR):
            if (top >> i) & 1:
                checksum ^= generator
    return checksum
