"""Privacy helpers: nothing that identifies the client is published in clear text."""

import hashlib
import hmac
import re

_NON_DIGITS = re.compile(r"\D")

#: Senegal country calling code, used when a local 9-digit number is given.
_SENEGAL_PREFIX = "221"
_LOCAL_NUMBER_LENGTH = 9


def normalize_phone(phone: str) -> str:
    """Return the number as digits with country code, e.g. "77 123 45 67" -> "221771234567".

    Accepts local Senegalese numbers (9 digits) and international ones written
    with "+" or "00". The same person always normalizes to the same value, so
    the anti-collusion cap per client works across spellings.

    Raises:
        ValueError: if the input does not look like a phone number.
    """
    stripped = phone.strip()
    digits = _NON_DIGITS.sub("", stripped)
    if stripped.startswith("00"):
        digits = digits[2:]
    elif len(digits) == _LOCAL_NUMBER_LENGTH and not stripped.startswith("+"):
        digits = _SENEGAL_PREFIX + digits
    if not 8 <= len(digits) <= 15:  # E.164 allows at most 15 digits
        raise ValueError("not a valid phone number")
    return digits


def hash_client_phone(phone: str, pepper: str) -> str:
    """Keyed hash (HMAC-SHA256) of the client's phone number, as lower-case hex.

    A plain SHA-256 would be reversible: there are only about a billion
    Senegalese numbers to try. The secret pepper, kept server-side, prevents that
    while still letting us count attestations per client.
    """
    if not pepper:
        raise ValueError("a non-empty pepper is required")
    return hmac.new(pepper.encode(), normalize_phone(phone).encode(), hashlib.sha256).hexdigest()
