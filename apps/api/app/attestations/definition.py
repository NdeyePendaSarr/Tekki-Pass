"""Publication of the Tekki-Pass badge definition (NIP-58, kind 30009).

Every attestation (kind 8) points to this definition through its `a` tag. Without
it on the relays, Nostr clients cannot display the badge's name and description,
and a verifier cannot see what the issuer claims to attest.

Run by hand:  python -m app.attestations.definition
"""

import asyncio
import json
import logging
import sys

from app.attestations.models import AttestationError
from app.attestations.nostr import IssuerKeys, build_badge_definition
from app.attestations.relays import EventPublisher, NostrRelayPublisher, PublishError, PublishResult

logger = logging.getLogger(__name__)


async def publish_badge_definition(
    issuer: IssuerKeys, publisher: EventPublisher, image_url: str | None = None
) -> PublishResult:
    """Sign and publish the badge definition. Raises PublishError if too few relays accept it."""
    return await publisher.publish(build_badge_definition(issuer, image_url))


async def publish_badge_definition_safely(
    issuer: IssuerKeys, publisher: EventPublisher, image_url: str | None = None
) -> PublishResult | None:
    """Same, for API startup: a relay outage is logged but must never stop the API."""
    try:
        result = await publish_badge_definition(issuer, publisher, image_url)
    except (PublishError, AttestationError) as exc:
        logger.warning("badge definition not published: %s", exc)
        return None
    except Exception:  # unexpected relay/library error: still keep the API running
        logger.exception("badge definition not published")
        return None
    logger.info(
        "badge definition %s published to %d relay(s)", result.event_id, len(result.accepted)
    )
    return result


def main() -> int:  # pragma: no cover - thin CLI wrapper around tested functions
    """CLI: publish the definition with the configured issuer key and relays."""
    from app.config import get_settings

    settings = get_settings()
    if settings.nostr_issuer_nsec is None:
        print("NOSTR_ISSUER_NSEC is not set", file=sys.stderr)
        return 1
    issuer = IssuerKeys(settings.nostr_issuer_nsec.get_secret_value())
    publisher = NostrRelayPublisher(settings.nostr_relays, settings.nostr_min_relay_acks)
    try:
        result = asyncio.run(publish_badge_definition(issuer, publisher, settings.badge_image_url))
    except PublishError as exc:
        print(f"failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"event_id": result.event_id, "accepted": list(result.accepted)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
