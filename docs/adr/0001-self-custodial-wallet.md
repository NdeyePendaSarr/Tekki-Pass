# 0001. Self-custodial Lightning wallet

- **Status:** Accepted. SDK chosen in [ADR 0005](0005-lightning-sdk-breez-spark.md) (Breez SDK - Spark)
- **Date:** 2026-11-14

## Context

The hackathon requires a working Bitcoin or Lightning wallet. Our promise is "Tekki-Pass never touches the money": the artisan must own the funds and the keys. The stack is a Next.js PWA and a FastAPI backend, and the main device is an entry-level Android phone over 3G.

## Decision

- Each artisan gets a **self-custodial Lightning wallet built into the app**, created at sign-up with a recovery phrase that the user must back up and confirm.
- Connecting an existing wallet through **NWC (Nostr Wallet Connect)** is a bonus, planned before the final pitch.
- The backend talks to wallets only through the `LightningWallet` protocol (`apps/api/app/lightning/wallet.py`: `create_invoice`, `check_payment` returning `paid` and `preimage`). The real SDK will be one adapter behind it.
- **SDK: TBD.** Selection criteria: truly self-custodial, works from a PWA or a thin backend, testnet support, maturity and maintenance, licence, integration effort in under 3 days.

## Consequences

- Business logic and tests do not depend on a vendor. Tests use an in-memory fake that respects `sha256(preimage) == payment_hash`.
- Key loss is the user's risk. We mitigate it with a guided backup at sign-up, and social recovery is on the roadmap.
- If no SDK can be integrated in time, the fallback is a demo video (allowed by the rules), with the interface unchanged.
- A follow-up ADR will record the SDK chosen and why.
