"""Nostr encoding of attestations as NIP-58 badges, signed with nostr-sdk.

This module is the only place that imports `nostr_sdk` (which has no type
hints). It converts everything to plain typed values at the boundary.

Event layout (https://github.com/nostr-protocol/nips/blob/master/58.md):

- Badge definition, kind 30009, published once by the issuer, `d` = BADGE_IDENTIFIER.
- Badge award, kind 8, one per attested job:
    ["a", "30009:<issuer>:tekki-pass-job"]   which badge
    ["p", <artisan pubkey>]                  who receives it
    ["attestation", <id>]                    sha256(payment_hash:artisan), anti-replay
    ["payment_hash", <hex>], ["preimage", <hex>]   proof of payment
    ["client", <keyed hash>]                 never the phone number itself
    ["network", "testnet" | "mainnet"]       a testnet proof cannot pass as mainnet
    ["t", "tekki-pass"]                      lets clients filter our events
  content = the job title.
"""

from typing import Final, get_args

import nostr_sdk

from app.attestations.models import Attestation, AttestationError, VerifiedAttestation
from app.types import Network

BADGE_IDENTIFIER: Final = "tekki-pass-job"
BADGE_DEFINITION_KIND: Final = 30009
BADGE_AWARD_KIND: Final = 8
HASHTAG: Final = "tekki-pass"


class IssuerKeys:
    """Issuer key pair. The secret never leaves this object and is never logged."""

    def __init__(self, secret: str) -> None:
        """Load the issuer key from an `nsec1...` string or 64 hex characters.

        Raises:
            AttestationError: if the key cannot be parsed. The message never
                contains the key.
        """
        try:
            self._keys = nostr_sdk.Keys(nostr_sdk.SecretKey.parse(secret))
        except Exception as exc:
            raise AttestationError("invalid Nostr issuer secret key") from exc

    @classmethod
    def generate(cls) -> "IssuerKeys":
        """Fresh random keys, for tests and local development only."""
        return cls(str(nostr_sdk.Keys.generate().secret_key().to_hex()))

    @property
    def public_key(self) -> str:
        """Issuer public key (hex), shown on the verification page."""
        return str(self._keys.public_key().to_hex())

    def __repr__(self) -> str:  # never expose the secret, even in debug output
        return f"IssuerKeys(public_key={self.public_key!r})"

    def sign(self, kind: int, content: str, tags: list[list[str]]) -> str:
        """Sign an event and return it as JSON."""
        builder = nostr_sdk.EventBuilder(nostr_sdk.Kind(kind), content).tags(
            [nostr_sdk.Tag.parse(tag) for tag in tags]
        )
        unsigned = builder.finalize_unsigned(self._keys.public_key())
        return str(self._keys.sign_event(unsigned).as_json())


def _badge_address(issuer_pubkey: str) -> str:
    return f"{BADGE_DEFINITION_KIND}:{issuer_pubkey}:{BADGE_IDENTIFIER}"


def build_badge_definition(issuer: IssuerKeys, image_url: str | None = None) -> str:
    """Signed badge definition event (JSON).

    Kind 30009 is addressable: relays keep only the latest version per issuer and
    `d` tag, so republishing it (e.g. at every API start) is harmless.
    """
    tags = [
        ["d", BADGE_IDENTIFIER],
        ["name", "Chantier attesté Tekki-Pass"],
        ["description", "Chantier confirmé par le client et payé en Lightning."],
        ["t", HASHTAG],
    ]
    if image_url:
        # NIP-58: optional image shown by Nostr clients next to the badge.
        tags.append(["image", image_url])
    return issuer.sign(BADGE_DEFINITION_KIND, "", tags)


def sign_attestation(attestation: Attestation, issuer: IssuerKeys) -> str:
    """Signed badge award event (JSON) for one attested job."""
    tags = [
        ["a", _badge_address(issuer.public_key)],
        ["p", attestation.artisan_pubkey],
        ["attestation", attestation.id],
        ["payment_hash", attestation.payment_hash],
        ["preimage", attestation.preimage],
        ["client", attestation.client_hash],
        ["network", attestation.network],
        ["t", HASHTAG],
    ]
    return issuer.sign(BADGE_AWARD_KIND, attestation.title, tags)


def _parse_network(value: str | None) -> Network:
    """Narrow a tag value to the `Network` literal type."""
    for network in get_args(Network):
        if value == network:
            return network  # type: ignore[no-any-return]  # get_args() is untyped
    raise AttestationError("missing or unknown network")


def _single_tags(tags: list[list[str]]) -> dict[str, str]:
    """Map tag name -> value, rejecting duplicates that could hide a second value."""
    values: dict[str, str] = {}
    for tag in tags:
        if len(tag) < 2:
            continue
        name, value = tag[0], tag[1]
        if name in values and name != "t":
            raise AttestationError(f"duplicate {name!r} tag")
        values[name] = value
    return values


def verify_attestation(event_json: str, expected_issuer: str) -> VerifiedAttestation:
    """Check a badge award end to end and return its content.

    Checks: valid signature and ID, kind 8, signed by `expected_issuer`, points to
    our badge definition, preimage matches the payment hash, and the attestation
    ID matches the payment and the recipient (anti-replay).

    Raises:
        AttestationError: on any failed check.
    """
    try:
        event = nostr_sdk.Event.from_json(event_json)
    except Exception as exc:
        raise AttestationError("not a valid Nostr event") from exc
    if not bool(event.verify()):
        raise AttestationError("invalid event signature or ID")
    if int(event.kind().as_u16()) != BADGE_AWARD_KIND:
        raise AttestationError("not a badge award event")

    issuer_pubkey = str(event.author().to_hex())
    if issuer_pubkey != expected_issuer:
        raise AttestationError("unknown issuer")

    tags = _single_tags([[str(v) for v in tag.to_vec()] for tag in event.tags()])
    if tags.get("a") != _badge_address(issuer_pubkey):
        raise AttestationError("not a Tekki-Pass badge")

    network = _parse_network(tags.get("network"))
    attestation = Attestation(
        artisan_pubkey=tags.get("p", ""),
        payment_hash=tags.get("payment_hash", ""),
        preimage=tags.get("preimage", ""),
        client_hash=tags.get("client", ""),
        title=str(event.content()),
        network=network,
    )
    if tags.get("attestation") != attestation.id:
        raise AttestationError("attestation ID does not match payment and artisan (replay?)")

    return VerifiedAttestation(
        attestation=attestation,
        event_id=str(event.id().to_hex()),
        issuer_pubkey=issuer_pubkey,
        issued_at=int(event.created_at().as_secs()),
    )
