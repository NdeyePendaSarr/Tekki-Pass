# Deployment (single server)

Tekki-Pass runs on one Linux server with Docker Compose. Caddy is the only service
exposed to the internet and gets the HTTPS certificate automatically.

```
internet ──443──> Caddy ──> web (Next.js) ──/api──> API ──> PostgreSQL
                     └──/relay──> Nostr relay  <── API publishes attestations
```

- `https://$DOMAIN/`: the app (artisan space, client page, public page).
- `wss://$DOMAIN/relay`: our Nostr relay, where attestations are published and where
  the public page reads them.
- The API, the database and the relay are not reachable directly from the internet.

> **Payments are simulated** until the Breez API key arrives (docs/adr/0005); step 6
> switches to real payments. This is safe: the fake backend is refused on mainnet and
> may only publish to our own relay, so nothing fake reaches public Nostr relays.

## 1. Server

- Any small VPS: 2 GB RAM, 1–2 vCPU, Ubuntu 24.04 (Hetzner, DigitalOcean, OVH, …).
- Install Docker Engine with the Compose plugin: https://docs.docker.com/engine/install/ubuntu/
- Open only ports 22 (SSH), 80 and 443 in the firewall.
- Point the domain to the server: an `A` record `tekki-pass.example.com → <server IP>`.
  No domain yet? `sslip.io` gives one for free: `<server-ip-with-dashes>.sslip.io`
  (e.g. `203-0-113-7.sslip.io`).

## 2. Secrets

On the server, in the repository folder (never on a shared machine, never in Git):

```bash
cp deploy/.env.example deploy/.env
chmod 600 deploy/.env
```

Fill in `deploy/.env`:

| Variable | How to generate it |
| --- | --- |
| `DOMAIN` | The domain from step 1 |
| `POSTGRES_PASSWORD` | `openssl rand -hex 24` |
| `CLIENT_PHONE_PEPPER` | `openssl rand -hex 32` |
| `NOSTR_ISSUER_NSEC` | see below |

The issuer key signs every attestation. Generate it **once**, keep a copy in the team's
password manager, and never change it: attestations signed by an old key would no longer
be recognised by the verification page.

```bash
docker run --rm ghcr.io/astral-sh/uv:0.13.5-python3.12-trixie-slim \
  uvx --from nostr-sdk==0.45.1 python -c "import nostr_sdk; print(nostr_sdk.Keys.generate().secret_key().to_bech32())"
```

## 3. Start

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --build
```

The first start builds the images (a few minutes), applies the database migrations,
gets the HTTPS certificate and publishes the badge definition to the relay. Until the API
reports "Application startup complete" (up to about a minute on a small server), Caddy
answers `502 Bad Gateway`: wait, then check again.

Check:

```bash
curl -s https://$DOMAIN/api/health           # {"status":"ok","network":"testnet"}
curl -s https://$DOMAIN/api/issuer           # issuer key + relays: ["wss://$DOMAIN/relay"]
docker compose -f deploy/docker-compose.prod.yml logs api | grep badge
```

## 4. Update after a merge

```bash
git pull
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --build
```

## 5. Backups

The database and the relay data live in Docker volumes. Before any risky operation:

```bash
docker compose -f deploy/docker-compose.prod.yml exec db pg_dump -U tekki tekki_pass > backup.sql
```

Attestations are also on the relay. Once real payments are on, add public relays to
`NOSTR_RELAYS` so the proofs survive the server (docs/adr/0002).

## 6. Real payments (once the Breez API key is here)

Payments are simulated until then. To switch to real sats (docs/adr/0005):

1. In `deploy/.env`:
   ```bash
   NETWORK=mainnet
   LIGHTNING_BACKEND=lnurl
   BREEZ_API_KEY=<the key from Breez>
   LNURL_ALLOWED_DOMAINS=["breez.tips"]   # domain of the Lightning addresses Breez gives
   ```
2. Restart: `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d`
   (no rebuild needed: the web server reads the key at runtime).
3. Check: `curl -s https://$DOMAIN/wallet-config` returns `"enabled":true`.
4. Each artisan opens **Mon portefeuille** once: the app creates the wallet from their
   12 words and registers their Lightning address. New requests are paid to it.

The API holds no wallet key: it asks the artisan's Lightning address for each invoice
and checks the payment with LUD-21. Requests created before the switch have no
Lightning address: create new ones. Test with a few sats first (docs/adr/0005).

## Notes

- Rate limits use the client IP forwarded by Caddy. `TRUSTED_PROXIES` covers the
  private Docker networks only; Caddy ignores any `X-Forwarded-For` sent by clients.
- `/dev/.../simulate-payment` exists only with the fake backend. It disappears when
  `LIGHTNING_BACKEND` switches to the real wallet.
