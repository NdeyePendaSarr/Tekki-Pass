"""Application settings, read from environment variables only.

Secrets (issuer keys, wallet credentials) must never be hard-coded: they are
injected through the environment, see `.env.example` at the repository root.

Defaults are safe for local development: testnet, fake Lightning payments and
a local Nostr relay, so a developer can never publish fake attestations to
public relays by accident.
"""

import secrets
from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.attestations.relays import is_local_relay, validate_relay_url
from app.types import Network

__all__ = ["LightningBackend", "Network", "Settings", "get_settings"]

#: "fake" settles invoices on demand (development and demo only). The real backend
#: (Lightning address + LUD-21, docs/adr/0005) comes with the Breez API key.
LightningBackend = Literal["fake"]


class Settings(BaseSettings):
    """Typed runtime configuration."""

    model_config = SettingsConfigDict(extra="ignore")

    #: Defaults to testnet so that a misconfigured deployment never moves real sats.
    network: Network = "testnet"

    #: SQLAlchemy URL. postgresql:// URLs are accepted and use the asyncpg driver.
    #: Default: a local SQLite file, for running the API without Docker.
    database_url: str = "sqlite+aiosqlite:///./tekki-dev.db"

    lightning_backend: LightningBackend = "fake"

    #: Local demo only: generate a throwaway issuer key and pepper when they are missing,
    #: so `docker compose up` works with no setup. Refused with a real Lightning backend.
    dev_generate_missing_secrets: bool = False

    #: Micro-fee paid by the client per attestation (docs/adr/0003).
    #: TODO: set the real amount after the field interviews.
    attestation_fee_sat: int = Field(default=210, ge=1)

    #: Anti-collusion cap: attestations one client can confirm over the rolling window.
    max_attestations_per_client: int = Field(default=5, ge=1)
    client_cap_window_days: int = Field(default=30, ge=1)

    #: Tekki-Pass issuer secret key (nsec or hex) used to sign attestations. See docs/adr/0002.
    #: Optional at startup so that /health works before the key is provisioned.
    nostr_issuer_nsec: SecretStr | None = None

    #: Secret mixed into the client phone hash. Without it, a plain hash of a 9-digit
    #: Senegalese number could be reversed by trying every number.
    client_phone_pepper: SecretStr | None = None

    #: Relays attestations are published to (env: JSON array). Production uses several
    #: independent public relays, e.g. relay.damus.io, nos.lol, relay.primal.net.
    nostr_relays: list[str] = Field(default=["ws://localhost:7777"], min_length=1)

    #: How many relays must accept an attestation for the publication to count.
    nostr_min_relay_acks: int = Field(default=1, ge=1)

    @field_validator("nostr_issuer_nsec", "client_phone_pepper", mode="before")
    @classmethod
    def _empty_means_unset(cls, value: object) -> object:
        # docker-compose passes unset variables as empty strings.
        return None if value == "" else value

    @field_validator("nostr_relays")
    @classmethod
    def _check_relay_urls(cls, relays: list[str]) -> list[str]:
        return [validate_relay_url(url) for url in relays]

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.nostr_min_relay_acks > len(self.nostr_relays):
            raise ValueError("NOSTR_MIN_RELAY_ACKS cannot exceed the number of relays")
        if self.lightning_backend == "fake":
            # Fake payments must never produce attestations that look real.
            if self.network != "testnet":
                raise ValueError("the fake Lightning backend is only allowed on testnet")
            if not all(is_local_relay(url) for url in self.nostr_relays):
                raise ValueError("the fake Lightning backend may only publish to local relays")
        elif self.dev_generate_missing_secrets:
            raise ValueError("DEV_GENERATE_MISSING_SECRETS is only allowed with the fake backend")
        return self

    def with_dev_secrets(self) -> "Settings":
        """Fill missing secrets with random throwaway values (local demo only)."""
        if not self.dev_generate_missing_secrets:
            return self
        updates: dict[str, SecretStr] = {}
        if self.nostr_issuer_nsec is None:
            updates["nostr_issuer_nsec"] = SecretStr(secrets.token_hex(32))
        if self.client_phone_pepper is None:
            updates["client_phone_pepper"] = SecretStr(secrets.token_hex(32))
        return self.model_copy(update=updates)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, built once from the environment."""
    return Settings()
