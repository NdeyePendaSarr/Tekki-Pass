"""Application settings, read from environment variables only.

Secrets (issuer keys, wallet credentials) must never be hard-coded: they are
injected through the environment, see `.env.example` at the repository root.
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Bitcoin network the deployment runs against. See docs/adr/0004.
Network = Literal["testnet", "mainnet"]


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


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, built once from the environment."""
    return Settings()
