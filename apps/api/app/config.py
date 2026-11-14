"""Application settings, read from environment variables only.

Secrets (issuer keys, wallet credentials) must never be hard-coded: they are
injected through the environment, see `.env.example` at the repository root.
"""

from functools import lru_cache
from typing import Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.attestations.relays import validate_relay_url
from app.types import Network

__all__ = ["Network", "Settings", "get_settings"]


class Settings(BaseSettings):
    """Typed runtime configuration."""

    model_config = SettingsConfigDict(extra="ignore")

    #: Defaults to testnet so that a misconfigured deployment never moves real sats.
    network: Network = "testnet"

    #: Tekki-Pass issuer secret key (nsec or hex) used to sign attestations. See docs/adr/0002.
    #: Optional at startup so that /health works before the key is provisioned.
    nostr_issuer_nsec: SecretStr | None = None

    #: Secret mixed into the client phone hash. Without it, a plain hash of a 9-digit
    #: Senegalese number could be reversed by trying every number.
    client_phone_pepper: SecretStr | None = None

    #: Public relays attestations are published to (env: JSON array). Independent operators,
    #: so proofs survive any single relay disappearing.
    nostr_relays: list[str] = Field(
        default=["wss://relay.damus.io", "wss://nos.lol", "wss://relay.primal.net"],
        min_length=1,
    )

    #: How many relays must accept an attestation for the publication to count.
    nostr_min_relay_acks: int = Field(default=2, ge=1)

    @field_validator("nostr_relays")
    @classmethod
    def _check_relay_urls(cls, relays: list[str]) -> list[str]:
        return [validate_relay_url(url) for url in relays]

    @model_validator(mode="after")
    def _check_min_acks(self) -> Self:
        if self.nostr_min_relay_acks > len(self.nostr_relays):
            raise ValueError("NOSTR_MIN_RELAY_ACKS cannot exceed the number of relays")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, built once from the environment."""
    return Settings()
