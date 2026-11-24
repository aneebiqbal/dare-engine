# Deploy the cloud web app

This deploys the **light** half: the website every gamer and every admin-planning
task uses. The heavy clip engine stays on the admin's Mac — see
`docs/architecture.md` and `docs/desktop-app.md`.

The result: `https://clipdesk.example.com` over TLS, backed by a managed
Postgres, with a health check, rate limiting, error reporting and backups.

## What runs where

| Service | Cloud | Desktop |
| --- | --- | --- |
| `web/` (Next.js) | yes | optional (the app loads the cloud URL) |
| `api/` (FastAPI) | yes | talks to the cloud API |
| PostgreSQL | managed (Neon) | — |
| `worker/` (render, transcribe) | optional | **yes** |
| `relay/` (RTMP ingest) | optional | — |
| Local models, FFmpeg, OBS, SSD | — | **yes** |

In the smallest deployment the cloud runs **only `api` and `web`**. The worker
is what renders clips; run it on the machine that has the footage (the desktop
app) or on a separate GPU host. It shares the same `DATABASE_URL`.

## 1. Managed database

Create a Neon project (or any Postgres 16+). You need two URLs:

- **Pooled** — host contains `-pooler`. For the API (`DATABASE_URL`).
- **Direct** — no `-pooler`. For migrations and the worker
  (`DATABASE_URL_DIRECT`).

Neon's pooled endpoint is PgBouncer in transaction mode, which breaks DDL and
the worker's row locks. That is why both exist.

## 2. Server

A 2 GB VPS is enough for the web half. Install Docker and Caddy:

```sh
curl -fsSL https://get.docker.com | sh
# Caddy: https://caddyserver.com/docs/install
```

## 3. Environment

Copy `.env.example` to `.env` on the server and fill in at least:

```sh
DATABASE_URL=postgresql://…-pooler…/…
DATABASE_URL_DIRECT=postgresql://…/…
SESSION_SECRET=$(openssl rand -hex 32)
APP_ENV=production
WEB_ORIGIN=https://clipdesk.example.com
INVITE_REQUIRED=true
DEV_AUTH_ENABLED=false
STORAGE_DRIVER=s3            # see the storage note below
S3_ENDPOINT=…
S3_BUCKET=…
S3_ACCESS_KEY=…
S3_SECRET_KEY=…
LLM_PROVIDER=openai
LLM_BASE_URL=…
LLM_API_KEY=…
LLM_MODEL=…
```

`APP_ENV=production` sets `Secure` cookies. `WEB_ORIGIN` must be the exact origin
the browser uses (CORS). Never set `DEV_AUTH_ENABLED=true` in production — the
API refuses to start.

**Storage.** The default `STORAGE_DRIVER=local` writes to a container volume. In
the cloud the API and the worker are different machines, so media must be shared:
set `STORAGE_DRIVER=s3` and provide an S3-compatible bucket (Cloudflare R2 or
AWS S3). The app talks to it through the `S3_*` variables only. The S3 path is
implemented but was only exercised against a local mock; prove it before launch.

## 4. TLS

`/etc/caddy/Caddyfile`:

```
clipdesk.example.com {
    reverse_proxy 127.0.0.1:3100
}
```

```sh
caddy reload --config /etc/caddy/Caddyfile
```

The browser only ever talks to the web origin. The Next.js app proxies `/api/*`
to the API container server-side, so the API port (8000) stays private.

DNS: an `A` record for `clipdesk.example.com` to the server.

## 5. Start

From the repo root on the server:

```sh
git clone <repo> && cd clipdesk
docker compose up -d --wait --build --no-deps api web
```

`--no-deps` skips the compose `db` service because the database is managed. The
API runs its migrations on startup (`app.db.migrate()`), so an empty database
becomes a working one.

## 6. Verify

```sh
curl -fsS https://clipdesk.example.com/healthz        # {"status":"ok"}
curl -fsS https://clipdesk.example.com/healthz/ready  # {"status":"ready"} (checks the DB)
docker compose logs --tail=50 api
make create-admin   # creates the first administrator, prompts for a password
```

Then open the site, sign in, and add a game.

## 11. Landing page slots

`/landing` reads four variables from the web environment. Empty values render
an honest `NEXT_PUBLIC_*` placeholder, never a dead button:

```sh
NEXT_PUBLIC_DOWNLOAD_MAC=https://…/Clipdesk_0.1.0_aarch64.dmg
NEXT_PUBLIC_DOWNLOAD_WINDOWS=https://…/Clipdesk_0.1.0_x64_en-US.msi
NEXT_PUBLIC_WEB_PORTAL=https://clipdesk.example.com
NEXT_PUBLIC_DEMO_CLIP=https://…/demo.mp4
```

See `docs/desktop-app.md` for producing the two installers.

## 7. Backups

The managed database has its own point-in-time recovery (Neon: 7–30 days). For a
self-managed Postgres, or for an extra copy:

```sh
make backup   # pg_dump → backups/clipdesk-<utc-timestamp>.sql.gz
```

Schedule it (systemd timer or cron) and keep at least 7 days. Restore with:

```sh
gunzip -c backups/clipdesk-<ts>.sql.gz | psql "$DATABASE_URL_DIRECT"
```

`backups/` is gitignored.

## 8. Hardening that is already on

- **Rate limiting.** `RATE_LIMIT_REQUESTS` per IP per `RATE_LIMIT_WINDOW`;
  `/auth/*` and `/admin/*` get `RATE_LIMIT_AUTH`. Returns `429` with
  `Retry-After`. The health check is never throttled.
- **Sessions.** Argon2id passwords, HMAC-sha256 session tokens in Postgres,
  HttpOnly + Secure + SameSite=Lax cookies, double-submit CSRF on every
  state-changing route, login lockout after 10 failures.
- **Error reporting.** The browser posts uncaught errors to `/client-error`;
  an admin reads them on the admin overview. No external service required.
- **Validation.** Every body is a Pydantic model; storage keys reject path
  traversal; the SSD bridge refuses paths outside the mount.

## 9. Update and roll back

```sh
git pull
docker compose up -d --wait --build --no-deps api web
docker image prune -f
```

Roll back by checking out the previous commit and rebuilding; migrations are
forward-only, so take `make backup` first.

## 10. What this deployment does not do

- It does not render clips, transcribe, or download models. That is the desktop
  app (`docs/desktop-app.md`).
- It does not post to YouTube/TikTok. Export is a zip.
- Live AI and live research need key credit; the fallbacks are flagged, never
  presented as live.
