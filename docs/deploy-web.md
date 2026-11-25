# Deploy the cloud web app (PM2)

This deploys the **light** half on a plain VPS: the website every gamer and every
admin-planning task uses, plus the FastAPI service behind it. The heavy clip
engine stays on the admin's machine — see `docs/architecture.md` and
`docs/desktop-app.md`.

The process manager is **PM2**. No Docker is required.

Result: `https://clipdesk.example.com` over TLS, backed by managed Postgres,
with health checks, rate limiting, error reporting and backups.

## What runs where

| Service | Cloud | Desktop |
| --- | --- | --- |
| `web/` (Next.js, standalone build) | yes | optional (loads the cloud URL) |
| `api/` (FastAPI + uvicorn) | yes | talks to the cloud API |
| PostgreSQL | managed (Neon) | — |
| `worker/` (render, transcribe) | no | **yes** |
| `relay/` (RTMP ingest) | optional | — |
| Local models, FFmpeg, OBS, SSD | no | **yes** |

## 1. Managed database

Create a Neon project (or any Postgres 16+). You need two URLs:

- **Pooled** — host contains `-pooler`. For the API (`DATABASE_URL`).
- **Direct** — no `-pooler`. For migrations (`DATABASE_URL_DIRECT`).

Neon's pooled endpoint is PgBouncer in transaction mode, which breaks DDL; the
API runs its migrations against the direct URL on startup.

## 2. Server packages

```sh
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -   # Node 20 LTS
apt-get install -y nodejs python3.12 python3.12-venv ffmpeg
npm install -g pm2
```

`ffmpeg`/`ffprobe` is required by the API for upload probing; without it the
pages still load but recording uploads fail.

## 3. Minimal checkout

Only the paths that build and run are needed:

```sh
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/aneebiqbal/dare-engine.git
cd dare-engine
git sparse-checkout set --no-cone \
  /api/ /web/ /contracts/ /shared/ /ecosystem.config.cjs \
  /.env.example /scripts/build-web-standalone.sh /scripts/setup-pm2.sh \
  /scripts/prepare-release.sh /worker/clip/templates.json /docs/deploy-web.md
```

Why each path: `api/` (uvicorn app), `web/` (Next.js), `contracts/` (shared
schemas), `shared/` (`llm.py`, `key_crypto.py`, `platforms.py`),
`worker/clip/templates.json` (imported by the API), `ecosystem.config.cjs`,
the two scripts, `.env.example`. Tests, screenshots, docs, desktop shell,
worker engine, relay and local bridges stay off the server.

## 4. Environment

```sh
cp .env.example .env
```

Minimum values:

```sh
DATABASE_URL=postgresql://…-pooler…/…
DATABASE_URL_DIRECT=postgresql://…/…
SESSION_SECRET=$(openssl rand -hex 32)
APP_ENV=production
WEB_ORIGIN=https://clipdesk.example.com
INVITE_REQUIRED=true
DEV_AUTH_ENABLED=false
STORAGE_DRIVER=s3                 # shared bucket, or local volume for single host
S3_ENDPOINT=…
S3_BUCKET=…
S3_ACCESS_KEY=…
S3_SECRET_KEY=…
LLM_PROVIDER=openai
LLM_BASE_URL=…
LLM_API_KEY=…
LLM_MODEL=…
```

Anything in `.env` is read by the API at runtime; `NEXT_PUBLIC_*` values are
baked into the web build, so set them before building.

## 5. Build and start under PM2

```sh
# API dependencies and the shared-module shims (once, and after changes)
scripts/setup-pm2.sh

# Web build (standalone server + static assets)
scripts/build-web-standalone.sh

pm2 start ecosystem.config.cjs
pm2 save
pm2 startup          # follow the printed command to survive reboots
```

Local storage instead of S3 (single host) or a non-Docker check needs one
extra variable so the API does not try to write `/data` (read-only on macOS):

