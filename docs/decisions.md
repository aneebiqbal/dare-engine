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
| Voice-over as an optional add-on | The installed `piper-tts` 1.8.0 is **GPL-3.0-or-later** (the old MIT `rhasspy/piper` is archived). It is not in the default build; `make voice` installs it into the worker on demand. | GPL-3.0 (optional, off by default) |
| Export package (zip) only | No YouTube/TikTok/Instagram API this sprint. | — |
| FFmpeg `sidechaincompress` ducking | Game audio dips only while the voice bed speaks. | LGPL (see above) |
| `piper-tts>=1.8.0` | `1.2.0` pins `piper-phonemize~=1.1.0`, which has no wheels on this platform. | GPL-3.0-or-later |

- **Voice-over licence.** The `piper-tts` PyPI package is GPL-3.0-or-later
  (metadata: `License: GPL-3.0-or-later`, home page `OHF-voice/piper1-gpl`). The
  old `rhasspy/piper` was MIT but is archived. The voice model repository
  declares MIT at the repo level; individual voice cards vary. Because the core
  must stay free of GPL code, voice-over is a clearly separated optional add-on:
  `worker/requirements.txt` has no voice dependency, `worker/requirements-voice.txt`
  holds it, and `make voice` installs it into the running worker. The CI licence
  check (`tests/licence_check.py`) fails if a GPL/AGPL package appears in the core
  requirements. The UI tells the creator that their own voice is safer for
  monetisation.
- **AI usage.** Every call logs provider, model, tokens, latency and whether a
  fallback was used. The admin sees the provider and model and whether a key is
  present, never the key.
- **Dev sign-in.** Off unless `DEV_AUTH_ENABLED=true`; the API refuses to start
  with it in production. Tests set it.

## Sprint 1 decisions

| Choice | Reason | Licence |
| --- | --- | --- |
| One shared client in `shared/llm.py`, copied into both images | The worker's beat selection and the API must use the same code; the legacy Gemini path is removed. | MIT (our code) |
| Session tokens stored as HMAC-SHA256 with `SESSION_SECRET` | A database dump no longer yields usable sessions. | — |
| Upload chunk routes require a session | The `upload_id` is a capability, not an authorisation. | — |
| Retention sweep on startup and `make cleanup` | An 8-hour recording cannot fill the disk; raw recordings go after 7 days, previews too. | — |
| Voice-over as an optional add-on | `piper-tts` is GPL-3.0; the core stays free of GPL code and `make voice` installs it on demand. | GPL (optional) |
| `tests/licence_check.py` in CI | Confirms no GPL/AGPL package in the core requirements. | — |

## Sprint 7 decisions — automatic moments and a clip grammar

| Choice | Reason | Licence |
| --- | --- | --- |
| Detector scores transcript + audio + scene cuts, cheapest signal first | One pass over the file; only the top candidates need the expensive video work. | — |
| CUDA Whisper when `ctranslate2` reports a GPU, else CPU int8 | Uses the GPU when present, never assumes one; the path is logged and shown. | MIT |
| Clip grammar in `worker/clip/templates.json` | Templates are added without code; 5 visual templates and 3 caption styles. | — |
| Cold open first, then hook text, context flash-back, payoff | Opens on the moment, never a slow lead-in; the payoff stays the longest beat. | — |
| Captions re-mapped onto disjoint beat ranges | The old hook/setup/payoff concat mapped words out of order; word-sync is now monotonic. | — |
| Studio runs in the worker, storage stays local | No cloud render, no upload of the source or the clips. | — |

- **Kept:** `transcribe.py`, `layout.py` filtergraphs, `caption.py` ASS/SRT,
  `policy.py` spoiler/letterbox guard, `voice.py` ducking, the job queue and the
  local storage driver.
- **Replaced:** the fixed hook + setup + payoff concatenation in `engine.py` with
  the beat grammar, and the caption time mapping (the old one produced
  out-of-order captions when the hook was cut from the middle of speech).
- **Local only.** The studio uploads a recording to the API container's local
  storage, the worker reads it from the shared volume, and every temp directory
  (upload, playback, detect, render) is removed after use. Nothing leaves the
  machine. The source recording stays the user's to keep on the SSD.
- **Retention.** `api/app/retention.py` still sweeps raw recordings and previews
  after `RECORDING_RETENTION_DAYS`; studio recordings live under
  `recordings/<user_id>/studio-…` so the same sweep covers them.

## Research-brain decisions

