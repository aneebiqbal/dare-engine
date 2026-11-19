# Clipdesk Missions

**Mission-first Shorts for gamers.** The mission card is written before the game
is played; Start and Done mark the exact window; the platform renders a finished
9:16 Short.

<!-- DEMO_GIF_SLOT
     Replace this comment with a 3-5 s GIF of a real clip being rendered from the
     owner's own gameplay. Do NOT use fixtures/gameplay_4min.mp4: it is a
     publisher trailer (IGN watermark), not the owner's gameplay.
-->

<!-- REAL_CLIPS_SLOT
     Replace this comment with 2-3 real Shorts rendered from the owner's own
     gameplay with commentary, each with a one-line human verdict.
-->

Design: `docs/spec.md`. Decisions: `docs/decisions.md`. Status: `PROGRESS.md`.
Run guide: `RUN.md`. Licences: `docs/licences.md`. Launch: `docs/launch.md`.

## Quick start (30 seconds)

```sh
cp .env.example .env   # local defaults; .env is gitignored
make up                # starts the database, API, worker, web and relay
make create-admin      # prompts for email and password
```

Open http://localhost:3100. Stop with `make down`.

First `make up` builds the images; later starts are seconds. Optional and off
by default: `make voice` (GPL piper-tts add-on, see `docs/licences.md`).

Services: web http://localhost:3100, api http://localhost:8000, worker
http://localhost:8001, relay control API http://localhost:19997. Storage is
local disk by default (set `STORAGE_DRIVER=s3` and the `S3_*` variables for
S3-compatible storage).

## Proof

Measured on this machine (Colima VM, 4 CPU, 8 GB RAM, managed Neon, software
H.264). Sources: `PROGRESS.md`, `docs/performance.md`,
`docs/screens/budgets.json`, `docs/screens/a11y.json`.

| What | Measured |
| --- | --- |
| Transcription, MLX Whisper on Metal | 30.17 s for the 4.9-min fixture (593 words) |
| Clip render, 3 clips in parallel | 87.1 s wall (~29 s/clip); clips 14.5 / 5.5 / 16.5 s, all `ready` |
| Warm karaoke re-render | 6.6 s (transcript and window cached) |
| Worker pool, 3 clips | serial 188.7 s vs parallel-4 119.8 s; warm 70.9 s |
| Moment detection, CPU int8 | 26 s warm / 39 s cold on the 4.9-min trailer |
| OBS live view | real OBS 33.0.1 / WebSocket 5.7.6: connected, scene, mic unmuted, 640x360 JPEG (4307 B) |
| SSD import | real mounted DMG: 291.8 s, 1280x720, 33 MB listed and imported |
| Research brain | 3 sourced candidates in 3.8 s (sample feed, `fallback: true`); local Ollama: 3 ideas citing real sources, `fallback: false` |
| Local model manager | 4 Ollama models listed with real sizes; pull with progress, per-model unload, free-all, live host/Ollama/MLX memory |
| Content loop | calendar queue with a 2/day cadence guardrail; long-form concat job; commentary step; swipe-through + saves/shares feeding the ranking score |
| Web TTFB | ~680 ms cold, ~10 ms warm |
| Web LCP, phone/desktop | dashboard 844/760 ms, today 4008/1912 ms, remote 32/40 ms, clips 764/724 ms, admin 80/68 ms; TBT 0 ms; budget 5000 ms |
| Tests | acceptance: 67 passed, 2 skipped, 0 failed; unit 60 passed, 1 skipped; `make check` 2 passed; Playwright page flows pass |
| Accessibility | axe-core 0 serious/critical on 30 pages at phone and desktop |

The two acceptance skips are the voice-over tests, off unless the GPL add-on is
installed.

### Not proven

- **A human verdict on clip quality.** The only footage is a publisher trailer
  (`fixtures/gameplay_4min.mp4`, IGN watermark) and a synthetic stand-in
  (`tests/fixtures/standin_speech_45s.mp4`). `fixtures/stream_10min.mp4` — the
  owner's own gameplay with commentary — does not exist, so the clip-quality
  bar is unmet.
- **Live AI.** The key returns 402/429; every AI path runs on the recorded
  provider and shows its fallback notice.
- **Live research sources.** The brain runs on the saved sample feed; YouTube,
  Reddit and RAWG keys are missing.
- **S3 storage, publishing, Google sign-in, billing.** Not built or stub only.
  The calendar’s “Mark published” is a manual marker (`unproven: youtube-api`);
  TikTok and Instagram are approval-gated and disabled.
- **Production operations.** No TLS termination, backups, structured logging or
  error reporting.
- The screenshots in `docs/screens/` were captured with
  `NEXT_PUBLIC_API_MOCK=1` so every page shows a filled state; the app itself
  never imports the mock layer (`make check` fails if it does).

## Layout

```
web/       Next.js + TypeScript + Tailwind app
api/       FastAPI service and mission/AI logic
worker/    clip rendering worker (FFmpeg)
relay/     MediaMTX configuration
contracts/ openapi.yaml and the mission card JSON schema
docs/      spec, decisions, context export
```

## Secrets

Every key is read from the environment. `.env` is gitignored. Never commit a
key, and never write one into a test or a doc.

## Tests

```sh
make doctor      # environment and connection checks
make accept      # acceptance suite
make web-accept  # Playwright page flows + accessibility
make licence     # dependency licence audit
```

`make accept` is the definition of done for each milestone.
