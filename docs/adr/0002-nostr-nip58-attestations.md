# 0002. Attestations as Nostr NIP-58 badges

- **Status:** Accepted
- **Date:** 2026-11-14

## Context

Proofs of work must stay verifiable even if Tekki-Pass disappears, and verifiers must not have to trust our server. A private database cannot offer that. Nostr gives us secp256k1-signed events on public relays, and NIP-58 already defines badges (definition, award, profile badges) that existing clients understand.

## Decision

- Each attested job is a **NIP-58 badge award** (kind 8) referencing a Tekki-Pass badge definition (kind 30009), awarded to the artisan's Nostr public key.
- In the MVP, **Tekki-Pass is the issuer** and signs with its own key. Accredited issuers (Chambre des Métiers, approved site managers) come later.
- The event carries the **payment hash** and the **preimage** (proof of payment), plus a **hash of the client's phone number**. It never carries a name or a phone number in clear text.
- The attestation ID is derived from the payment hash and the artisan's public key, so a proof cannot be replayed for another artisan.
- Events are published to several public relays. The verification page reads the relays directly and checks the issuer's public key.
- Signing uses an established Nostr library, never home-made cryptography.

## Consequences

- Proofs survive Tekki-Pass and anyone can verify them.
- Published events are public and permanent: any data mistake is irreversible, so payloads need strict review and tests.
- A single MVP issuer is a trust point. We say so openly in the pitch, and the roadmap moves to multiple accredited issuers.
- The issuer secret key lives only in an environment variable or secret store (`NOSTR_ISSUER_NSEC`).
- OpenTimestamps anchoring is a later bonus.
