# Progress

## Milestone M0 — Skeleton: DONE

`make accept` passes: 8 tests, every service healthy.

```
tests/acceptance/test_m0_health.py  8 passed
```

### What runs

| Service | Image | URL |
| --- | --- | --- |
| web | `./web` (Next.js 15, TS, Tailwind, Geist) | http://localhost:3100 |
| api | `./api` (FastAPI) | http://localhost:8000 |
| worker | `./worker` (FastAPI + FFmpeg) | http://localhost:8001 |
| db | postgres:16-alpine | internal |
| storage | adobe/s3mock (Apache-2.0) | http://localhost:9100 |
| relay | `./relay` (MediaMTX + curl) | RTMP :1935, API http://localhost:19997 |

### Done

- `docs/spec.md` exported from the design PDF.
- `contracts/openapi.yaml` and `contracts/mission-card.schema.json`.
- Compose stack with a health check per service; `docker compose up -d --wait` is green.
- API: `/healthz`, `/healthz/ready`, `/today`; 13-table schema; job-queue table.
- Worker: row-locking job loop.
- Web: landing page + `/api/health`.
- `make accept`, `.github/workflows/ci.yml`.

### Environment notes (not code)

- **Docker Desktop is broken on this machine**: its VM disk
  `~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw` is
  `root:staff 644`, so the engine cannot resize it (`permission denied`).
  **Colima** is running instead (`colima start --runtime docker`, 4 CPU / 8 GB),
  and the docker context is `colima`. Fix for Docker Desktop:
  `sudo chown $(whoami):staff ~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw`.
- Host ports 3000, 9000 and 9997 are taken by other projects / an SSH tunnel, so
  the stack publishes 3100 (web), 9100 (S3) and 19997 (relay API).
- MinIO is unavailable (OSS server archived, `quay.io` blocked). Adobe S3Mock is
  the stand-in; see `docs/decisions.md`.

### Next milestone: M1 — Clip engine on a file

Next three tasks:

1. Build `worker/clip/`: fetch the window (Start−10s … Done+5s), transcribe with
   faster-whisper, pick beats, hook, 9:16 layout, burned word captions, end card,
   render 1080x1920 H.264 + thumbnail, write the caption/metadata files.
2. Add `faster-whisper` to the worker and a CLI entry point so a file + two
   timestamps can be rendered without the API.
3. `tests/acceptance/test_m1_clip.py`: run on a recording, `ffprobe` asserts
   1080x1920, <60s, audio track; caption file contains transcript words.

### Needs human

- `fixtures/stream_10min.mp4` — a real 10-minute gameplay recording with
  commentary. **Not present anywhere on the machine.** M1 acceptance needs it;
  until then automated tests use a clearly labelled synthetic stand-in.
- `legacy/clipdesk/` — not present. The spec says it was never available, so the
  clip engine is written from scratch, not reused.
- Docker Desktop ownership fix (above) if we want to move off Colima.
- LLM API key (M2); S3 credentials or keep S3Mock (M0–M4); Google OAuth client +
  test YouTube channel (M5, M6); YouTube Data API key (M8).
- A person to watch the M1 Short and say whether it is actually good.
- A git remote: this repo has none, so the "open a pull request" rule cannot be
  satisfied yet. Commits go to the `m0-skeleton` branch locally.
