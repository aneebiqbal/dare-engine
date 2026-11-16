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

## Next milestone: M2 — Missions

Next three tasks:

1. `POST /admin/questions` → Gemini provider in `api/llm/`, validate every card
   against `contracts/mission-card.schema.json`, store candidates in the pool.
2. Admin pool page (`/admin`) and Today page; accept and swap
   (`POST /assignments`, `POST /assignments/{id}/swap`).
3. Acceptance: ten typed questions → ten valid cards; a Playwright test accepts
   one. CI uses `LLM_PROVIDER=recorded`.

### Needs human

- All six Gate 0 items above.
- A git remote, so the "open a pull request" rule can be satisfied.
