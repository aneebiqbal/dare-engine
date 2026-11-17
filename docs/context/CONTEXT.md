# Clipdesk Missions — context index

Read this first. It summarises the application as it exists in the repository
today and links the detailed documents. Everything here was read from the code;
unverified claims are marked **not verified**.

## What it is

Clipdesk Missions turns a gameplay stream into 9:16 Shorts. An admin types
audience questions; an AI writes mission cards (hook, setup, win condition). A
creator accepts missions, taps Start and Done on the phone remote, and the
platform cuts that exact window, transcribes it, picks the payoff, burns hook
text and word captions, lays the frame out for 9:16, renders 1080×1920 H.264,
and can add a local Piper voice-over with ducking. Creators retitle, trim,
restyle and export a zip. Admins manage users, invites, the pool, jobs, AI
usage, the audit log and setup checks. Accounts are email + password with
Argon2id, server sessions and CSRF; sign-up is invite-only.

## Status table

| Feature | Status |
| --- | --- |
| Accounts, sessions, CSRF, roles, invites, lockout, reset | **working locally** (10 tests) |
| Managed PostgreSQL (Neon/Aiven) | **missing** (no URL) |
| Migrations on an empty DB | **working locally** (26 tables) |
| Job queue, backoff, errors | **working locally** (kill/recovery test) |
| Mission cards from questions | **stand-in only** (recorded AI) |
| Live AI | **missing** (no key) |
| Upload → render → Short | **stand-in only** (1.4 MB synthetic fixture) |
| Real gameplay fixture | **missing** |
| Voice-over with the real Piper model | **working locally** (2 tests) |
| Local storage | **working locally** |
| S3 storage | **built, unproven** |
| Relay mid-stream render | **stand-in only** |
| Publishing, Google sign-in, billing, miner | **off / missing** |
| Web app, all pages, light/dark, phone/desktop | **working locally** (11 tests + axe clean) |
| Tours and first-visit hints | **working locally** |
| `make doctor` | **working locally** (11/13; key/model missing) |

## Documents

| File | Contents |
| --- | --- |
| `00-overview.md` | what it is, roles, main flow, status table |
| `01-repository-map.md` | tree, root files, stack versions, line counts |
| `02-services-and-run.md` | compose services, make targets, start/stop/reset, flags |
| `03-configuration.md` | every environment variable and flag |
| `04-data-model.md` | every table, migrations, ER diagram, job queue |
| `05-api.md` | every route, role, request/response, handler |
| `06-web-app.md` | every page, components, shell, tokens, tours, mock |
| `07-auth-and-security.md` | sign-up/in, sessions, CSRF, roles, invites, lockout, reset, weaknesses |
| `08-video-pipeline.md` | upload → render → export, stages, tools, times, 8-hour risk |
| `09-storage.md` | every file location, sizes, retention, disk calculations |
| `10-ai.md` | every AI call, schemas, fallbacks, providers, voice model |
| `11-missions-flow.md` | mission lifecycle with routes and tables |
| `12-tests-and-quality.md` | test inventory, current results, gaps |
| `13-dependencies-and-licences.md` | every dependency, version, licence |
| `14-gaps-and-risks.md` | unfinished, dead code, cleanup, security, operations |
| `15-open-questions.md` | questions only the owner can answer |

## Five things to know first

1. **Nothing has run on a managed database or with live AI.** No URL, no key.
2. **The real gameplay fixture is missing**, so M1/M3/M4 are not accepted.
3. **`piper-tts` 1.8.0 is GPL-3.0-or-later**, while `docs/decisions.md` says MIT.
4. **No retention/cleanup**: recordings, clips, relay segments and upload
   staging accumulate; an 8-hour upload needs ~65 GB.
5. **The session token is stored in plaintext** and `SESSION_SECRET` is unused.

## Verify before relying on this

```sh
make up
make doctor
make accept          # API acceptance suite
make web-accept      # Playwright + axe
.venv/bin/python -m pytest tests/unit -q
```

See `12-tests-and-quality.md` for the results captured when this context was
written.
