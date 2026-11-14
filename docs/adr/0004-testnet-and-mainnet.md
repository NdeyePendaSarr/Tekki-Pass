# 0004. Testnet and mainnet environments

- **Status:** Accepted
- **Date:** 2026-11-14

## Context

The organizers have not yet said whether mainnet is required or testnet is accepted (question pending on Devpost). Development and automated tests must never risk real funds, but a live demo may need mainnet.

## Decision

- One codebase, with the network selected by a single environment variable: **`NETWORK=testnet|mainnet`**, validated at startup (`apps/api/app/config.py`). An unknown value refuses to start.
- **Default is `testnet`** everywhere: local, CI and preview deployments. Mainnet is set explicitly, only on the demo deployment.
- Each network has its own secrets (wallet credentials, issuer key) and its own database. Nothing is shared between them.
- The UI and `/health` show the active network so a demo never confuses the two.
- Nostr attestations record the network, so a testnet proof can never pass as a mainnet one.

## Consequences

- Switching networks is a configuration change, not a code change.
- Tests run only against testnet or fakes.
- Two sets of secrets to manage. Mainnet amounts stay tiny (micro-fees only).
- If the organizers require mainnet, only the demo deployment's configuration changes.
