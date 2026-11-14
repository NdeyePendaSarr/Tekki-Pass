# Security Policy

Tekki-Pass deals with Lightning payments, signing keys and personal data. We take reports seriously.

## Supported versions

Only the `main` branch is supported during the hackathon.

## Reporting a vulnerability

**Please do not open a public issue.** Use GitHub's private vulnerability reporting instead:
**Security → Report a vulnerability** on this repository.

Include:

- what is affected (file, endpoint, flow) and the impact;
- steps to reproduce or a proof of concept;
- whether real funds or personal data may be at risk.

We aim to acknowledge reports within 72 hours and to agree on a fix and disclosure date with you.

## Scope and principles

- Tekki-Pass never holds the artisan's funds: wallets are self-custodial.
- No personal data is published on Nostr in clear text; only hashes are.
- Secrets (issuer key, wallet credentials) live in environment variables and are never committed. CI scans every push with gitleaks.
- No home-made cryptography: only established Bitcoin, Lightning and Nostr libraries.
- Dependencies are pinned and audited in CI (`pip-audit`, `npm audit`).

The MVP threat model is in the [README](README.md#threat-model-mvp).

## Testnet first

Run against **testnet** unless you are explicitly testing a mainnet deployment. Never use real funds or real personal data in a report.
