"""Real payments through the artisan's Lightning address (LNURL-pay + LUD-21).

A fake wallet provider answers like Breez's LNURL server would: no network access.
"""

import hashlib
import json
import secrets
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.attestations import IssuerKeys, verify_attestation
from app.config import Settings
from app.lightning import InvoiceNotFoundError, WalletUnavailableError
from app.lightning.bolt11 import decode
from app.lightning.lnurl import LnurlLightningWallet, LnurlWalletResolver, Resolver
from app.main import create_app
from tests.database import TEST_DATABASE_URL
from tests.fakes.fake_publisher import FakePublisher
from tests.fakes.invoices import make_invoice

ADDRESS = "moussa@wallet.example"
VERIFY = "https://wallet.example/lnurlp/moussa/verify/"


async def public_dns(host: str) -> list[str]:
    return ["93.184.215.14"]


@dataclass
class FakeProvider:
    """Breez-like LNURL server for one Lightning address."""

    network: str = "mainnet"
    paid: set[str] = field(default_factory=set)
    invoices: dict[str, str] = field(default_factory=dict)  # payment hash -> preimage
    requests: list[httpx2.Request] = field(default_factory=list)
    #: Overrides, to simulate misbehaving providers.
    pay_answer: dict[str, Any] | None = None
    invoice_amount: int | None = None
    verify_url: str | None = VERIFY
    send_preimage: bool = True

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        path = request.url.path
        if path == "/.well-known/lnurlp/moussa":
            return httpx2.Response(200, json=self.pay_answer or self._pay_request())
        if path == "/lnurlp/moussa/callback":
            amount_sat = int(request.url.params["amount"]) // 1000
            preimage = secrets.token_hex(32)
            payment_hash = hashlib.sha256(bytes.fromhex(preimage)).hexdigest()
            self.invoices[payment_hash] = preimage
            invoice = make_invoice(
                payment_hash, self.invoice_amount or amount_sat, network=self.network
            )
            answer: dict[str, Any] = {"pr": invoice, "routes": []}
            if self.verify_url:
                answer["verify"] = self.verify_url + payment_hash
            return httpx2.Response(200, json=answer)
        if path.startswith("/lnurlp/moussa/verify/"):
            payment_hash = path.rsplit("/", 1)[1]
            if payment_hash not in self.invoices:
                return httpx2.Response(200, json={"status": "ERROR", "reason": "Not found"})
            settled = payment_hash in self.paid
            revealed = self.invoices[payment_hash] if settled and self.send_preimage else None
            return httpx2.Response(
                200, json={"status": "OK", "settled": settled, "preimage": revealed, "pr": ""}
            )
        return httpx2.Response(404)

    def _pay_request(self) -> dict[str, Any]:
        return {
            "tag": "payRequest",
            "callback": "https://wallet.example/lnurlp/moussa/callback",
            "minSendable": 1000,
            "maxSendable": 100_000_000,
            "metadata": json.dumps([["text/plain", "Pay Moussa"]]),
            "commentAllowed": 30,
        }

    def pay(self, payment_hash: str) -> None:
        self.paid.add(payment_hash)


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


def wallet(
    provider: FakeProvider,
    *,
    network: str = "mainnet",
    resolver: Resolver = public_dns,
    allowed_domains: list[str] | None = None,
) -> LnurlLightningWallet:
    client = httpx2.AsyncClient(transport=httpx2.MockTransport(provider))
    return LnurlLightningWallet(
        ADDRESS,
        network=network,
        client=client,
        resolver=resolver,
        allowed_domains=allowed_domains,
    )


# --- Adapter ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_invoice_from_the_lightning_address(provider: FakeProvider) -> None:
    invoice = await wallet(provider).create_invoice(210, "Tekki-Pass: Carrelage")

    assert invoice.amount_sat == 210
    assert decode(invoice.bolt11).payment_hash == invoice.payment_hash
    assert invoice.verify_url == VERIFY + invoice.payment_hash
    callback = provider.requests[1]
    assert callback.url.params["amount"] == "210000"  # millisatoshis
    assert callback.url.params["comment"] == "Tekki-Pass: Carrelage"


