"""Small shared types, kept free of imports to avoid circular dependencies."""

from typing import Literal

#: Bitcoin network the deployment runs against. See docs/adr/0004.
Network = Literal["testnet", "mainnet"]
