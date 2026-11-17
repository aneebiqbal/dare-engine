# 00 — Overview

## In ten sentences

Clipdesk Missions turns a gameplay stream into a series of 9:16 Shorts. An
admin types audience questions; an AI writes playable mission cards with a hook,
a setup and a win condition. A creator accepts missions, then taps Start and
Done on the phone remote while streaming; each tap pair marks the exact window.
The platform cuts that window, transcribes it, picks the payoff beats, burns
hook text and word captions, lays the frame out for 9:16, and renders a
1080×1920 H.264 Short. A creator can retitle, trim, change the layout and
caption style, add a local Piper voice-over, and export a zip package. Admins
manage users, invites, the mission pool, jobs, AI usage, the audit log and the
setup checks. Accounts are email + password with Argon2id, server sessions and
CSRF; sign-up is invite-only. The database is PostgreSQL, the job queue is
Postgres rows, storage is local disk by default with an S3 driver available, and
the AI is one OpenAI-compatible client. Nothing has run against a managed
database or a live AI key yet; the real gameplay fixture is missing.

## Roles

| Role | Can | Cannot |
| --- | --- | --- |
| `creator` | Today, mission editor, Live, Clips, clip review/trim/export, Results, History, Settings, Help, tours; upload and render their own clips | Any `/admin/*` route (403), other users' rows |
| `admin` | Everything a creator can, plus Users, Invites, Pool, Templates, Jobs, AI usage, Audit log, Setup status | — |
| anonymous | `/welcome`, `/signin`, `/signup`, `/reset`, `/terms`, `/privacy`, `/m/{slug}`, `/leaderboard`, `/creators/{id}` | Everything else (401) |

Roles are enforced in `api/app/users.py` (`require_admin`) and by the router
dependency in `api/app/main.py`. Every query is scoped by `user_id` unless the
role is admin.

## The main flow today

1. `make create-admin` creates the first admin (`api/app/create_admin.py`).
2. Admin signs in, opens **Admin → Invites**, creates a code.
3. Creator signs up at `/signup?code=…` (`POST /auth/sign-up`).
4. Admin opens **Admin → Pool**, types questions, clicks **Write cards**
   (`POST /admin/questions` → `api/app/ai.py` → `POST /ai/...`), then approves
   (`POST /admin/pool/{id}/approve`).
5. Creator opens **Today**, accepts a mission (`POST /assignments`).
6. Creator opens **Go Live** (issues a stream key) or **Remote**.
7. Creator taps Start and Done (`POST /marks`); the API enqueues one
   `render_clip` job per mission (`api/app/clips.py`).
8. The worker claims the job (`worker/app/jobs.py`), renders
   (`worker/clip/engine.py`), stores the Short, and marks the clip `ready`.
9. Creator opens **Clips → review**, retitles/trims/styles, optionally adds a
   voice-over, and exports a zip (`GET /clips/{id}/export`).

## Status table

| Feature | Status | Evidence |
| --- | --- | --- |
| Email/password accounts, sessions, CSRF, roles | **working locally** (real DB) | `tests/acceptance/test_r1_auth.py`, 10 passed |
| Invite-only sign-up, lockout, reset links | **working locally** | same file |
| Managed PostgreSQL (Neon/Aiven) | **missing** (no URL supplied) | `PROGRESS.md` Gate 0 |
| Migrations on an empty database | **working locally** | 26 tables; `api/app/migrations/` |
| Job queue with backoff and errors | **working locally** | `test_s1_parallel.py` |
| Mission cards from typed questions | **stand-in only** (recorded AI) | `test_m2_missions.py` |
| Live AI calls | **missing** (no key) | `LLM_PROVIDER=recorded` |
| Upload → render → Short | **stand-in only** (synthetic 45 s fixture) | `test_r2_local_path.py` |
| Real gameplay fixture | **missing** | `fixtures/` is empty |
| Voice-over with the real Piper model | **working locally** | `test_sprint6_voice.py`, 2 passed |
| Local disk storage | **working locally** | `api/app/storage.py` |
| S3 storage driver | **built, unproven** (no credentials) | `STORAGE_DRIVER=s3` path |
| Relay (MediaMTX) mid-stream render | **stand-in only** | `test_m4_relay.py` |
| Publishing to YouTube/TikTok/Instagram | **behind a flag, off**; `POST /clips/{id}/post` only flips state | `api/app/clips.py` |
| Google sign-in | **missing/off** (route absent) | `contracts/openapi.yaml` has no `/auth/google/*` |
| Question miner | **missing/off** | no route, no job |
| Billing / plans | **off**; `plan` is hardcoded `free` | `api/app/account.py` |
| Mock layer | **screenshots only**; barred from app code | `make check`, `web/lib/mock.ts` |
| Web app (all pages, light/dark, phone/desktop) | **working locally** | `make web-accept`, 11 passed + axe clean |
| Tours and first-visit hints | **working locally** | `test_sprint6_tour.py` |
| `make doctor` | **working locally** (11/13; only key/model missing) | `api/app/doctor.py` |
