"""HTTP routes of the attestation flow.

Errors return `{"detail": {"code": ..., "message": ...}}` so the front end can
show a plain-language message per `code` (see the UX principles in the brief).
"""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from pydantic import BaseModel, Field

from app.attestations import AttestationError
from app.attestations.models import MAX_TITLE_LENGTH
from app.db import session_scope
from app.lightning.fake import FakeWalletResolver
from app.requests.models import AttestationRequest, RequestStatus
from app.requests.service import (
    AttestationService,
    ClientCapReachedError,
    InvalidStateError,
    NotConfiguredError,
    PublicationFailedError,
    RequestError,
    RequestNotFoundError,
)

HEX64 = r"^[0-9a-f]{64}$"

router = APIRouter(tags=["attestations"])

_HTTP_STATUS: dict[type[RequestError], int] = {
    RequestNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidStateError: status.HTTP_409_CONFLICT,
    ClientCapReachedError: status.HTTP_429_TOO_MANY_REQUESTS,
    NotConfiguredError: status.HTTP_503_SERVICE_UNAVAILABLE,
    PublicationFailedError: status.HTTP_502_BAD_GATEWAY,
}


def _http_error(exc: RequestError) -> HTTPException:
    return HTTPException(
        status_code=_HTTP_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": str(exc)},
    )


async def get_service(request: Request) -> AsyncIterator[AttestationService]:
    """One service (and database session) per HTTP request."""
    state = request.app.state
    async with session_scope(state.session_factory) as session:
        yield AttestationService(
            session=session,
            settings=state.settings,
            wallets=state.wallets,
            publisher=state.publisher,
        )


Service = Annotated[AttestationService, Depends(get_service)]


# --- Schemas -----------------------------------------------------------------------


class CreateRequestIn(BaseModel):
    artisan_pubkey: str = Field(pattern=HEX64, description="Artisan's Nostr public key (hex)")
    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    lightning_address: str | None = Field(
        default=None, max_length=320, pattern=r"^[a-z0-9._+-]+@[a-z0-9.-]+\.[a-z]{2,}$"
    )


class ConfirmIn(BaseModel):
    client_phone: str = Field(min_length=8, max_length=32)


class RequestOut(BaseModel):
    """Public view of a request. Never includes the client hash."""

    token: str
    status: RequestStatus
    title: str
    artisan_pubkey: str
    amount_sat: int
    network: str
    bolt11: str | None
    payment_hash: str | None
    invoice_expires_at: datetime | None
    event_id: str | None

    @classmethod
    def of(cls, r: AttestationRequest) -> "RequestOut":
        return cls(
            token=r.token,
            status=r.status,
            title=r.title,
            artisan_pubkey=r.artisan_pubkey,
            amount_sat=r.amount_sat,
            network=r.network,
            bolt11=r.bolt11,
            payment_hash=r.payment_hash,
            invoice_expires_at=r.invoice_expires_at,
            event_id=r.event_id,
        )


class PublishedAttestationOut(BaseModel):
    event_id: str
    title: str
    payment_hash: str
    published_at: datetime
    #: The signed NIP-58 event, so anyone can re-verify it without trusting us.
    event_json: str


class IssuerOut(BaseModel):
    pubkey: str | None
    network: str


class SimulatedPayment(BaseModel):
    status: Literal["paid"]


# --- Routes ------------------------------------------------------------------------


@router.post("/attestation-requests", status_code=status.HTTP_201_CREATED)
async def create_request(body: CreateRequestIn, service: Service) -> RequestOut:
    """Artisan: describe a job and get the token for the link sent to the client."""
    created = await service.create(body.artisan_pubkey, body.title.strip(), body.lightning_address)
    return RequestOut.of(created)


@router.get("/attestation-requests/{token}")
async def get_request(token: str, service: Service) -> RequestOut:
    """Client page: what am I attesting, and for how much?"""
    try:
        return RequestOut.of(await service.get(token))
    except RequestError as exc:
        raise _http_error(exc) from exc


@router.post("/attestation-requests/{token}/confirm")
async def confirm_request(token: str, body: ConfirmIn, service: Service) -> RequestOut:
    """Client: confirm the job and receive the invoice to pay."""
    try:
        return RequestOut.of(await service.confirm(token, body.client_phone))
    except ValueError as exc:  # invalid phone number
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "invalid_phone", "message": "invalid phone number"},
        ) from exc
    except RequestError as exc:
        raise _http_error(exc) from exc


@router.post("/attestation-requests/{token}/refresh")
async def refresh_request(token: str, service: Service) -> RequestOut:
    """Check the payment; once paid, sign and publish the attestation. Safe to repeat."""
    try:
        return RequestOut.of(await service.refresh(token))
    except AttestationError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail={"code": "invalid_proof", "message": str(exc)}
        ) from exc
    except RequestError as exc:
        raise _http_error(exc) from exc


@router.get("/artisans/{artisan_pubkey}/attestations")
async def list_attestations(
    artisan_pubkey: Annotated[str, Path(pattern=HEX64)],
    service: Service,
) -> list[PublishedAttestationOut]:
    """Public page: an artisan's published attestations (also readable on the relays)."""
    return [
        PublishedAttestationOut(
            event_id=r.event_id or "",
            title=r.title,
            payment_hash=r.payment_hash or "",
            published_at=r.published_at or r.created_at,
            event_json=r.event_json or "",
        )
        for r in await service.published_for_artisan(artisan_pubkey)
    ]


@router.get("/issuer")
async def issuer(request: Request) -> IssuerOut:
    """Issuer public key the verification page must check signatures against."""
    state = request.app.state
    return IssuerOut(pubkey=state.issuer_pubkey, network=state.settings.network)


dev_router = APIRouter(prefix="/dev", tags=["development"])


@dev_router.post("/attestation-requests/{token}/simulate-payment")
async def simulate_payment(token: str, request: Request, service: Service) -> SimulatedPayment:
    """Fake backend only: pay the invoice as the client would. Absent in production."""
    wallets = request.app.state.wallets
    if not isinstance(wallets, FakeWalletResolver):  # defensive: router not mounted otherwise
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    try:
        found = await service.get(token)
    except RequestError as exc:
        raise _http_error(exc) from exc
    if found.payment_hash is None:
        raise _http_error(InvalidStateError("the client has not confirmed yet"))
    wallets.wallet.mark_paid(found.payment_hash)
    return SimulatedPayment(status="paid")
