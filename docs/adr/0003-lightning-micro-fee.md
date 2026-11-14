# 0003. Lightning micro-fee per attestation

- **Status:** Accepted. Amount to be set after field interviews
- **Date:** 2026-11-14

## Context

Artisans are paid in Wave, Orange Money or cash, and asking clients to pay a whole job over Lightning is unrealistic today. We still need each attestation to cost something real, so that faking a hundred of them is expensive, and to be backed by a cryptographic proof of payment.

## Decision

- The client pays a **small attestation fee in sats** over Lightning. The job itself stays paid in CFA francs through the usual channels.
- The fee goes **directly to the artisan's wallet** (see ADR 0001). Tekki-Pass never holds it.
- An attestation is published only after `check_payment` returns `paid = true` with a preimage that matches the payment hash.
- MVP anti-collusion measures: the fee is mandatory, and the number of attestations per client is capped.
- **Amount: TBD** (a few hundred FCFA equivalent is the working hypothesis), to be set after interviews with at least five artisans.
- A small commission on this fee is a possible revenue source, to be validated.

## Consequences

- Payment habits stay the same, which lowers the adoption barrier.
- A colluding client can still pay, but faking at scale becomes costly. Graph signals and accredited issuers will reduce the risk later.
- Clients without a Lightning wallet need help: a ready demo wallet for the pitch, and a mobile-money gateway later.
- Target version: deposit or whole job paid over Lightning (roadmap).
