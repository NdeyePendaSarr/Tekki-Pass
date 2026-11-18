"""`LightningWallet` backed by the artisan's Lightning address (docs/adr/0005).

The artisan's self-custodial wallet (Breez SDK - Spark, in their browser) registers a
Lightning address. For each attestation the API:

1. asks that address for an invoice (LNURL-pay, LUD-06 and LUD-16);
2. checks the invoice: amount and network as requested (BOLT 11);
3. later asks the LUD-21 `verify` URL whether it is paid, and gets the preimage.

The money goes straight to the artisan's wallet: the API holds no key and no funds.
The phone of the artisan does not need to be online.

The URLs come from outside (the artisan's address and the answers of their wallet
provider), so every request is restricted (threat model: SSRF): HTTPS only, public
host names that resolve to public addresses only, no redirects, short timeouts and
small answers.
"""

import asyncio
import ipaddress
import logging
import socket
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlsplit

import httpx2

from app.lightning.bolt11 import InvalidInvoiceError, decode
from app.lightning.wallet import (
    Invoice,
    InvoiceNotFoundError,
    PaymentStatus,
    WalletUnavailableError,
    preimage_matches,
)

logger = logging.getLogger(__name__)

#: Seconds per request to the wallet provider.
TIMEOUT_SECONDS = 10
#: LNURL answers are small JSON documents.
MAX_RESPONSE_BYTES = 64 * 1024

#: BOLT 11 networks accepted for each Tekki-Pass network (settings.network).
_INVOICE_NETWORKS = {"mainnet": {"mainnet"}, "testnet": {"testnet", "signet", "regtest"}}

#: Resolves a host name to its IP addresses (replaced in the tests).
Resolver = Callable[[str], Awaitable[list[str]]]


async def resolve_host(host: str) -> list[str]:
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]