@pytest.mark.anyio
async def test_payment_is_checked_with_lud21(provider: FakeProvider) -> None:
    w = wallet(provider)
    invoice = await w.create_invoice(210, "job")

    unpaid = await w.check_payment(invoice.payment_hash, verify_url=invoice.verify_url)
    assert not unpaid.paid

    provider.pay(invoice.payment_hash)
    paid = await w.check_payment(invoice.payment_hash, verify_url=invoice.verify_url)
    assert paid.paid
    assert paid.preimage == provider.invoices[invoice.payment_hash]


@pytest.mark.anyio
async def test_settled_without_preimage_is_not_paid(provider: FakeProvider) -> None:
    provider.send_preimage = False
    w = wallet(provider)
    invoice = await w.create_invoice(210, "job")
    provider.pay(invoice.payment_hash)

    status = await w.check_payment(invoice.payment_hash, verify_url=invoice.verify_url)
    assert not status.paid


@pytest.mark.anyio
async def test_unknown_payment(provider: FakeProvider) -> None:
    with pytest.raises(InvoiceNotFoundError):
        await wallet(provider).check_payment("00" * 32, verify_url=VERIFY + "00" * 32)
    with pytest.raises(InvoiceNotFoundError):
        await wallet(provider).check_payment("00" * 32)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("setup", "reason"),
    [
        (lambda p: setattr(p, "invoice_amount", 21_000), "amount"),
        (lambda p: setattr(p, "network", "testnet"), "network"),
        (lambda p: setattr(p, "verify_url", None), "verification"),
        (lambda p: setattr(p, "pay_answer", {"status": "ERROR", "reason": "no"}), "unknown"),
        (lambda p: setattr(p, "pay_answer", {"tag": "withdrawRequest"}), "LNURL-pay"),
        (
            lambda p: setattr(
                p,
                "pay_answer",
                {**p._pay_request(), "minSendable": 1_000_000},
            ),
            "amount",
        ),
    ],
)
async def test_bad_answers_are_refused(
    provider: FakeProvider, setup: Callable[[FakeProvider], None], reason: str
) -> None:
    setup(provider)
    with pytest.raises(WalletUnavailableError, match=reason):
        await wallet(provider).create_invoice(210, "job")


@pytest.mark.anyio
async def test_regtest_invoices_are_accepted_on_testnet(provider: FakeProvider) -> None:
    provider.network = "regtest"
    invoice = await wallet(provider, network="testnet").create_invoice(210, "job")
    assert invoice.bolt11.startswith("lnbcrt")


@pytest.mark.anyio
@pytest.mark.parametrize("addresses", [["127.0.0.1"], ["10.0.0.5"], ["93.184.215.14", "::1"], []])
async def test_private_hosts_are_refused(provider: FakeProvider, addresses: list[str]) -> None:
    async def dns(host: str) -> list[str]:
        return addresses

    with pytest.raises(WalletUnavailableError, match="not public"):
        await wallet(provider, resolver=dns).create_invoice(210, "job")
    assert provider.requests == []


@pytest.mark.anyio
async def test_only_https_urls_are_followed(provider: FakeProvider) -> None:
    provider.pay_answer = {**provider._pay_request(), "callback": "http://wallet.example/cb"}
    with pytest.raises(WalletUnavailableError, match="HTTPS"):
        await wallet(provider).create_invoice(210, "job")


@pytest.mark.anyio
async def test_allowed_domains(provider: FakeProvider) -> None:
    await wallet(provider, allowed_domains=["example"]).create_invoice(210, "job")
    with pytest.raises(WalletUnavailableError, match="allowed list"):
        await wallet(provider, allowed_domains=["breez.tips"]).create_invoice(210, "job")


