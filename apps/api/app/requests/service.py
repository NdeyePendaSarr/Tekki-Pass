"""Business logic of the attestation flow, independent of HTTP.

    artisan: create()  ->  client: confirm()  ->  client pays  ->  refresh()
                                                                  checks payment,
                                                                  signs, publishes

The service never holds funds or keys of the artisan: invoices are paid to
the artisan's wallet, and the API only checks the proof of payment.
"""

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.attestations import (
    Attestation,
    EventPublisher,
    IssuerKeys,
    PublishError,
    hash_client_phone,
    sign_attestation,
)
from app.config import Settings
from app.lightning import LightningWallet
from app.requests.models import AttestationRequest, RequestStatus

#: Invoice lifetime: long enough to open a wallet app, short enough to limit stale requests.
INVOICE_EXPIRY = timedelta(minutes=30)

#: Statuses that count towards the per-client cap (a confirmed, possibly paid, request).
_COUNTED_STATUSES = (RequestStatus.AWAITING_PAYMENT, RequestStatus.PAID, RequestStatus.PUBLISHED)


class WalletResolver(Protocol):
    """Gives the wallet that receives the fee for a given artisan."""

    def wallet_for(self, lightning_address: str | None) -> LightningWallet: ...


class RequestError(Exception):
    """Base class of expected, user-facing errors. `code` is stable for the front end."""

    code = "request_error"


class RequestNotFoundError(RequestError):
    code = "not_found"


class InvalidStateError(RequestError):
    code = "invalid_state"


class ClientCapReachedError(RequestError):
    code = "client_cap_reached"


class NotConfiguredError(RequestError):
    """A server secret (issuer key, pepper) is missing: an operator problem, not the user's."""

    code = "not_configured"


class PublicationFailedError(RequestError):
    """Paid but not enough relays accepted the attestation. Safe to retry refresh()."""

    code = "publication_failed"


def utcnow() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    """SQLite returns naive datetimes: they are stored in UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


@dataclass(slots=True)
class AttestationService:
    session: AsyncSession
    settings: Settings
    wallets: WalletResolver
    publisher: EventPublisher
    now: Callable[[], datetime] = utcnow

    async def create(
        self, artisan_pubkey: str, title: str, lightning_address: str | None
    ) -> AttestationRequest:
        """Artisan side: register a job and get the token for the client link."""
        request = AttestationRequest(
            token=secrets.token_urlsafe(16),
            artisan_pubkey=artisan_pubkey,
            lightning_address=lightning_address,
            title=title,
            network=self.settings.network,
            amount_sat=self.settings.attestation_fee_sat,
            status=RequestStatus.AWAITING_CLIENT,
            created_at=self.now(),
        )
        self.session.add(request)
        await self.session.commit()
        return request

    async def get(self, token: str, *, for_update: bool = False) -> AttestationRequest:
        query = select(AttestationRequest).where(AttestationRequest.token == token)
        if for_update:
            # Serializes concurrent refreshes on PostgreSQL (no-op on SQLite).
            query = query.with_for_update()
        request = (await self.session.execute(query)).scalar_one_or_none()
        if request is None:
            raise RequestNotFoundError("attestation request not found")
        return request

    async def confirm(self, token: str, client_phone: str) -> AttestationRequest:
        """Client side: confirm the job and receive the invoice to pay."""
        pepper = self.settings.client_phone_pepper
        if pepper is None:
            raise NotConfiguredError("CLIENT_PHONE_PEPPER is not set")
        request = await self.get(token, for_update=True)
        if request.status is not RequestStatus.AWAITING_CLIENT:
            raise InvalidStateError("this request was already confirmed")

        client_hash = hash_client_phone(client_phone, pepper.get_secret_value())
        await self._enforce_client_cap(client_hash)

        wallet = self.wallets.wallet_for(request.lightning_address)
        invoice = await wallet.create_invoice(
            amount_sat=request.amount_sat,
            memo=f"Tekki-Pass: {request.title}",
            expiry_seconds=int(INVOICE_EXPIRY.total_seconds()),
        )
        request.client_hash = client_hash
        request.bolt11 = invoice.bolt11
        request.payment_hash = invoice.payment_hash
        request.invoice_expires_at = invoice.expires_at
        request.confirmed_at = self.now()
        request.status = RequestStatus.AWAITING_PAYMENT
        await self.session.commit()
        return request

    async def refresh(self, token: str) -> AttestationRequest:
        """Check payment, then sign and publish. Idempotent: safe to call repeatedly."""
        request = await self.get(token, for_update=True)

        if request.status is RequestStatus.AWAITING_PAYMENT:
            await self._check_payment(request)
        if request.status is RequestStatus.PAID:
            await self._publish(request)
        return request

    async def published_for_artisan(self, artisan_pubkey: str) -> list[AttestationRequest]:
        query = (
            select(AttestationRequest)
            .where(
                AttestationRequest.artisan_pubkey == artisan_pubkey,
                AttestationRequest.status == RequestStatus.PUBLISHED,
            )
            .order_by(AttestationRequest.published_at.desc())
        )
        return list((await self.session.execute(query)).scalars())

    async def _enforce_client_cap(self, client_hash: str) -> None:
        since = self.now() - timedelta(days=self.settings.client_cap_window_days)
        count = await self.session.scalar(
            select(func.count()).where(
                AttestationRequest.client_hash == client_hash,
                AttestationRequest.status.in_(_COUNTED_STATUSES),
                AttestationRequest.confirmed_at >= since,
            )
        )
        if (count or 0) >= self.settings.max_attestations_per_client:
            raise ClientCapReachedError("this client has reached the attestation limit")

    async def _check_payment(self, request: AttestationRequest) -> None:
        assert request.payment_hash is not None  # set by confirm()  # noqa: S101
        status = await self.wallets.wallet_for(request.lightning_address).check_payment(
            request.payment_hash
        )
        if status.paid:
            request.preimage = status.preimage
            request.status = RequestStatus.PAID
        elif request.invoice_expires_at and _aware(request.invoice_expires_at) <= self.now():
            request.status = RequestStatus.EXPIRED
        await self.session.commit()

    async def _publish(self, request: AttestationRequest) -> None:
        nsec = self.settings.nostr_issuer_nsec
        if nsec is None:
            raise NotConfiguredError("NOSTR_ISSUER_NSEC is not set")
        # Re-validates everything, including sha256(preimage) == payment_hash.
        attestation = Attestation(
            artisan_pubkey=request.artisan_pubkey,
            payment_hash=request.payment_hash or "",
            preimage=request.preimage or "",
            client_hash=request.client_hash or "",
            title=request.title,
            network=self.settings.network,
        )
        # Sign once and keep the event, so a retry republishes the same event ID.
        if request.event_json is None:
            request.event_json = sign_attestation(attestation, IssuerKeys(nsec.get_secret_value()))
            await self.session.commit()
        try:
            result = await self.publisher.publish(request.event_json)
        except PublishError as exc:
            raise PublicationFailedError("not enough relays accepted the attestation") from exc
        request.event_id = result.event_id
        request.published_at = self.now()
        request.status = RequestStatus.PUBLISHED
        await self.session.commit()