| Choice | Reason | Licence |
| --- | --- | --- |
| RAWG for the games database | One API key, no OAuth dance; catalog is large enough for launch. IGDB needs a Twitch app and a token refresh. | — |
| YouTube Data API + Reddit + gaming-news RSS | Three independent free sources, so one outage does not stop the brain. No Google Trends (closed alpha, against terms). | — |
| Sources stored in `mission_sources`, not in the card JSONB | The mission-card schema stays stable; an idea with no source row is simply never shown. | — |
| Every citation checked against the fetched feed | The model cannot invent a URL and have it shown; an idea with no real source is dropped. | — |
| Daily gate is a database read, not an in-process cron | Idempotent across API replicas and restarts; no extra dependency. The loop checks every 5 minutes. | — |
| Recorded provider + saved sample feed | The whole pipeline is provable without keys; the run is flagged `fallback`. | — |
| Card identity is an SVG endpoint | No remote image dependency; the same card is used in the admin queue and the dare editor. | — |
| Contract path resolves in Docker and in a local checkout | `make contract` and the API unit tests run from the repo root, where `contracts/` is at the root. | — |

## OBS live view decisions

| Choice | Reason | Licence |
| --- | --- | --- |
| obs-websocket 5.x over `simpleobsws` | OBS 31+ ships obs-websocket 5.x; `simpleobsws` is the maintained client. | MIT |
| Periodic scene snapshot, not a video feed | `GetSourceScreenshot` on the program scene is the only frame OBS exposes without a second pipeline; the page labels it "periodic snapshot, not a live video feed". | — |
| Real status + manual ticks in one checklist | Connection, streaming, recording, scene and mic mute come from OBS; HDCP/mic/radio stay manual because OBS cannot see them. | — |
| Clear unreachable state | If OBS is off or the WebSocket server is disabled, the endpoint returns `connected:false` + how to enable it, never a spinner. | — |
| `OBS_WS_URL` defaults to `host.docker.internal` | The API runs in a container; the host is `host.docker.internal` under Colima. | — |

## SSD import decisions

| Choice | Reason | Licence |
| --- | --- | --- |
| Host bridge (`local/ssd_bridge.py`) over a container mount of `/Volumes` | A Linux container cannot see the Mac's `/Volumes`; Colima shares `$HOME`, so the bridge copies into a shared inbox. | — |
| Import by local copy, never a cloud upload | The source stays on the SSD; the API copies into its own local storage and probes it. | — |
| Import enqueues `detect_moments` | Importing a video starts the local processing job, not just a file copy. | — |
| Bridge refuses paths outside the mount dir | The endpoint takes a host path; it must not be an arbitrary-file-read primitive. | — |
| Top level + one folder deep | A full recursive scan of a multi-terabyte SSD would hang the page; camera rolls and Desktop/Movies are one level down. | — |

## Local MLX clip engine decisions

| Choice | Reason | Licence |
| --- | --- | --- |
| MLX Whisper runs in a host bridge, not the container | The worker is a Linux container with no Metal. The worker streams the file bytes to the host, which returns word timestamps. | MIT (mlx-whisper) |
| Stream the file, not a path | The container's `/data/storage` is not visible on the host; a path would not resolve. `http.client` streams in 1 MB chunks. | — |
| Fall back to faster-whisper CPU when `MLX_WHISPER_URL` is empty | The default stack keeps working with no host setup; the compute path is stored and shown. | — |
| Visual strikingness from 1 fps 32×32 gray frames | ~1 KB/s; dark (<8% luma) and blown-out (>95%) frames score 0 and are never picked as the cold open. | — |
| Karaoke caption style | One ASS event per phrase with `{\k}` word timings; the style's primary colour highlights word by word. | — |
| Rendering stays in the container (libx264) | The container has no VideoToolbox; `detect_encoder()` already prefers it when present. A host render bridge is future work. | — |

## Ship sprint — cloud + desktop split

| Choice | Reason | Licence |
| --- | --- | --- |
| Cloud runs only `web` + `api` + managed Postgres | A gamer needs the plan and the results, not a render. The cloud stays on the smallest plan. | — |
| The desktop runs the worker, models, capture and SSD | 20 GB recordings and 18 GB models cannot live on a web host; uploading them defeats the point. | — |
| One API contract, two clients | The browser and the desktop app call the same HTTP API and database; there is no sync step. | — |
| Tauri for the desktop shell | ~3–10 MB vs Electron's ~150 MB, Rust backend suited to FFmpeg and sidecars, no bundled Chromium. | MIT/Apache-2.0 |
| Integrate OBS over obs-websocket 5.x, bundle an FFmpeg recorder for the no-OBS case | OBS is the reliable default; a user who has not set it up can still record. We do not reinvent OBS. | OBS GPL-2.0 (external), obs-websocket MIT |
| Qwen2.5-VL-7B (Apache-2.0) for the vision pass | Small, Apple-Silicon-friendly at 4-bit (~6–8 GB), stable JSON output; the MLX 4-bit build runs on Metal. | Apache-2.0 |
| The vision pass is sampled, not per-frame | One frame every 5 s (default), capped at 40 frames; the VLM loads only for the pass and is unloaded + verified. | — |
| Rate limit per IP, stricter on `/auth` and `/admin` | Login already locks out; this caps a script that scrapes or hammers the API. | — |
| Error reports in Postgres, read on the admin overview | No external service needed; survives a restart. | — |
| `make backup` → `pg_dump` gzip | A managed database has PITR; a self-hosted one needs a dump. | — |
| A project's stage is derived, never stored | It is computed from the real recording, jobs, clips and exports, so the dashboard cannot claim a stage the artifacts do not support. | — |
| The analysis queue is one lane (advisory lock) | Two projects never analyse — and never load models — at the same time; the oldest queued project runs first. | — |

