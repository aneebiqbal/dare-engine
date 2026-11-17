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

- **`legacy/clipdesk/` was not available and will not be.** The spec itself says
  "Clipdesk's code was not available here, only your summary of it." Sprint 2
  confirms the decision: the clip engine is written from scratch and we do not
  wait for the legacy code. `worker/clip/` is that engine.
- `fixtures/stream_10min.mp4` was not provided. M1/M3/M4 acceptance needs a real
  recording; a synthetic stand-in is used for automated tests only, and those
  milestones are not accepted.

## Sprint 3 — web app

| Choice | Reason | Licence |
| --- | --- | --- |
| `openapi-typescript` for `web/lib/api-types.ts` | Typed client generated from `contracts/openapi.yaml`, not hand-written. | MIT |
| Mock layer in `web/lib/mock.ts` | Pages whose backend is blocked by Gate 0 render contract-shaped data behind `NEXT_PUBLIC_API_MOCK=1`. | — |
| axe-core for accessibility | Automated serious/critical checks in `make web-accept`. | MPL-2.0 (dev/test only, not shipped) |
| CSS custom-property tokens in `globals.css` | One token file for both themes; no UI kit dependency. | — |

- **Contract changes.** Sprint 3 added `/results`, `/history`, `/settings` and made
  `Today.daily` nullable and `accepted` explicit. The repo has no git remote, so
  the "contract change in its own pull request" rule cannot be satisfied yet;
  the changes are recorded here instead.
- **Mocked pages are not working pages.** Every page served by the mock layer is
  listed under "Mocked pages" in `PROGRESS.md`.
- **Stream keys.** Masked in the UI, revealed on tap, copied with one button,
  never logged, never in a URL. The key does appear in Next's RSC payload,
  because the client needs it; that is app data, not a URL or a log.

## M1 clip engine

| Choice | Reason | Licence |
| --- | --- | --- |
| faster-whisper 1.2.1 for transcription | Word-level timestamps on CPU, mission windows only. | MIT |
| FFmpeg `subtitles`/`ass` filter for the burn-in | libass renders the hook, word captions and end card from one ASS file. | LGPL (see above) |
| DejaVu Sans (font) | Installed in the worker image so libass has a font. | Free license (Bitstream Vera / public domain) |

- **Spoiler guard scope.** Two signals: no speech (drops the window) and
  letterbox / black bars (flagged for review, not dropped). Letterbox uses
  FFmpeg `cropdetect`; it has **not** been checked on real gameplay footage, so
  it flags rather than drops. Full interface detection (OCR / UI recognition)
  is still out of scope.
- **Beats without an LLM.** The payoff is the last 18 s before Done; setup is the
  three speech-richest 3 s pieces before it. Voice energy is approximated by
  word density. M2 adds the LLM read of the transcript.
- **Stand-in fixture.** `tests/fixtures/standin_speech_45s.mp4` is a synthetic
  test pattern with real recorded speech (macOS `say`). It exists only because
  `fixtures/stream_10min.mp4` was not provided; it is not a gameplay recording.

## Contracts first

`contracts/openapi.yaml` and `contracts/mission-card.schema.json` are written
before code. Changing them needs a human to approve. Sprint 6 regenerates the
contract from the implemented routes with `make contract`; a CI test fails if
the two differ in either direction.

## Sprint 6 decisions

| Choice | Reason | Licence |
| --- | --- | --- |
| Argon2id (`argon2-cffi`) for passwords | Current memory-hard password hash; no password is stored or logged. | MIT |
| Sessions in Postgres, double-submit CSRF | No third-party identity provider this sprint; every state-changing route is protected. | — |
| Invite-only sign-up, admin-issued reset links | No email service; an admin creates a code or a one-time link. | — |
| `DATABASE_URL` pooled + `DATABASE_URL_DIRECT` direct | Neon's PgBouncer is transaction mode and breaks DDL and the worker's row locks; Aiven's URI is direct. | — |
| Local-disk storage by default, S3 behind `STORAGE_DRIVER` | The mock S3 container is not part of the default run. | — |
| OpenAI-compatible chat client (`LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL`) | One client for OpenCode Zen and xAI Grok by changing three values; verified against both providers' docs. | — |
| Piper for voice-over | Local, no paid speech service. Piper is MIT; `rhasspy/piper-voices` declares MIT, individual voice cards vary. | MIT |
| Export package (zip) only | No YouTube/TikTok/Instagram API this sprint. | — |
| FFmpeg `sidechaincompress` ducking | Game audio dips only while the voice bed speaks. | LGPL (see above) |
| `piper-tts>=1.8.0` | `1.2.0` pins `piper-phonemize~=1.1.0`, which has no wheels on this platform. | MIT |

- **Voice-over licence.** Piper is MIT. The voice model repository declares MIT
  at the repo level; the individual voice card is the authority. The UI tells
  the creator that their own voice is safer for monetisation.
- **AI usage.** Every call logs provider, model, tokens, latency and whether a
  fallback was used. The admin sees the provider and model and whether a key is
  present, never the key.
- **Dev sign-in.** Off unless `DEV_AUTH_ENABLED=true`; the API refuses to start
  with it in production. Tests set it.