class LnurlLightningWallet:
    """Invoices from one Lightning address, payments checked with LUD-21."""

    def __init__(
        self,
        lightning_address: str,
        *,
        network: str,
        client: httpx2.AsyncClient,
        allowed_domains: list[str] | None = None,
        resolver: Resolver = resolve_host,
    ) -> None:
        username, _, domain = lightning_address.lower().partition("@")
        if not username or not domain:
            raise WalletUnavailableError("invalid Lightning address")
        self._username = username
        self._domain = domain
        self._network = network
        self._client = client
        self._allowed_domains = [d.lower() for d in allowed_domains or []]
        self._resolver = resolver

    async def create_invoice(
        self, amount_sat: int, memo: str, expiry_seconds: int = 3600
    ) -> Invoice:
        """LNURL-pay: the invoice's expiry is chosen by the wallet, not by us."""
        if amount_sat <= 0:
            raise ValueError("amount_sat must be positive")
        amount_msat = amount_sat * 1000

        pay = await self._get_json(f"https://{self._domain}/.well-known/lnurlp/{self._username}")
        if pay.get("status") == "ERROR":
            raise WalletUnavailableError("the Lightning address is unknown to its provider")
        if pay.get("tag") != "payRequest" or not isinstance(pay.get("callback"), str):
            raise WalletUnavailableError("the Lightning address is not an LNURL-pay endpoint")
        low, high = pay.get("minSendable"), pay.get("maxSendable")
        if not isinstance(low, int) or not isinstance(high, int) or not low <= amount_msat <= high:
            raise WalletUnavailableError("the wallet does not accept this amount")

        params: dict[str, str | int] = {"amount": amount_msat}
        comment_allowed = pay.get("commentAllowed")
        if isinstance(comment_allowed, int) and comment_allowed > 0:
            params["comment"] = memo[:comment_allowed]
        answer = await self._get_json(pay["callback"], params=params)
        if answer.get("status") == "ERROR":  # LNURL error: {"status": "ERROR", "reason": ...}
            raise WalletUnavailableError("the wallet refused to create the invoice")

        bolt11, verify_url = answer.get("pr"), answer.get("verify")
        if not isinstance(bolt11, str):
            raise WalletUnavailableError("the wallet returned no invoice")
        if not isinstance(verify_url, str):
            # Without LUD-21 the API could never confirm the payment.
            raise WalletUnavailableError("the wallet does not support payment verification")
        try:
            decoded = decode(bolt11)
        except InvalidInvoiceError as exc:
            raise WalletUnavailableError(f"the wallet returned a bad invoice: {exc}") from exc
        if decoded.amount_msat != amount_msat:
            raise WalletUnavailableError("the invoice amount is not the one requested")
        if decoded.network not in _INVOICE_NETWORKS.get(self._network, set()):
            raise WalletUnavailableError("the invoice is for another Bitcoin network")
        await self._check_url(verify_url)

        return Invoice(
            bolt11=bolt11,
            payment_hash=decoded.payment_hash,
            amount_sat=amount_sat,
            memo=memo,
            expires_at=decoded.expires_at,
            verify_url=verify_url,
        )

    async def check_payment(
        self, payment_hash: str, verify_url: str | None = None
    ) -> PaymentStatus:
        """LUD-21: `{"settled": true, "preimage": "..."}` once the invoice is paid."""
        if verify_url is None:
            raise InvoiceNotFoundError(payment_hash)
        answer = await self._get_json(verify_url)
        if answer.get("status") == "ERROR":
            raise InvoiceNotFoundError(payment_hash)
        if answer.get("settled") is not True:
            return PaymentStatus(paid=False)

        preimage = answer.get("preimage")
        if not isinstance(preimage, str) or not preimage_matches(preimage, payment_hash):
            # Settled but no valid proof: never treat it as paid (docs/adr/0005, open check 1).
            logger.warning("settled payment without a valid preimage from the verify URL")
            return PaymentStatus(paid=False)
        return PaymentStatus(paid=True, preimage=preimage.lower())

    async def _get_json(
        self, url: str, params: dict[str, str | int] | None = None
    ) -> dict[str, Any]:
        await self._check_url(url)
        try:
            response = await self._client.get(
                url, params=params, timeout=TIMEOUT_SECONDS, follow_redirects=False
            )
        except httpx2.HTTPError as exc:
            raise WalletUnavailableError("the wallet provider cannot be reached") from exc
        if response.status_code != 200:
            raise WalletUnavailableError(f"the wallet provider answered {response.status_code}")
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise WalletUnavailableError("the wallet provider answer is too large")
        try:
            data = response.json()
        except ValueError as exc:
            raise WalletUnavailableError("the wallet provider answer is not JSON") from exc
        if not isinstance(data, dict):
            raise WalletUnavailableError("the wallet provider answer is not a JSON object")
        return data

    async def _check_url(self, url: str) -> None:
        """Only HTTPS to public hosts (and allowed domains, if configured)."""
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        if parts.scheme != "https" or not host or parts.username or parts.password:
            raise WalletUnavailableError("the wallet provider URL is not a public HTTPS URL")
        if self._allowed_domains and not any(
            host == domain or host.endswith("." + domain) for domain in self._allowed_domains
        ):
            raise WalletUnavailableError("the wallet provider is not on the allowed list")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise WalletUnavailableError("the wallet provider URL must use a host name")
        try:
            addresses = await self._resolver(host)
        except OSError as exc:
            raise WalletUnavailableError("the wallet provider host cannot be resolved") from exc
        if not addresses or not all(ipaddress.ip_address(a).is_global for a in addresses):
            raise WalletUnavailableError("the wallet provider host is not public")


class LnurlWalletResolver:
    """One `LnurlLightningWallet` per artisan's Lightning address, sharing one HTTP client."""

    #: The invoice is requested from the artisan's address: requests must carry one.
    requires_lightning_address = True

    def __init__(
        self,
        *,
        network: str,
        allowed_domains: list[str] | None = None,
        client: httpx2.AsyncClient | None = None,
        resolver: Resolver = resolve_host,
    ) -> None:
        self._network = network
        self._allowed_domains = allowed_domains
        self._client = client if client is not None else httpx2.AsyncClient()
        self._resolver = resolver

    def wallet_for(self, lightning_address: str | None) -> LnurlLightningWallet:
        if lightning_address is None:
            raise WalletUnavailableError("this request has no Lightning address")
        return LnurlLightningWallet(
            lightning_address,
            network=self._network,
            client=self._client,
            allowed_domains=self._allowed_domains,
            resolver=self._resolver,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
