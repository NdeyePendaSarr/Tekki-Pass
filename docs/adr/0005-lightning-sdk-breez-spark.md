# 0005. Lightning SDK: Breez SDK - Spark

- **Status:** Proposed (team decision due 15 Nov 2026). Completes ADR 0001
- **Date:** 2026-11-14

## Context

ADR 0001 requires a self-custodial Lightning wallet built into the PWA, behind the `LightningWallet` interface. We need an SDK that:

1. keeps keys on the artisan's phone (self-custodial);
2. runs in the browser (Next.js PWA) without a node to operate;
3. has a test environment;
4. is mature and actively maintained, under an open-source licence;
5. can be integrated in under 3 days.

Options reviewed (November 2026):

| Option | Browser | Self-custodial | Verdict |
| --- | --- | --- | --- |
| **Breez SDK - Spark** | Yes (WASM, `/ssr` subpath for Next.js) | Yes, keys on the device, unilateral exit to Bitcoin L1 | **Recommended** |
| Breez SDK - Liquid | Yes (WASM) | Yes | Breez itself advises new and existing partners to move to Spark |
| Breez SDK - Greenlight | – | Yes | Deprecated by Breez in 2025 |
| LDK (rust-lightning) | WASM in beta | Yes | Weeks to months of work: too slow for the hackathon |
| NWC only | Yes | Depends on the user's wallet | Not a built-in wallet; kept as the bonus (ADR 0001) |

## Decision

Use **Breez SDK - Spark** (`@breeztech/breez-sdk-spark`, MIT, version 0.28.x) in the PWA. A Python binding (`breez-sdk-spark` on PyPI) exists if the API ever needs it.

- **Wallet in the browser.** The artisan's app creates the wallet from a 12-word mnemonic, shown once on the guided backup screen. SDK data is stored in IndexedDB. The mnemonic is never sent to the API.
- **A Lightning address per artisan.** At sign-up, the app registers a Lightning address for the artisan (`registerLightningAddress`, served by Breez's LNURL server). The artisan's phone does not need to be online for the rest of the flow.
- **Invoices fetched by the API.** For each attestation request, the API asks the artisan's Lightning address for an invoice over plain HTTP (LNURL-pay). The API stores the BOLT 11 string, its payment hash and the LUD-21 `verify` URL. The money still goes straight to the artisan's wallet.
- **Payment checked by the API.** The API polls the LUD-21 `verify` URL, which returns `settled` and the `preimage`. Before signing the attestation, it checks `sha256(preimage) == payment_hash` (`preimage_matches`).
- **The API interface does not change.** `LightningWallet.create_invoice` becomes the LNURL-pay request and `check_payment` becomes the LUD-21 check, in a `LnurlLightningWallet` adapter. The API never holds a key.
- **The client needs no SDK.** The client pays the invoice from any Lightning wallet (QR code or `lightning:` link). The verifier page does not load the SDK either.
- **Lazy loading.** The WASM module is loaded only on the artisan's wallet screens, then cached by the service worker.

## Consequences

- **Size on 3G.** The WASM module is 12.7 MB raw, 5.3 MB gzipped and 4.0 MB with Brotli. Estimated first download: about 20 s on fast 3G (1.6 Mbit/s) and about 80 s on slow 3G (0.4 Mbit/s), with Brotli. Mitigations:
  - serve it with Brotli;
  - download it in the background while the artisan fills in the profile form;
  - cache it with the service worker, so it is downloaded only once.
  The client and verifier pages do not load it. This still has to be measured on a real phone.
- **API key required.** Breez issues it on request through the form on breez.technology. It lives in an environment variable (`BREEZ_API_KEY`) and is never committed. Request it today: the timing is on the critical path.
- **Testing and networks.**
  - Spark's regtest network (hosted by Lightspark, free, no key needed) **has no Lightning**. Breez recommends testing Lightning on **mainnet with small amounts**.
  - Plan: CI and unit tests use the fakes; the Spark wallet is developed and tested on regtest; the end-to-end Lightning flow is tested and demoed on mainnet with a few sats.
  - This qualifies ADR 0004: for Lightning, "testnet" in practice means Spark regtest without Lightning. A follow-up ADR will update 0004 once the organizers answer.
- **Trust assumptions to state in the pitch.** Spark relies on a set of operators (1-of-n honesty assumption) and on a Lightning service provider for swaps. Funds remain recoverable on Bitcoin L1 without them.
- **Vendor lock-in is limited.** On the API side, everything goes through `LightningWallet` and standard protocols (LNURL-pay, LUD-21). Any wallet with a Lightning address that supports LUD-21 would work, NWC wallets included.
- **Plan B (risk in the brief):** if the integration fails by 18 Nov, the demo uses the same flow with an NWC-connected wallet, or the demo video allowed by the rules.

## Spike results (14 Nov 2026, SDK 0.28.4, regtest, desktop browser)

A throwaway test page ran the SDK in the browser on regtest, **without an API key**:

| Step | Time |
| --- | --- |
| `init()` (WASM compilation) | 0.9 s |
| `connect()` with a new 12-word mnemonic | 0.13 s |
| `getInfo()` | 0.07 s |
| Create a Spark address | 2.1 s |
| Create a BOLT 11 invoice (210 sats, `lnbcrt…`, 0 sats fee) | 2.1 s |

What the documentation and the types confirm:

1. **The artisan can be offline.** "Lightning payments work in Spark even if the receiver is offline." The app claims the payment the next time it opens (`PaymentSucceeded` event).
2. **The artisan's app gets the preimage.** It is in `payment.details.htlcDetails.preimage` once the payment is claimed.
3. **LUD-21 is supported.** Payments received through a Lightning address can be verified by a third party at a public `verify` URL. This is what lets the API check payment without the artisan's phone.

## Still to check (needs the API key and a few mainnet sats)

1. That the Breez `verify` URL really returns the `preimage`, and not just `settled`. If it doesn't, fallback: the artisan's app sends the preimage to the API when it opens.
2. That Lightning address registration works with our API key, and what the address domain is.
3. Real load times on an entry-level Android phone over throttled 3G.
4. API key terms (cost, limits), confirmed by email with Breez.

## Sources

- Breez SDK - Spark docs: [getting started](https://sdk-doc-spark.breez.technology/guide/getting_started.html), [initializing](https://sdk-doc-spark.breez.technology/guide/initializing.html), [testing](https://sdk-doc-spark.breez.technology/guide/testing.html)
- [breez/spark-sdk on GitHub](https://github.com/breez/spark-sdk)
- [Breez - Spark integration (Spark docs)](https://docs.spark.money/integrations/breez)
- [Breez SDK - Liquid testing page (migration notice)](https://sdk-doc-liquid.breez.technology/guide/testing.html)
- Breez SDK - Spark: [receiving payments](https://sdk-doc-spark.breez.technology/guide/receive_payment.html), [Lightning address and LUD-21](https://sdk-doc-spark.breez.technology/guide/receive_lnurl_pay.html)
- [LUD-21: verify LNURL-pay payments](https://github.com/lnurl/luds/blob/luds/21.md)