```sh
STORAGE_LOCAL_DIR=$PWD/storage LLM_RECORDED_RESPONSE="$PWD/api/app/llm_recorded.json" \
  API_PORT=8010 WEB_PORT=3200 pm2 start ecosystem.config.cjs
```

`ecosystem.config.cjs` runs exactly two processes:

| Name | Command | Port |
| --- | --- | --- |
| `clipdesk-api` | `.venv/bin/python -m uvicorn app.main:app` | `127.0.0.1:8000` |
| `clipdesk-web` | `node .next/standalone/server.js` | `127.0.0.1:3100` |

Ports can be overridden for a local check:

```sh
API_PORT=8010 WEB_PORT=3200 pm2 start ecosystem.config.cjs
```

Useful commands:

```sh
pm2 status            # both apps green
pm2 logs clipdesk-api --lines 50
pm2 reload ecosystem.config.cjs   # zero-downtime restart after an update
pm2 monit
```

## 6. TLS (Caddy)

`/etc/caddy/Caddyfile`:

```
clipdesk.example.com {
    reverse_proxy 127.0.0.1:3100
}
```

```sh
caddy reload --config /etc/caddy/Caddyfile
```

The browser only talks to the web origin. Next.js proxies `/api/*` to
`127.0.0.1:8000` server-side, so the API port stays private.

## 7. Verify

```sh
curl -fsS http://127.0.0.1:3100/healthz          # {"status":"ok"}
curl -fsS http://127.0.0.1:3100/api/healthz/ready # checks the DB
pm2 status
```

Then open the site, sign in, add a game. The first admin is created with:

```sh
.venv/bin/python -m app.create_admin
```

(run from the repo root; prompts for email and password.)

## 8. Update and roll back

```sh
git pull
.venv/bin/pip install -r api/requirements.txt     # if requirements changed
scripts/build-web-standalone.sh                    # if web changed
pm2 reload ecosystem.config.cjs
```

Roll back: check out the previous commit, rebuild the web bundle, and
`pm2 reload`. Migrations are forward-only, so take a backup first:

```sh
gunzip -c backups/clipdesk-<ts>.sql.gz | psql "$DATABASE_URL_DIRECT"
```

## 9. Backups

Managed Postgres has point-in-time recovery. For a self-managed instance or an
extra copy:

```sh
pg_dump "$DATABASE_URL_DIRECT" | gzip > backups/clipdesk-$(date -u +%Y%m%dT%H%M%SZ).sql.gz
```

Schedule it (systemd timer or cron) and keep at least 7 days.

## 10. Hardening already on

- Per-IP rate limits; stricter budgets on `/auth/*` and `/admin/*`.
- Argon2id passwords, HMAC-sha256 sessions, HttpOnly + Secure + SameSite=Lax
  cookies, double-submit CSRF, login lockout.
- Browser errors posted to `/client-error` and surfaced on the admin overview.
- Validated bodies, storage-key traversal guards, SSD bridge mount guard.

## 11. Landing page downloads

`/landing` reads `web/releases/manifest.json` and serves binaries from
`web/public/downloads/` at `/downloads/<file>`. A CDN URL can be put in the
manifest instead. Nothing is hardcoded in the page.

Prepare a release locally (binaries stay gitignored; only the manifest is
committed):

```sh
scripts/prepare-release.sh 0.1.0 \
  desktop/src-tauri/target/release/bundle/dmg/"Clipdesk Missions_0.1.0_aarch64.dmg" \
  downloads/"Clipdesk Missions_0.1.0_x64_en-US.msi" \
  demo.mp4          # optional
git add web/releases/manifest.json && git commit -m "release 0.1.0"
```

On the server, or after cloning, place the files in `web/public/downloads/` and
rebuild the web bundle. A missing file shows an honest “Not uploaded yet”
button, never a dead link.

## 12. Optional: Docker instead of PM2

The container path still works for hosts that prefer it:

```sh
docker compose up -d --wait --build --no-deps api web
```

See `docker-compose.yml`; the same `.env` drives both paths. Use one or the
other, not both on the same ports.
