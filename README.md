# Clipdesk Missions

Mission-first Shorts for gamers. The mission card is written before the game is
played; Start and Done mark the exact window; the platform renders a finished
9:16 Short.

Design: `docs/spec.md`. Decisions: `docs/decisions.md`. Status: `PROGRESS.md`.
Run guide: `RUN.md`.

## Layout

```
web/       Next.js + TypeScript + Tailwind app
api/       FastAPI service and mission/AI logic
worker/    clip rendering worker (FFmpeg)
relay/     MediaMTX configuration
contracts/ openapi.yaml and the mission card JSON schema
docs/      spec, decisions, context export
```

## Run

```sh
cp .env.example .env   # local defaults; .env is gitignored
make up                # starts the database, API, worker, web and relay
make voice             # one-time download of the local TTS voice
make create-admin      # creates the first administrator (prompts)
```

Open http://localhost:3100. Stop with `make down`.

Services: web http://localhost:3100, api http://localhost:8000, worker
http://localhost:8001, relay control API http://localhost:19997. Storage is
local disk by default (set `STORAGE_DRIVER=s3` and the `S3_*` variables for
S3-compatible storage).

## Secrets

Every key is read from the environment. `.env` is gitignored. Never commit a
key, and never write one into a test or a doc.

## Tests

```sh
make doctor      # environment and connection checks
make accept      # acceptance suite
make web-accept  # Playwright page flows + accessibility
```

`make accept` is the definition of done for each milestone.
