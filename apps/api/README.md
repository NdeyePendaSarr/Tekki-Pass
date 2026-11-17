# Tekki-Pass API

FastAPI service (Python 3.12, fully typed). See the [root README](../../README.md) for the big picture.

```bash
uv sync                                   # install dependencies (pinned in uv.lock)
uv run uvicorn app.main:app --reload      # http://localhost:8000/docs (SQLite file by default)
uv run pytest                             # tests
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run alembic upgrade head               # PostgreSQL migrations (Docker runs this on startup)
```

## Attestation flow

| Step | Who | Route |
| --- | --- | --- |
| 1. Describe the job, get the link token | Artisan | `POST /attestation-requests` |
| 2. Open the link | Client | `GET /attestation-requests/{token}` |
| 3. Confirm, receive the invoice | Client | `POST /attestation-requests/{token}/confirm` |
| 4. Pay the invoice | Client | Any Lightning wallet (fake backend: `POST /dev/attestation-requests/{token}/simulate-payment`) |
| 5. Check payment, sign and publish | Client page (polling) | `POST /attestation-requests/{token}/refresh` |
| 6. See the artisan's proofs | Verifier | `GET /artisans/{pubkey}/attestations`, `GET /issuer` |
| — Dashboard | Artisan | `GET /artisans/{pubkey}/requests` (always signed with NIP-98: it contains the client links) |

Errors return `{"detail": {"code": "...", "message": "..."}}`. The front end maps each
`code` (`not_found`, `invalid_state`, `client_cap_reached`, `invalid_phone`,
`publication_failed`, `not_configured`) to a plain-language message.

Step 1 requires a NIP-98 `Authorization: Nostr <event>` header signed by the artisan key
(`app/auth/nip98.py`); errors: `auth_required`, `invalid_auth`, `auth_pubkey_mismatch`. Each signed
event can be used once: clients add a random `nonce` tag so that two requests in the same
second do not look like a replay.

The badge definition (NIP-58 kind 30009) that every attestation points to is published
to the relays when the API starts (`app/attestations/definition.py`); a relay outage is
logged and never blocks startup. Manual run: `uv run python -m app.attestations.definition`.

Creation, confirmation and payment checks are rate-limited per client IP (`app/ratelimit.py`):
`429` with code `rate_limited` and a `Retry-After` header. Behind a proxy, set `TRUSTED_PROXIES`
so the real client IP is read from `X-Forwarded-For`.

Not done yet: the real Lightning backend (docs/adr/0005).
