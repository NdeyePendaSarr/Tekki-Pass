"""BOLT 11 decoding, checked against the test vectors of the specification."""

from datetime import UTC, datetime, timedelta

import pytest

from app.lightning.bolt11 import InvalidInvoiceError, decode

SPEC_HASH = "0001020304050607080900010203040506070809000102030405060708090102"
SPEC_TIME = datetime(2017, 6, 1, 10, 57, 38, tzinfo=UTC)  # 1496314658

DONATION = (
    "lnbc1pvjluezsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygspp5qqqsyqcyq5rqwzqfqq"
    "qsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqdpl2pkx2ctnv5sxxmmwwd5kgetjypeh2ursdae8g6twvus8g6rfwvs8"
    "qun0dfjkxaq9qrsgq357wnc5r2ueh7ck6q93dj32dlqnls087fxdwk8qakdyafkq3yap9us6v52vjjsrvywa6rt52"
    "cm9r9zqt8r2t7mlcwspyetp5h2tztugp9lfyql"
)
COFFEE = (
    "lnbc2500u1pvjluezsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygspp5qqqsyqcyq5rqwz"
    "qfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqdq5xysxxatsyp3k7enxv4jsxqzpu9qrsgquk0rl77nj30yxdy8j9"
    "vdx85fkpmdla2087ne0xh8nhedh8w27kyke0lp53ut353s06fv3qfegext0eh0ymjpf39tuven09sam30g4vgpfna3rh"
)
TESTNET = (
    "lntb20m1pvjluezsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygshp58yjmdan79s6qqdhdzg"
    "ynm4zwqd5d7xmw5fk98klysy043l2ahrqspp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqfpp"
    "3x9et2e20v6pu37c5d9vax37wxq72un989qrsgqdj545axuxtnfemtpwkc45hx9d2ft7x04mt8q7y6t0k2dge9e7h8kpy"
    "9p34ytyslj3yu569aalz2xdk8xkd7ltxqld94u8h2esmsmacgpghe9k8"
)
PICO = (
    "lnbc9678785340p1pwmna7lpp5gc3xfm08u9qy06djf8dfflhugl6p7lgza6dsjxq454gxhj9t7a0sd8dgfkx7cmtwd6"
    "8yetpd5s9xar0wfjn5gpc8qhrsdfq24f5ggrxdaezqsnvda3kkum5wfjkzmfqf3jkgem9wgsyuctwdus9xgrcyqcjcgp"
    "zgfskx6eqf9hzqnteypzxz7fzypfhg6trddjhygrcyqezcgpzfysywmm5ypxxjemgw3hxjmn8yptk7untd9hxwg3q2d6"
    "xjcmtv4ezq7pqxgsxzmnyyqcjqmt0wfjjq6t5v4khxsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zy"
    "g3zygsxqyjw5qcqp2rzjq0gxwkzc8w6323m55m4jyxcjwmy7stt9hwkwe2qxmy8zpsgg7jcuwz87fcqqeuqqqyqqqqlg"
    "qqqqn3qq9q9qrsgqrvgkpnmps664wgkp43l22qsgdw4ve24aca4nymnxddlnp8vh9v2sdxlu5ywdxefsfvm0fq3sesf0"
    "8uf6q9a2ke0hc9j6z6wlxg5z5kqpu2v9wz"
)
UPPER = (
    "LNBC25M1PVJLUEZPP5QQQSYQCYQ5RQWZQFQQQSYQCYQ5RQWZQFQQQSYQCYQ5RQWZQFQYPQDQ5VDHKVEN9V5SXYETPDE"
    "ESSP5ZYG3ZYG3ZYG3ZYG3ZYG3ZYG3ZYG3ZYG3ZYG3ZYG3ZYG3ZYG3ZYGS9Q5SQQQQQQQQQQQQQQQQSGQ2A25DXL5HRN"
    "TDTN6ZVYDT7D66HYZSYHQS4WDYNAVYS42XGL6SGX9C4G7ME86A27T07MDTFRY458RTJR0V92CNMSWPSJSCGT2VCSE3S"
    "GPZ3UAPA"
)
NO_PAYMENT_HASH = (
    "lnbc25m1pvjluezdq5vdhkven9v5sxyetpdeessp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg"
    "s9q5sqqqqqqqqqqqqqqqqsgqjy08jd52dtj25pefkh0enc54lxtjtr8wnum2msrq2d8uztp9vhhpccq93ljpff0kkjgzk"
    "zcp2czlyenjphf6upazjlc8uxw7za0ynusqrfhg8u"
)
TWO_PAYMENT_HASHES = (
    "lnbc1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqpp5llllllllllllllllllllll"
    "lllllllllllllllllllllllllllllsdpyv36hqmrfvdshgefqwpshjmt9de6zq6rpwd5qsp5zyg3zyg3zyg3zyg3zyg3zy"
    "g3zyg3zyg3zyg3zyg3zyg3zyg3zygs9g3f93cqturay6zk2fyfcmeflphlzew9wfq0n5nf9hqnlwxthtzqcljcuurljyd2"
    "vngkya5hndakf33ghly97qm5nc3umj7jep22nfsq3nr0w8"
)


def test_any_amount_invoice() -> None:
    decoded = decode(DONATION)
    assert decoded.network == "mainnet"
    assert decoded.amount_msat is None
    assert decoded.payment_hash == SPEC_HASH
    assert decoded.created_at == SPEC_TIME
    assert decoded.expires_at == SPEC_TIME + timedelta(hours=1)  # default expiry


def test_amount_and_expiry() -> None:
    decoded = decode(COFFEE)
    assert decoded.amount_msat == 250_000_000  # 2500u = 0.0025 BTC
    assert decoded.payment_hash == SPEC_HASH
    assert decoded.expires_at == SPEC_TIME + timedelta(seconds=60)


def test_testnet_invoice() -> None:
    decoded = decode(TESTNET)
    assert decoded.network == "testnet"
    assert decoded.amount_msat == 2_000_000_000  # 20m


def test_pico_bitcoin_amount() -> None:
    assert decode(PICO).amount_msat == 967_878_534


def test_upper_case_and_lightning_prefix() -> None:
    assert decode(UPPER).payment_hash == SPEC_HASH
    assert decode("lightning:" + COFFEE).payment_hash == SPEC_HASH


@pytest.mark.parametrize(
    ("invoice", "reason"),
    [
        (COFFEE[:-1] + ("q" if COFFEE[-1] != "q" else "p"), "bad checksum"),
        (COFFEE[:20] + COFFEE[20:].upper(), "mixed case"),
        (NO_PAYMENT_HASH, "no payment hash"),
        (TWO_PAYMENT_HASHES, "more than one payment hash"),
        ("lnxx2500u1qqqqqq", "bad checksum"),
        ("not an invoice", "no bech32 separator"),
        ("lnbc" + "q" * 8000, "too long"),
    ],
)
def test_invalid_invoices(invoice: str, reason: str) -> None:
    with pytest.raises(InvalidInvoiceError, match=reason):
        decode(invoice)
