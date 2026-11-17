# Progress

## Gate 0 — human supplies (checked at the start of this session)

| Item | Status |
| --- | --- |
| `fixtures/stream_10min.mp4` (real gameplay + commentary) | **MISSING** |
| LLM API key in `.env` | **MISSING** (no `.env` at all) |
| Git remote on the organisation's Git host | **MISSING** (`git remote -v` empty) |
| Google OAuth client + test YouTube channel | **MISSING** |
| YouTube Data API key | **MISSING** |
| Payment provider test-mode keys | **MISSING** |

**Accepted on stand-in data only:** M1. Because the real fixture is missing, M1,
M3 and M4 are **not accepted** and will not be until `fixtures/stream_10min.mp4`
exists and the run is made.

## Sprint 3 — the web app (W0–W7)

Status: W0 done; W1–W6 pages built; W7 journey passes. 11 Playwright flow tests
pass, axe-core reports **0 serious/critical** on the five main pages at phone and
desktop. 64 screenshots in `docs/screens/`.

### W0 design system

- `web/app/globals.css` — one token file: colour, type, spacing, radius, motion;
  light (warm cream) and dark (OLED) themes.
- `web/components/ui.tsx` — Button, Input, Textarea, Field, Card (double-bezel),
  Badge, Eyebrow, Tabs, Dialog, Toast, Table, EmptyState, Skeleton, PageState
  (loading / error / empty / filled).
- `/styleguide` shows every component in both themes.

### Pages

Real backend: `/` Today, `/admin` pool (M2). Everything else is listed under
"Mocked pages" and is **not** reported as working against the real backend.

**Mocked pages** (served by `web/lib/mock.ts` behind `NEXT_PUBLIC_API_MOCK=1`):
`/welcome` (partial), `/signin`, `/m/[slug]`, `/leaderboard`, `/creators/[id]`,
`/terms`, `/privacy`, `/remote` (marks), `/clips`, `/clips/[id]`, `/live`,
`/results`, `/history`, `/settings`.

### Three worst screens, and what I changed

1. **Phone remote** — the mission badge stretched full width. Fixed: `Badge` is
   now `self-start`.
2. **Styleguide** — the light theme never applied because the theme toggle
   re-asserted dark on mount. Fixed: the toggle honours `?theme=light|dark`.
3. **Phone remote offline queue** — a tap queued while offline never flushed,
   because the assignment was created while still offline. Fixed: `flush` creates
   the assignment first; the Playwright test now covers offline → online.

### Commands

- `make accept` — milestone tests (M0/M1/M2), real API.
- `make web-accept` — page flows + axe, mock layer, then restores the real build.
- `make screens` — screenshots + a11y report.

## Sprint 5 — finish, speed up, live show

Status: `make accept` **28 passed**. Part 0 items 1–3 done; item 4 (M12/M13) not
started. Part 1: S1 and S3 done, S2 not started. Part 2 not started.

### Part 0

- **R3 / M4 — built, unproven on real gameplay.** MediaMTX records fMP4 segments
  to a shared volume, authenticates the stream key through
  `/hooks/relay/auth`, registers segments, and `Done` enqueues a render from the
  segments. The Live page polls `/streams/{id}/status` every second. Test: the
  stand-in pushed over RTMP (`-stream_loop 3`) shows **connected**, Start at
  stream time 8 and Done at 16 produce a ready Short in <180 s while the stream
  is still running.
- **R6 proof — done.** Deleting an account removes the user, assignments,
  sessions, streams, clips, attempts and the S3 objects under
  `recordings/<user_id>/` and `clips/<clip_id>/`. A test asserts zero rows and
  zero files, and 401 afterwards.
- **D1 — done.** `docs/design.md`: concept, type scale, colour roles, spacing,
  motion, the three signature moments. D2/D3 not started.

### Part 1

- **S1 — done.** `WORKER_CONCURRENCY` (default = CPU count) render pool plus a
  stale-job reaper (`WORKER_STALE_SECONDS`, default 600). Measured on this
  machine: **serial 188.7 s** vs **parallel-4 119.8 s** for three clips; a
  killed worker's jobs are recovered on restart and the test ends with exactly
  three clips, no duplicates. Numbers in `docs/performance.md`.
- **S3 — done.** `detect_encoder()` picks `h264_videotoolbox` / `h264_nvenc` /
  `h264_qsv` when present, else `libx264`; the choice is logged and stored in
  the metadata. Unit tests cover both paths.

### Not started

S2 (stages + progress + transcript cache), Part 2 (L1–L6), D2/D3, M12, M13.

## Sprint 4 — make every page real

Status: `make accept` **25 passed**; `make web-accept` **11 passed** + axe clean
against the real backend (`NEXT_PUBLIC_API_MOCK=0`).

### R1 — DONE

- `POST /auth/dev/sign-in` creates a **real user and a real session** (cookie),
  gated by `DEV_AUTH_ENABLED`. The API **refuses to start** when that flag is set
  in `APP_ENV=production`; a test proves it.
- Every endpoint takes the session user; `/today`, `/clips`, `/uploads`,
  `/settings` and `/results` filter by `user_id`.
- Web: same-origin `/api/*` proxy keeps the cookie on the web origin; the
  server components forward it to the API.
- Tests: two dev users are isolated, anonymous requests get 401, the production
  guard trips. `make check` fails if `web/lib/mock.ts` is imported by app code.

### R2 / M3 — built, unproven on the real fixture

- Real `POST /marks`, `POST /uploads` (multipart), `GET /clips`, `PATCH`,
  `approve`, `download`, `POST /streams`, `GET /history`.
- Worker `render_clip`: S3 download → `clip.engine.render_short` → S3 upload →
  clip row `ready`.