> Updated 2026-11-24: the advisory lock became a self-expiring `pipeline_lane`
> heartbeat lease, because an orphaned session on a managed database can hold a
> session advisory lock after its worker dies and wedge the lane.
| The setup wizard verifies the real endpoint before marking a step done | A step is not "done" because the user clicked; the SSD bridge, OBS WebSocket, model bridge and provider config are actually asked. | — |
| Caption edits are a stored override, not a re-transcribe | The transcript is cached on the clip; editing words or timings re-renders from the cache, so an edit is fast and the source is untouched. | — |
| Engine activity is logged to Postgres, not stdout | The admin overview can show what loaded, what unloaded and what was cleaned up, and it survives a restart. | — |

### Capture and clip projects studied

Public docs and repositories, read before building the capture path. What we
took from each:

| Project | What it is | What we took |
| --- | --- | --- |
| OBS Studio | The open-source capture/stream standard (GPL-2.0). | The scene/source model and the replay buffer as the reliable default; we integrate it rather than replace it. |
| obs-websocket | WebSocket control for OBS (MIT). | The existing 5.x client: connection, stream/record state, scene, mic, snapshot. |
| Segra | Record and clip games, built on OBS/libobs. | The "record through OBS, clip after" flow; per-game profiles. Confirms OBS is the capture layer. |
| OpenShorts | Open-source short-video tooling. | The 9:16 vertical output and caption-first framing. |
| AutoClip | Automatic clipping from a stream/recording. | The idea that clipping should be automatic but human-approved. |
| Cap | Open-source screen recorder with automatic zoom. | The no-OBS built-in recorder: simple, one-click, MP4 out. |
| ShareX | Open-source screen capture and sharing. | The "record a region, save a file" simplicity for the bundled recorder. |
| Insights Capture | OBS alternative for automatic game recording and clipping. | The replay-buffer + auto-highlight UX; validates the out-of-the-box feature. |
| Medal / Outplayed | Consumer clip tools with replay buffers. | The "instant clip" expectation; the admin still decides what to publish. |
| NVIDIA Highlights / ShadowPlay | Driver-level automatic highlights. | The vision-detector idea: the software watches and proposes; the human picks. |
| Loom / Screen Studio | Polished no-setup recorders. | The no-OBS path must be one click and produce a file, not a project. |
| LM Studio / Jan | Local model managers. | The Models & Setup UX: install state, size, fit, download progress, unload, live memory. We copy the pattern, not the code. |

**Honest scope.** This is a reading of public material, not a code audit of each
project. The OBS integration is the proven path; the bundled FFmpeg recorder and
the Tauri shell are built here but need a real user on real hardware to call
finished.

### Moment-selection tools studied (2026-11-24)

Read before rebuilding the picker away from vision-first. What we took from each:

