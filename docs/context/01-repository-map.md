# 01 — Repository map

## Tree (three levels)

```
clipdesk/
├── api/                     FastAPI service: accounts, missions, clips, admin, AI
│   ├── app/
│   │   ├── llm/             AI provider clients (openai-compatible, recorded, stub, gemini)
│   │   ├── migrations/      Numbered SQL migrations run on startup
│   │   ├── account.py       results, settings, data export, account deletion
│   │   ├── admin.py         admin users/invites/jobs/audit/AI/storage/setup
│   │   ├── ai.py            the seven page-level AI endpoints + usage logging
│   │   ├── auth.py          sign-up/in/out, CSRF, change/reset password, dev sign-in
│   │   ├── clips.py         marks, uploads, clips, trim, voice-over, export, streams
│   │   ├── community.py     public mission page, leaderboard, creator profile
│   │   ├── config.py        all API environment variables
│   │   ├── create_admin.py  `make create-admin`
│   │   ├── db.py            pooled/direct connections + migration runner
│   │   ├── doctor.py        `make doctor` checks
│   │   ├── export_contract.py  `make contract`
│   │   ├── hooks.py         MediaMTX auth/segment hooks, stream status
│   │   ├── main.py          app wiring, CSRF dependency, error shape, health
│   │   ├── missions.py      mission writer, pool, today, assignments, /me
│   │   ├── paging.py        pagination/filter/sort helpers
│   │   ├── storage.py       local + S3 storage interface
│   │   ├── tours.py         tour progress
│   │   ├── users.py         current_user, require_admin, csrf_protect, audit
│   │   ├── llm_recorded.json  recorded AI responses for CI
│   │   ├── help_guide.md    the text the Help AI may quote
│   │   └── schema.sql       legacy Sprint-5 schema; no longer applied (see 14)
│   └── Dockerfile
├── worker/                  render worker
│   ├── app/
│   │   ├── config.py        worker environment variables
│   │   ├── db.py            direct connection
│   │   ├── handlers.py      `render_clip` and `preview_voice` job handlers
│   │   ├── jobs.py          Postgres queue: claim, finish, fail with backoff
│   │   ├── main.py          worker loop + health/ready
│   │   ├── storage.py       local + S3 storage interface (worker copy)
│   │   ├── voice.py         `make voice` model downloader
│   │   └── worker.py        concurrency pool + stale reaper
│   ├── clip/
│   │   ├── engine.py        render_short: cut, transcribe, beats, captions, layout
│   │   ├── beats.py         setup beat selection (LLM or word density)
│   │   ├── caption.py       ASS burn-in + SRT
│   │   ├── layout.py        blur_fit / center_crop / fit_height filtergraphs
│   │   ├── policy.py        spoiler guard, letterbox flag, title flags
│   │   ├── transcribe.py    faster-whisper word timestamps
│   │   ├── tts.py           Piper speech
│   │   ├── voice.py         ducking mix
│   │   ├── llm.py           legacy Gemini client used by beats/cli
│   │   └── cli.py           `python -m clip.cli`
│   └── Dockerfile
├── web/                     Next.js 15 + TypeScript + Tailwind app
│   ├── app/                 one folder per route (see 06)
│   │   └── api/[...path]/   same-origin proxy to the API
│   ├── components/          shell, pages' client components, ui kit, icons, tour
│   ├── data/                tours.json, hints.json
│   ├── lib/                 api.ts, types.ts, mock.ts, server.ts, api-types.ts
│   └── Dockerfile
├── relay/                   MediaMTX config + Dockerfile
├── contracts/               openapi.yaml, mission-card.schema.json
├── tests/
│   ├── acceptance/          pytest + Playwright against the running stack
│   ├── unit/                clip policy/layout, encoder, mock-leak
│   ├── screenshots/         capture.py, a11y.py
│   ├── performance/         bench.py
│   └── fixtures/            standin_speech_45s.mp4, card.json
├── docs/                    spec, prompts, decisions, design, performance, screens/
├── fixtures/                empty (the real 10-min recording is missing)
├── legacy/                  empty
└── .github/workflows/ci.yml
```

## Root files

| File | Purpose |
| --- | --- |
| `docker-compose.yml` | the whole stack (db, api, worker, web, relay) |
| `Makefile` | up/down/accept/test/check/web-accept/screens/doctor/create-admin/voice/contract/types |
| `.env.example` | every variable, no values |
| `.gitignore` | ignores `.env`, `*.mp4`, `node_modules`, `.next`, `m1-render-*` |
| `.dockerignore` | keeps `web/`, `tests/`, `docs/`, `*.md` out of the api/worker build |
| `PROGRESS.md` | milestone status, Gate 0, Sprint 6 report |
| `README.md` | short overview |
| `.github/workflows/ci.yml` | runs `make accept` and `make check` |

## Languages, frameworks, versions

| Area | Choice | Version | File |
| --- | --- | --- | --- |
| web | Next.js / React | 15.1.6 / 19.0.0 | `web/package.json` |
| web | TypeScript | 5.7.3 | `web/package.json` |
| web | Tailwind CSS | 3.4.17 | `web/package.json` |
| web | Geist font | 1.3.1 | `web/package.json` |
| api | FastAPI | 0.115.6 | `api/requirements.txt` |
| api | psycopg | 3.2.3 | `api/requirements.txt` |
| api | argon2-cffi | 23.1.0 | `api/requirements.txt` |
| worker | faster-whisper | 1.2.1 | `worker/requirements.txt` |
| worker | PyAV | 16.1.0 | `worker/requirements.txt` |
| worker | piper-tts | >=1.8.0 | `worker/requirements-voice.txt` (optional) |
| db | PostgreSQL | 16-alpine | `docker-compose.yml` |
| relay | MediaMTX | latest (image `clipdesk-relay`) | `relay/Dockerfile` |
| tests | pytest / Playwright | 8.3.4 / 1.65.2 | `tests/requirements.txt` |

## Line counts (code, excluding `node_modules`/`.next`/`__pycache__`)

| Area | Lines |
| --- | --- |
| `api/` | 3,769 |
| `worker/` | 1,451 |
| `web/` | 9,417 (includes the generated `lib/api-types.ts`, 3,687) |
| `contracts/` | 1,726 (`openapi.yaml`) |
| `tests/` | 1,750 |
| total measured | 20,877 |
