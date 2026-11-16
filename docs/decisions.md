# Decisions

One line of reasoning per choice. Add the licence check for every dependency.

## Stack (from `docs/spec.md`)

| Choice | Reason | Licence |
| --- | --- | --- |
| Next.js + TypeScript + Tailwind for `web/` | One app serves dashboard, phone remote and public pages. | MIT |
| FastAPI for `api/` and `worker/` | The clip pipeline is Python; one language covers both. | MIT |
| PostgreSQL for data and the job queue | One service to run and back up; row locking replaces Redis/Celery. | PostgreSQL |
| MediaMTX for the relay | MIT, RTMP in, fMP4 segments out, RTMP forward, HTTP auth hooks. | MIT |
| Adobe S3Mock for S3-compatible storage | Local stand-in for S3 until real credentials arrive. | Apache-2.0 |
| FFmpeg for rendering | Already the plan; libass captions, 9:16 scale, H.264 out. | LGPL-2.1+ (see note) |
| faster-whisper for transcription | CPU-friendly word timestamps, windows only. | MIT |
| Gemini behind `api/llm/` | JSON mission cards, titles and payoff picks; swappable. | Proprietary API |

### Notes

- **Storage.** MinIO was the first choice, but its open-source server is
  archived (downloads return 410) and `quay.io` is blocked from this network
  (401 even from the host). Adobe S3Mock (Apache-2.0) is pulled from Docker Hub
  and provides the S3 subset we need. It is a test tool, not production storage:
  before launch, swap the `storage` block for AWS S3 or Cloudflare R2 and provide
  credentials. The app talks to it through the `S3_*` environment variables, so
  the swap is configuration only. S3Mock is path-style only; the client must set
  path-style addressing.
- **FFmpeg** is LGPL-2.1-or-later when built without GPL-only components. The
  distro package we install may include GPL codecs (libx264). We invoke it as a
  separate binary, not a linked library. Flagged for legal review before any
  commercial launch; a Cisco OpenH264 (BSD) build is the fallback.
- **faster-whisper** wraps OpenAI Whisper (MIT) and CTranslate2 (MIT). No GPL.

## Repository layout

`web/ api/ worker/ relay/ contracts/ docs/` exactly as the spec's build plan
requires, so work packages can touch separate folders.

## Missing inputs (see `PROGRESS.md` → Needs human)

- `legacy/clipdesk/` was **not available**. The spec itself says "Clipdesk's code
  was not available here, only your summary of it." The clip engine is therefore
  written from scratch against the spec's nine steps, not reused.
- `fixtures/stream_10min.mp4` was not provided. M1 acceptance needs a real
  recording; a synthetic stand-in is used for automated tests only.

## M1 clip engine

| Choice | Reason | Licence |
| --- | --- | --- |
| faster-whisper 1.2.1 for transcription | Word-level timestamps on CPU, mission windows only. | MIT |
| FFmpeg `subtitles`/`ass` filter for the burn-in | libass renders the hook, word captions and end card from one ASS file. | LGPL (see above) |
| DejaVu Sans (font) | Installed in the worker image so libass has a font. | Free license (Bitstream Vera / public domain) |

- **Spoiler guard scope.** The spec says "no speech *and no interface on screen*".
  M1 drops windows with no transcribed speech. Detecting an on-screen interface
  needs a visual pass (OCR / UI detection) and is not in M1. Recorded as a
  limit, not silently skipped.
- **Beats without an LLM.** The payoff is the last 18 s before Done; setup is the
  three speech-richest 3 s pieces before it. Voice energy is approximated by
  word density. M2 adds the LLM read of the transcript.
- **Stand-in fixture.** `tests/fixtures/standin_speech_45s.mp4` is a synthetic
  test pattern with real recorded speech (macOS `say`). It exists only because
  `fixtures/stream_10min.mp4` was not provided; it is not a gameplay recording.

## Contracts first

`contracts/openapi.yaml` and `contracts/mission-card.schema.json` are written
before code. Changing them needs a human to approve.
