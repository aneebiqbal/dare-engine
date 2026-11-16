# Clipdesk Missions

Mission-first Shorts for gamers. The mission card is written before the game is
played; Start and Done mark the exact window; the platform renders a finished
9:16 Short.

Design: `docs/spec.md`. Decisions: `docs/decisions.md`. Status: `PROGRESS.md`.

## Layout

```
web/       Next.js + TypeScript + Tailwind app
api/       FastAPI service and mission/LLM logic
worker/    clip rendering worker (FFmpeg)
relay/     MediaMTX configuration
contracts/ openapi.yaml and the mission card JSON schema
docs/      spec and decisions
```

## Run

```sh
cp .env.example .env   # fill in keys as milestones need them
make up                # docker compose up -d --wait
make accept            # acceptance tests
```

Services: web http://localhost:3100, api http://localhost:8000,
relay API http://localhost:19997, S3 storage http://localhost:9100.

Host ports are offset (3100/9100) so the stack does not collide with other
local projects. Container-to-container traffic uses the service names.

## Secrets

Every key is read from the environment. `.env` is gitignored. Never commit a
key, and never write one into a test or a doc.

## Tests

`make accept` is the definition of done for each milestone. It brings the stack
up and runs `tests/acceptance/`.