@pytest.mark.anyio
async def test_unreachable_provider() -> None:
    def down(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("down")

    client = httpx2.AsyncClient(transport=httpx2.MockTransport(down))
    w = LnurlLightningWallet(ADDRESS, network="mainnet", client=client, resolver=public_dns)
    with pytest.raises(WalletUnavailableError, match="reached"):
        await w.create_invoice(210, "job")


# --- Through the API ---------------------------------------------------------------------


@pytest.fixture
def api(provider: FakeProvider) -> Iterator[tuple[TestClient, IssuerKeys, FakePublisher]]:
    issuer = IssuerKeys.generate()
    publisher = FakePublisher()
    settings = Settings(
        network="mainnet",
        lightning_backend="lnurl",
        nostr_relays=["wss://relay.example"],
        database_url=TEST_DATABASE_URL,
        client_phone_pepper=SecretStr("test-pepper"),
        nostr_issuer_nsec=SecretStr(issuer._keys.secret_key().to_hex()),
        nip98_required=False,
        publish_badge_definition_on_startup=False,
    )
    client = httpx2.AsyncClient(transport=httpx2.MockTransport(provider))
    resolver = LnurlWalletResolver(network="mainnet", client=client, resolver=public_dns)
    app = create_app(settings, wallets=resolver, publisher=publisher)
    with TestClient(app) as test_client:
        yield test_client, issuer, publisher


def test_full_flow_with_a_real_lightning_address(
    api: tuple[TestClient, IssuerKeys, FakePublisher], provider: FakeProvider
) -> None:
    client, issuer, publisher = api
    artisan = IssuerKeys.generate().public_key
    created = client.post(
        "/attestation-requests",
        json={"artisan_pubkey": artisan, "title": "Carrelage", "lightning_address": ADDRESS},
    )
    token = created.json()["token"]

    confirmed = client.post(
        f"/attestation-requests/{token}/confirm", json={"client_phone": "771234567"}
    )
    assert confirmed.status_code == 200, confirmed.text
    bolt11 = confirmed.json()["bolt11"]
    assert bolt11.startswith("lnbc2100n1")  # 210 sats, mainnet
    assert client.post(f"/attestation-requests/{token}/refresh").json()["status"] == (
        "awaiting_payment"
    )

    provider.pay(decode(bolt11).payment_hash)  # the client pays from any wallet
    published = client.post(f"/attestation-requests/{token}/refresh").json()
    assert published["status"] == "published"
    verified = verify_attestation(publisher.published[0], issuer.public_key)
    assert verified.attestation.artisan_pubkey == artisan
    assert client.post(f"/dev/attestation-requests/{token}/simulate-payment").status_code == 404


def test_a_lightning_address_is_required(api: tuple[TestClient, IssuerKeys, FakePublisher]) -> None:
    client, _, _ = api
    response = client.post(
        "/attestation-requests",
        json={"artisan_pubkey": IssuerKeys.generate().public_key, "title": "Carrelage"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "lightning_address_required"


def test_wallet_provider_down_is_a_502(
    api: tuple[TestClient, IssuerKeys, FakePublisher], provider: FakeProvider
) -> None:
    client, _, _ = api
    provider.pay_answer = {"status": "ERROR", "reason": "maintenance"}
    token = client.post(
        "/attestation-requests",
        json={
            "artisan_pubkey": IssuerKeys.generate().public_key,
            "title": "Carrelage",
            "lightning_address": ADDRESS,
        },
    ).json()["token"]

    response = client.post(
        f"/attestation-requests/{token}/confirm", json={"client_phone": "771234567"}
    )
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "wallet_unavailable"
    # Nothing was consumed: the client can try again once the wallet is back.
    assert client.get(f"/attestation-requests/{token}").json()["status"] == "awaiting_client"
