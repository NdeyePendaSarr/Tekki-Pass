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
- **Invoices from the artisan's app.** The artisan's app creates the invoice for the micro-fee. The API stores only the BOLT 11 string and its payment hash, linked to the attestation request.
- **The client needs no SDK.** The client pays the invoice from any Lightning wallet (QR code or `lightning:` link). The verifier page does not load the SDK either.
- **API side.** The API never holds keys. Before signing an attestation, it checks `sha256(preimage) == payment_hash` (`preimage_matches`). The `LightningWallet` interface moves to the front end, with a TypeScript twin. The API keeps a `PaymentVerifier` that answers "is this request paid, and here is the proof". See *Open points*.
- **Lazy loading.** The WASM module is loaded only on wallet screens and then cached by the service worker.

## Consequences

- **Size on 3G.** The WASM module is 12.7 MB, or about 5.2 MB gzipped. The artisan downloads it once, on the wallet screens only, and the service worker caches it afterwards. The client and verifier pages stay light. This must be measured on a real phone with throttled 3G (brief, UX principles).
- **API key required.** Breez issues it on request through the form on breez.technology. It lives in an environment variable (`BREEZ_API_KEY`) and is never committed. Request it today: the timing is on the critical path.
- **Testing and networks.**
  - Spark's regtest network (hosted by Lightspark, free, no key needed) **has no Lightning**. Breez recommends testing Lightning on **mainnet with small amounts**.
  - Plan: CI and unit tests use the fakes; the Spark wallet is developed and tested on regtest; the end-to-end Lightning flow is tested and demoed on mainnet with a few sats.
  - This qualifies ADR 0004: for Lightning, "testnet" in practice means Spark regtest without Lightning. A follow-up ADR will update 0004 once the organizers answer.
- **Trust assumptions to state in the pitch.** Spark relies on a set of operators (1-of-n honesty assumption) and on a Lightning service provider for swaps. Funds remain recoverable on Bitcoin L1 without them.
- **Vendor lock-in is limited.** Everything goes through `LightningWallet` and `PaymentVerifier`, so changing SDK means rewriting one adapter.
- **Plan B (risk in the brief):** if the integration fails by 18 Nov, the demo uses the same flow with an NWC-connected wallet, or the demo video allowed by the rules.

## Open points (to settle in a half-day spike)

1. **Getting the preimage to the API.** Ways the preimage can reach the API:
   - (a) the artisan's app reports it once it syncs;
   - (b) the client's wallet shows it, which is unreliable;
   - (c) an LNURL-verify endpoint (LUD-21) on the artisan's Lightning address, if Breez provides one.
   Check which of these the SDK supports.
2. **Payment while the artisan's phone is offline.** Can a Spark wallet receive a Lightning payment while the app is closed, and claim it later? This decides whether the attestation can be published without the artisan online.
3. **Real loading time** of `init()` plus `connect()` on an entry-level Android phone over throttled 3G.
4. **API key terms** (cost, limits), confirmed by email with Breez.

## Sources

- Breez SDK - Spark docs: [getting started](https://sdk-doc-spark.breez.technology/guide/getting_started.html), [initializing](https://sdk-doc-spark.breez.technology/guide/initializing.html), [testing](https://sdk-doc-spark.breez.technology/guide/testing.html)
- [breez/spark-sdk on GitHub](https://github.com/breez/spark-sdk)
- [Breez - Spark integration (Spark docs)](https://docs.spark.money/integrations/breez)
- [Breez SDK - Liquid testing page (migration notice)](https://sdk-doc-liquid.breez.technology/guide/testing.html)
