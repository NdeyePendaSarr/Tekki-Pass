"""ORM model of an attestation request.

Lifecycle (`status`):
    awaiting_client   created by the artisan, link not yet opened and confirmed
    awaiting_payment  client confirmed, invoice issued
    paid              invoice paid, attestation not yet published (relay outage: retry)
    published         signed attestation accepted by enough relays
    expired           invoice expired unpaid

Only hashes are stored about the client, never the phone number.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RequestStatus(enum.StrEnum):
    AWAITING_CLIENT = "awaiting_client"
    AWAITING_PAYMENT = "awaiting_payment"
    PAID = "paid"
    PUBLISHED = "published"
    EXPIRED = "expired"


class AttestationRequest(Base):
    __tablename__ = "attestation_requests"
    __table_args__ = (
        Index("ix_requests_client_confirmed", "client_hash", "confirmed_at"),
        Index("ix_requests_artisan_status", "artisan_pubkey", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    #: Unguessable token in the link sent to the client (the only identifier exposed).
    token: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    artisan_pubkey: Mapped[str] = mapped_column(String(64))
    #: Where the fee is paid (docs/adr/0005). Unused by the fake backend.
    lightning_address: Mapped[str | None] = mapped_column(String(320))
    title: Mapped[str] = mapped_column(String(140))
    network: Mapped[str] = mapped_column(String(16))
    amount_sat: Mapped[int] = mapped_column(Integer)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus, native_enum=False, length=32), default=RequestStatus.AWAITING_CLIENT
    )

    client_hash: Mapped[str | None] = mapped_column(String(64))
    bolt11: Mapped[str | None] = mapped_column(Text)
    payment_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    preimage: Mapped[str | None] = mapped_column(String(64))
    invoice_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    event_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    event_json: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
