"""Demo data: a few attested jobs for one artisan (the brief's persona "Moussa").

Only with the fake Lightning backend (local and demo deployments): the jobs go
through the real flow (create, confirm, pay, sign, publish), with payments settled
by the fake wallet. Nothing here is ever possible with a real wallet.
"""

import secrets

from app.lightning.fake import FakeLightningWallet
from app.requests.models import AttestationRequest
from app.requests.service import AttestationService

#: Typical tiler jobs, as Moussa would describe them.
DEMO_JOBS = (
    "Carrelage cuisine, 9 m²",
    "Pose de faïence salle de bain, 12 m²",
    "Carrelage terrasse, 20 m²",
)


def demo_client_phone() -> str:
    """A random, fictitious client number for one demo job.

    Only its keyed hash is stored, and nobody is ever contacted. A new number per job
    keeps demo runs clear of the per-client anti-collusion cap.
    """
    return "+22170" + "".join(secrets.choice("0123456789") for _ in range(7))


async def seed_demo_attestations(
    service: AttestationService, wallet: FakeLightningWallet, artisan_pubkey: str
) -> list[AttestationRequest]:
    """Create, confirm, pay and publish one attestation per demo job."""
    published: list[AttestationRequest] = []
    for title in DEMO_JOBS:
        request = await service.create(artisan_pubkey, title, lightning_address=None)
        request = await service.confirm(request.token, demo_client_phone())
        assert request.payment_hash is not None  # set by confirm()  # noqa: S101
        wallet.mark_paid(request.payment_hash)
        published.append(await service.refresh(request.token))
    return published