- Acceptance on the stand-in: three marks → three real Shorts. **M3 is not
  accepted** — `fixtures/stream_10min.mp4` is missing.

### R4 / M7 — built

- Real `/m/{slug}`, `/missions/{id}/leaderboard`, `/creators/{id}`.
- Two dev users' attempts rank correctly (test passes).

### R5 / R6 / R7 — built

- `/metrics` manual entry updates the mission score; `/results` reads it.
- `/settings`, `DELETE /account` (removes rows and stored files).
- `/admin/templates`, `/admin/users`, `/admin/jobs`, `/admin/jobs/{id}/retry`.

### Mocked pages (with the exact blocker)

| Page | Blocker |
| --- | --- |
| `/signin` Google path | Gate 0: Google OAuth client |
| `/live` real relay connection | Gate 0: no stream key/relay credentials for a real stream |
| `/remote` mid-stream marks | Gate 0: needs a real live stream |
| `/results` YouTube collector | Gate 0: YouTube Data API key |

Everything else is real.

### Built, unproven against the real service

| Feature | Stand-in | Waiting on |
| --- | --- | --- |
| Google sign-in (M5) | dev sign-in | Gate 0: OAuth client |
| YouTube posting (M6) | `POST /clips/{id}/post` flips state | Gate 0: OAuth + channel |
| Question miner (M8) | recorded LLM | Gate 0: YouTube Data API key |
| Billing (M10) | plan field on `/settings` | Gate 0: payment keys |
| TikTok / Instagram (M14) | — | platform approval |

## Milestone M2 — Missions: DONE (recorded LLM; live call untested)

`make accept`: 18 passed (M0 8, M1 6, M2 4). Unit tests: 12 passed.

### What runs

- `POST /admin/questions` → `api/llm/` provider → every card validated against
  `contracts/mission-card.schema.json` → stored as pool candidates.
- `GET /admin/pool`, `POST /admin/pool/{id}/approve`.
- `GET /today` (daily mission + picks + accepted state), `POST /assignments`,
  `POST /assignments/{id}/swap`.
- Web: `/admin` (type questions, approve) and `/` (Today, accept/swap).
- Providers: `recorded` (CI/dev default, `api/app/llm_recorded.json`), `gemini`
  (REST, no SDK), `stub`. `GEMINI_API_KEY` unset → no live call.

### Verified

- Ten typed questions → ten schema-valid cards; pool lists them; approving one
  moves it to Today; Playwright signs in (dev user), writes cards, approves one,
  and accepts a mission on the Today page.
- The M2 tests truncate the mission tables first, so they are repeatable.

### Not done

- The live Gemini run (no key). The recorded provider always returns the same
  ten cards, so the live question→card mapping is untested.
- Real accounts: M2 uses a seeded `dev-user`; M5 adds Google sign-in.

## Milestone M1 — Clip engine on a file: stand-in only, NOT accepted

`make accept`: 14 passed (M0 8, M1 6). Unit tests: 12 passed.

### Closed this session

- **Interface detection in the spoiler guard.** FFmpeg `cropdetect` measures
  black bars; a frame that is more than 15% black is flagged
  (`spoiler_flags.letterbox`). It flags for review rather than dropping, because
  it has not been checked on real gameplay footage. No speech still drops.
- **LLM beat selection with a word-density fallback.** `worker/clip/llm.py` is a
  dependency-free Gemini REST client; `select_setup()` uses it when
  `GEMINI_API_KEY` is set and falls back to word density otherwise. Not exercised
  live (no key).
- Recorded in `docs/decisions.md`: the clip engine stays hand-written; we do not
  wait for `legacy/clipdesk/`.

### Verified on the stand-in

- `ffprobe`: 1080x1920 h264, 29.04 s, AAC audio.
- `captions.srt`: 121 words. Frames inspected: hook, bottom word captions, end card.
- Letterboxed test clip is flagged; the full-frame stand-in is not.

### Still open

- The real 10-minute fixture run.
- Live LLM beat selection.
- A human judgement of whether the Short is actually good.

## Milestone M0 — Skeleton: DONE

`make accept` green; every service healthy.

| Service | Image | URL |
| --- | --- | --- |
| web | `./web` (Next.js 15, TS, Tailwind, Geist) | http://localhost:3100 |
| api | `./api` (FastAPI) | http://localhost:8000 |
| worker | `./worker` (FastAPI + FFmpeg + faster-whisper) | http://localhost:8001 |
| db | postgres:16-alpine | internal |
| storage | adobe/s3mock (Apache-2.0) | http://localhost:9100 |
| relay | `./relay` (MediaMTX + curl) | RTMP :1935, API http://localhost:19997 |

### Environment notes (not code)

- **Docker Desktop is broken on this machine**: its VM disk is `root:staff 644`,
  so the engine cannot resize it. **Colima** is running instead
  (`colima start --runtime docker`, 4 CPU / 8 GB), docker context `colima`.
  Fix: `sudo chown $(whoami):staff ~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw`.
- Colima only shares `$HOME` with the VM, so bind-mounted test output must live
  under the repo, not in `/private/var/folders`.
- Host ports 3000/9000/9997 are taken, so the stack publishes 3100/9100/19997.
- MinIO is unavailable (archived, `quay.io` blocked); Adobe S3Mock stands in.

## Next milestone: M3 — Marks and the local path

Next three tasks:

1. Phone remote page with Start and Done (`POST /marks`), storing stream time.
2. Local upload path: upload a recording plus its marks, enqueue one clip job
   per mission, worker renders via `worker/clip/`.
3. Acceptance: upload the fixture with three marks → three Shorts on the Clips
   page, each downloadable. Blocked on the real fixture.

### Needs human

- All six Gate 0 items above.
- A git remote, so the "open a pull request" rule can be satisfied.