| Project | What it does | What we adopted |
| --- | --- | --- |
| OpenShorts (`mutonby/openshorts`, MIT) | faster-whisper word timestamps + PySceneDetect boundaries, then an LLM scores the transcript and returns 3–15 moments of 15–60 s with a 0–100 virality score, hook line and reason. Runs fully local against any OpenAI-compatible endpoint. | Transcript-first scoring; clips **start on a sentence** (windows scored, not free-floating); scene boundaries as a structural prior; a virality score + hook line + reason per clip; the scorer is a pluggable local model, never a cloud dependency. |
| Clips Kitty / clips-studio (`ColinGPT9/clips-studio`, AGPL-3.0; SDK MIT) | Five signals in 1-second bins — transcript, audio excitement/bursts/silence→explosion, visual cuts/motion/reactions — normalized within the video. The LLM reads the transcript **plus the event timeline**. Every clip clearing `min_score` is kept (**no arbitrary cap**). Windows scored ~8 at a time; only a transcript pick below the bar hides an overlapping signal peak; scoring budget goes to the strongest peaks, not the earliest; later local versions rerank finalists relatively. | Multimodal fusion with **per-video normalization**; the compact **event timeline** handed to the scoring LLM; quality-bar selection with no hard count; **relative head-to-head rerank** for the final order; label + reason recorded per clip. We do not copy its code or GPL assets. |
| ClipForge (`Orlando0309/clipforge`; also the `lowdevco/Clip-Forge` skill) | Shot-boundary prior + an LLM virality rubric fused with audio "buzz"; keep everything above a sensitivity threshold (~70 strict … ~40 generous), snap to sentence boundaries, suppress overlaps, and an "editor" pass stitches setup→payoff and drops dead air. Rubric: hook / emotional peak / opinion bomb / revelation / conflict / quotable / story-peak / practical value + a self-contained check. | A **sensitivity-driven quality bar**, not a fixed N; snapping cuts to speech edges; the hook/payoff self-contained check; explicit, explainable dimensions. We fuse transcript+audio+vision rather than transcript+audio only. |
| cutawan (`JeremySNR/cutawan`) | An LLM picks **self-contained hook→build→payoff micro-stories**, then a second AI pass reviews every ending and extends it to the beat that completes the thought. Editorial ranking moves repeated ideas down and treats scores as provisional. | The **micro-story unit** and the ending-completion pass (we approximate it by growing windows to whole sentences and requiring a payoff dimension ≥ band); de-duplicating by idea, not just overlap; labels + provisional reasons shown. |
| viral-clipper / shortsmith-style rubric prompts | Score hook strength, emotional peak, payoff clarity, standalone value; **kill criteria** reject weak hooks, mid-thought starts and context-free fragments; prefer loops (end feeds the hook) and 15–40 s; isolate the strongest 5–10 s as the hook. | Explicit **kill criteria** and scoring bands; the hook line returned verbatim; length preference; hook isolation (our cold open is the window's peak). |
| AI-Youtube-Shorts-Generator (`Anil-matcha/…`, MIT) | Classify content type/density first, chunk long videos with overlap, rank candidates on a virality framework (hook, emotional peak, opinion bomb, revelation, conflict, quotable, story peak, practical value) scored 0–100, dedupe >50 % overlap keeping the higher score, then render. | Content-type/density awareness in the prompt; **overlap suppression keeping the higher score**; a named virality framework; score+hook+reason emitted together. |

**Net design.** Transcribe candidate regions first (language auto-detected),
segment to sentences, grow self-contained hook-build-payoff windows of 14–60 s
snapped to speech edges, fuse audio/scene signals with a shortlist vision read,
score against a calibrated rubric in editable skill files, head-to-head rerank,
then keep everything above the quality bar with no arbitrary cap. The vision
model is one signal, never the primary picker.

## 2026-11-24 session — intelligence and distribution

| Choice | Reason | Licence |
| --- | --- | --- |
| Research source fetch is independent of the AI provider | A stored `YOUTUBE_API_KEY` was attached but never read because `gather_sources()` also required `LLM_PROVIDER != recorded`. Live sources now fetch whenever a source key exists; the sample feed is used only when no key exists or every live fetch fails. | — |
| `source_fallback` and `ai_fallback` are separate columns | They are different facts. A run can read ten live YouTube sources and still have no AI credit; the UI must not call that either "all live" or "all sample". | — |
| A local OpenAI-compatible model can prove the whole brain | `make setup-engine` + `LLM_BASE_URL=http://localhost:11434/v1` produced a real YouTube→idea run with no cloud credit (10 sources, 1 sourced idea, 37 s). | — |
| One platform registry in `shared/platforms.py`, copied into both images | Adding a target is a data change, never a code fork. The API validates from it; the worker reads `max_seconds` when growing windows and `caption_style` when rendering. | — |
| Platform is carried on project → pipeline run → clip | The user picks the target once; the engine adapts length and caption style, and the clip keeps the target for the calendar and export. | — |
| `PATCH /clips/{id}` re-renders assignment-less clips too | The automatic pipeline publishes clips with `assignment_id = NULL`; the old re-render query inner-joined assignments, so layout/caption edits on those clips silently did nothing. The editor now falls back to the clip's own recording window and cached transcript. | — |
| Cover art comes from RAWG and is backfilled, not drawn | `scripts/backfill_game_art.py` fills empty `art_url` from RAWG; games with no match stay empty and get a gradient monogram rather than a grey tile. | — |
| `/landing` reads owner slots from env | No dead buttons and no committed URLs: `NEXT_PUBLIC_DOWNLOAD_MAC`, `NEXT_PUBLIC_DOWNLOAD_WINDOWS`, `NEXT_PUBLIC_WEB_PORTAL`, `NEXT_PUBLIC_DEMO_CLIP`. | — |
| Setup is invited, never forced | The admin overview shows a dismissible wizard invitation when a check fails; basic use is never blocked. | — |



