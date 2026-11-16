# Progress

## Milestone M1 — Clip engine on a file: DONE (stand-in)

`make accept`: 14 passed (M0 8, M1 6). Unit tests: 7 passed.

### What runs

```
python -m clip.cli <input> --start 5 --end 35 --card card.json --out-dir ./out
```

`worker/clip/` implements the spec's nine steps: fetch the window
(Start−10 s … Done+5 s), faster-whisper word timestamps, beats, hook, rotating
9:16 layout, ASS burn-in, end card, 1080x1920 H.264 + thumbnail, metadata.

### Verified on the stand-in

- `ffprobe`: 1080x1920 h264, 29.04 s, AAC audio track.
- `captions.srt`: 121 words from the transcript.
- Frames inspected at 1 s / 8 s / 15 s / 28 s: hook text over the payoff frame,
  word captions at the bottom, end card with mission number and result.
- Render time for a 40 s window: ~10 s end to end.

### Improvement pass (this milestone)

- Slowest step: faster-whisper transcription (~4 s for 40 s) — acceptable
  against the spec's two-minute goal.
- Ugliest output: captions were rendering at the vertical centre (ASS alignment
  5) and `fit_height` letterboxed a landscape source into a thin band.
  Fixed both: captions are alignment 2 (bottom), and layout rotation is
  aspect-aware so a landscape capture never gets the letterbox layout.

### Limits (not hidden)

- **The real acceptance run on `fixtures/stream_10min.mp4` has NOT happened.**
  The fixture is missing. Automated tests use
  `tests/fixtures/standin_speech_45s.mp4`, a synthetic test pattern with real
  recorded speech. It is not gameplay.
- Spoiler guard checks for speech only; "no interface on screen" needs a visual
  pass and is not implemented.
- Beats are chosen by word density, not by the LLM reading the transcript.
  That arrives with M2.

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

- **Docker Desktop is broken on this machine**: its VM disk
  `~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw` is
  `root:staff 644`, so the engine cannot resize it (`permission denied`).
  **Colima** is running instead (`colima start --runtime docker`, 4 CPU / 8 GB),
  and the docker context is `colima`. Fix for Docker Desktop:
  `sudo chown $(whoami):staff ~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw`.
- Colima only shares `$HOME` with the VM, so bind-mounted test output must live
  under the repo, not in `/private/var/folders`.
- Host ports 3000, 9000 and 9997 are taken by other projects / an SSH tunnel, so
  the stack publishes 3100 (web), 9100 (S3) and 19997 (relay API).
- MinIO is unavailable (OSS server archived, `quay.io` blocked). Adobe S3Mock is
  the stand-in; see `docs/decisions.md`.

## Next milestone: M2 — Missions

Next three tasks:

1. `POST /admin/questions`: send typed questions to the LLM, validate the cards
   against `contracts/mission-card.schema.json`, store them in the pool.
2. Admin pool page + Today page; a creator can accept or swap.
3. Acceptance: ten typed questions produce ten valid cards; a Playwright test
   accepts one. CI uses `LLM_PROVIDER=recorded`.

### Needs human

- `fixtures/stream_10min.mp4` — a real 10-minute gameplay recording with
  commentary. **Not present anywhere on the machine.** M1's real-fixture run is
  blocked on it.
- `legacy/clipdesk/` — not present. The spec says it was never available, so the
  clip engine is written from scratch, not reused.
- LLM API key for M2 (Gemini). CI can use the recorded provider instead.
- S3 credentials, or keep S3Mock (M0–M4).
- Google OAuth client + test YouTube channel (M5, M6); YouTube Data API key (M8).
- A person to watch the M1 Short and say whether it is actually good.
- A git remote: this repo has none, so the "open a pull request" rule cannot be
  satisfied yet. Commits go to feature branches locally.
