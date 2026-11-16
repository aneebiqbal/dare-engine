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
