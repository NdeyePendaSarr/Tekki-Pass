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

Errors return `{"detail": {"code": "...", "message": "..."}}`. The front end maps each
`code` (`not_found`, `invalid_state`, `client_cap_reached`, `invalid_phone`,
`publication_failed`, `not_configured`) to a plain-language message.

Not done yet: authentication of the artisan on step 1 (planned: NIP-98 signed requests),
rate limiting, and the real Lightning backend (docs/adr/0005).
