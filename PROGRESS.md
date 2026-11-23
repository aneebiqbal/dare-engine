# Progress

## Automatic upload-to-Shorts pipeline

Status: **built and committed on branch `auto-pipeline`; proven end to end
through the real API on the real stack with the real MLX/VLM bridge. The
acceptance suite is running. Clip quality still needs the owner's gameplay.**

### What was built

- **Schema** (`0022_pipeline.sql`, `0023_pipeline_media.sql`): `pipeline_runs`
  (state, last completed stage, progress, plain-language action, ETA/remaining,
  model loaded, per-stage timings, measured rates, notes, memory readout) and
  `pipeline_candidates` (cheap score, vision score, final score, origin
  `ai|user`, selected, status, cut key, transcript, clip id). The run resumes
  from the last COMPLETED stage; each candidate resumes at its own status.
- **Cheap whole-video scan** (`worker/clip/scan.py`): FFmpeg only — per-second
  audio RMS, scene cuts, 1 fps frame stats, and silencedetect speech activity.
  No model ever sees the whole file. Produces a shortlist, merges user
  timestamps as high-priority candidates and never replaces the AI suggestions.
- **Vision pass** (`vision.score_windows`): loads the VLM once, samples two
  downscaled frames per shortlisted window (never the whole video), scores
  clippability + reason + striking frame, then unloads and verifies against the
  model inventory.
- **Cut**: seeks (`-ss` before `-i`), re-encodes only the short window, with a
  2 s pre-roll/post-roll; downscales sources above 1080p.
- **Transcribe**: MLX Whisper on Metal once per stage, only the cut clips,
  word timestamps cached to the SSD and the DB; unloads and verifies. Falls
  back to faster-whisper CPU and says so.
- **Render** (`engine.render_cut`): renders from the cached cut with the cached
  transcript — no re-transcribe, no re-cut of the source. Grammar beats, ASS
  word-synced captions clear of the platform UI zone, 1080×1920 H.264, thumbnail.
  Each Short is published as soon as it finishes.
- **Orchestration** (`worker/clip/pipeline.py`): sequential stages, converging
  ETA (measured rates replace the starting estimates after every stage), live
  action/progress/model, pause on a full disk or a missing source volume,
  resume from the last completed stage, cleanup of cuts and a live memory
  readout at the end.
- **One model at a time**: the `run_pipeline` job takes the same Postgres
  advisory lock as `run_project`, so a pipeline and a manual analysis can never
  load models together.
- **API** (`api/app/pipeline.py`): `POST /pipeline/upload` (one upload starts
  the run), `GET /pipeline`, `GET /pipeline/{id}` (run + candidates + clips),
  `POST /pipeline/{id}/timestamps`, `POST /pipeline/{id}/resume`. Admin-only;
  metadata only, media stays on the SSD.
- **UI** (`web/components/pipeline.tsx`, projects page): one upload control,
  per-stage bars with seconds, plain-language action, model loaded/idle, ETA and
  remaining, ranked candidates with reasons and thumbnails, finished Shorts as
  cards that appear one by one, optional timestamp entry, resume on a paused or
  failed run.
- **Output**: every run is self-contained under `projects/<run_id>/` on the SSD —
  the source, candidate thumbnails, transcripts, and the finished Shorts,
  captions and metadata. The same finals are served from `clips/<id>/` for the
  existing review/calendar pages. Nothing media-sized enters the database.
- Contract regenerated (**133 paths**). Unit tests **16 passed**; `make check`
  **2 passed**; web `tsc --noEmit` clean.

### Measured on this machine (2026-11-23)

A 45 s stand-in through the real API (`POST /pipeline/upload`), top_n=3, real
MLX Whisper bridge up, real Qwen2.5-VL-7B vision bridge up:

| Stage | Seconds |
| --- | --- |
| ingest | 11.61 |
| cheap scan | 16.36 |
| rank | 14.81 |
| vision (real VLM, 6 frames) | 91.02 |
| cut (3 clips) | 36.91 |
| transcribe (MLX Metal, 3 cuts) | 43.20 |
| render (3 Shorts) | 54.98 |
| **total** | **268.9** (~4.5 min) |

- Compute path recorded: `asr=mlx/metal encoder=libx264` (the worker container
  has no VideoToolbox; the host path would use it).
- MLX peak memory **3.95 GB**; host RAM 21.3 / 38.6 GB (55.1%) at the end;
  `ollama_running: []` — the vision model was unloaded and verified.
- Cheap scan alone on the 291.8 s trailer: **5.84 s** total (audio 0.2,
  speech 1.2, scene 3.2, frame stats 1.2), 18 candidates, **no model**.
- Vision cost is ~15 s per frame on this 6 GB VLM; the first finished Short
  lands after the vision pass, the cut, all transcripts and the first render.
- Sampling frames at **512 px** instead of full resolution measured **8.5 s vs
  12.7 s per frame** with the same clippability judgment.

A second real run on the 291.8 s publisher trailer (`fixtures/gameplay_4min.mp4`),
top_n=2, real VLM + MLX:

| Stage | Seconds |
| --- | --- |
| ingest | 13.59 |
| cheap scan | 30.65 |
| rank | 21.03 |
| vision (real VLM, 15 windows × 2 frames) | 193.51 |
| cut (2 clips) | 29.91 |
| transcribe (MLX Metal, 2 cuts) | 39.69 |
| render (2 Shorts) | 50.05 |
| **total** | **358.4** (~6.0 min) |

- The vision pass found striking moments (no fallback note); compute path
  `asr=mlx/metal encoder=libx264`; MLX peak **3.96 GB**; `ollama_running: []`
  at the end.
- First finished Short ≈ 5.7 min into the run (after scan, vision, cut, all
  transcripts and the first render).
- A first trailer run exposed a real quality bug: when the cold-open peak sat at
  the window edge, the grammar produced a **2.8 s** Short. `grammar.build_beats`
  now reserves a real payoff after the cold open; the re-run produced **7.9 s
  and 16.0 s** clips from the same candidates. Regression test added.

### The long-video lever (honest)

The cheap scan is CPU-bound FFmpeg. In this 4-core Colima VM it measured
**0.107 s of scan per second of video** (a 2 h upload ≈ 12.8 min); on the
14-core host the same scan measured **0.020 s/s** (2 h ≈ 2.4 min). The scan does
not get faster by adding a model — it needs CPU threads. `colima start --cpu 8`
(or running the worker natively on the Mac) is the fix on this machine. The
vision pass is capped at 15 windows × 2 frames regardless of length, so it stays
~3–4 min; the scan is the part that scales with duration.

Reproduce a long-video run on a generated 2 h file:

```sh
ffmpeg -f lavfi -i testsrc2=duration=7200:size=640x360:rate=15 \
       -f lavfi -i sine=frequency=440:duration=7200 \
       -c:v libx264 -preset veryfast -crf 30 -c:a aac -shortest /tmp/long2h.mp4
make pipeline-demo FILE=/tmp/long2h.mp4 TOP_N=10
```

### Honest latency note

The stages are sequential by design, so on a 2 h upload the cheap scan plus the
vision pass dominate before the first cut. Measured: the 45 s stand-in put the
first finished Short at ~3.9 min, the 4.9 min trailer at ~5.7 min. A 2 h run is
estimated at 10–15 min to the first Short **in this 4-core VM**, mostly the scan;
on the host CPU it is ~7–9 min. A one-frame-per-window mode
(`VISION_FRAMES_PER_WINDOW=1`) and a larger Colima CPU allocation are the two
levers if the owner needs the first Short under three minutes. This is unproven
on real 2 h footage.

### Verification

- Unit tests: **124 passed, 1 skipped**; the pipeline suite alone is 18,
  including stage sequencing, resume from the last completed stage, the
  no-model cheap scan, window-scoped vision with unload, user-timestamp
  merging, silent video, disk-full pause, high-res downscale and a real
  `render_cut` on a cached cut.
- `make check` (no mock + licence): **2 passed**. Web `tsc --noEmit`: clean.
- Pipeline acceptance through the real API: **4/4 passed** — upload → done with
  three published Shorts and all seven stage timings; the project shows the live
  run; timestamps add a user candidate while the AI candidates remain; a paused
  run resumes and finishes.
- `test_projects.py` **6/6**; `test_contract.py` **2/2**.
- Live UI proof: `docs/screens/pipeline-live.png` (stage bars, ETA, model state,
  a user-marked candidate next to AI ones).

### Real vs stand-in

- **Real:** ingest, cheap scan, ranking, real VLM scoring with reasons, cutting,
  MLX transcription, caption/render, publishing, resume, timestamps, the live
  UI, per-stage timings, memory unload verification.
- **Stand-in / sample:** the acceptance footage is the synthetic
  `standin_speech_45s.mp4` test pattern, so the VLM correctly reports "nothing
  striking"; the publisher trailer is the only real video. **No human has
  watched the output**, so clip quality is unproven.
- **Not measured on 2 h footage:** the owner's own recording. The 45 s and
  4.9 min runs prove the plumbing and the rates; a 2 h run needs the owner's
  file and is the only thing that proves the long-video budget.

### Blocked on the owner

1. The owner's own gameplay recording — the only thing that proves clip quality
   and the real 2 h timing budget.
2. Credit on the AI/research keys for live runs (not needed for the local
   MLX/Ollama path).
3. The SSD mount and the host/remote decisions.

## Redesign sprint — a workplace tool, not a stat dashboard

Status: **built, tested on the real stack, and screenshot-verified. The human
visual verdict is pending.**

### What changed

- **Design tokens** (`web/app/globals.css`, `tailwind.config.ts`): the "control
  room" theme. Light is the default (cool silver canvas, white surfaces,
  diffused ambient shadows); dark is a first-class alternative. The accent is a
  signal blue that means *running*; amber means *needs you*, green *done*, red
  *failed*. Geist Mono for numbers, stages and ids. One motion curve; a
  breathing live dot and a filling pipeline are the only moves.
- **Component kit** (`web/components/work.tsx`): `WorkHeader`, `LiveStrip`,
  `Pipeline`, `ProgressCard`, `StatusBadge`, `LiveDot`, `WorkQueue`,
  `ActivityFeed`, `Metric`, `WorkEmpty`, `FilterBar`, `DataTable`, `Section`,
  `Rail`. Every rebuilt page is built from these.
- **Backend**: `GET /admin/overview` (one batched read of jobs, research,
  projects, pool, keys, system, activity, best/worst results, clips today,
  users, invites, storage); `GET /admin/projects` (admin-only, all users);
  async research runs with real stages (`fetch → write → store`) via
  `POST /admin/games/{id}/research` + `GET /admin/research/{run_id}`
  (migration `0021_research_progress.sql`); pool filters (`q`, `source`,
  `min_score`) and `POST /admin/pool/bulk`.
- **Pages rebuilt on real data**: Overview (command center), Games + game
  profile (live research pipeline), Pool (filterable table, row expansion, bulk
  approve/reject/assign), Projects (full stage pipeline + queue position),
  Studio (live detection job stage, render stages, candidates), Clip review +
  Captions (render pipeline, sourced caption editor with re-render progress),
  Calendar (week-first with the cadence guardrail), Long-form (live build),
  Results (leading indicators + best/worst + sort), Models (live engine panel),
  Setup (grouped checks + integration keys), Users, Invites, Jobs, AI, Audit,
  Templates, Dashboard, Today, Clips, History, Settings, Mission editor, Export.
- **Screenshots**: `docs/screens/before/` (the old build) and
  `docs/screens/after/{mock,real}/` (the new build, phone/desktop × dark/light).

### Verification

- Unit **105 passed, 1 skipped**; `make check` **2 passed**.
- Contract regenerated (**127 paths**, including `/admin/overview`,
  `/admin/projects`, `/admin/research/{run_id}`, `/admin/pool/bulk`);
  `test_contract.py` **2 passed**.
- `test_redesign.py` **4 passed**; `test_games_research.py` **2 passed** — the
  latter drives a real async research run (fetch → write → store) and asserts
  the ideas land.
- `make budgets` — **PASS**: TBT 0 ms everywhere; LCP 28–2032 ms on the five
  main pages at phone and desktop (`docs/screens/budgets.json`). The range is
  Neon-bound: the managed compute answered ~10 ms/query when warm and
  ~240–600 ms/query during the run, and `/today` makes two to three queries.
  `/admin/overview` batches its five scalar counts into one round trip.
- a11y (axe-core, every page × phone/desktop × dark/light): see
  `docs/screens/a11y.json`. The first redesign build failed contrast (dark
  accent-on-soft 4.29, dark muted 2.79, light success 4.2); the tokens were
  darkened and re-measured to 0 serious/critical.

### Honest labels

- **Real work:** jobs, projects, clips, research runs, calendar, users,
  invites, models, keys, the studio pipeline.
- **Stand-in:** the AI provider is recorded unless a key is stored; research
  uses the sample feed unless source keys are stored; publishing is a manual
  marker.
- **Empty because it needs the owner:** clip quality (no owner gameplay
  fixture), live trends (source keys), real metrics (a YouTube collector).

### Owner verdict pending

The honest bar is a human looking at `docs/screens/after/` and calling the
layout a real workplace tool. Screenshots are saved; the verdict is not claimed.

## Autonomous sprint — projects, setup wizard, edge cases

Status: **projects and the first-run wizard are built, tested on the real
stack, and committed.**

### Projects (one stream = one project)

- Migration `0016_projects.sql`: `projects` — one per studio recording, or
  created by hand.
- The stage is **derived from real artifacts** on read, never stored:
  `planned → recording → imported → analyzing → clips_ready → reviewed → exported`.
- `api/app/projects.py`: list/create/get/attach/vision/queue/delete. Upload and
  SSD import start a project; a render links its stream back.
- Sequential analysis: `POST /projects/{id}/queue` enqueues a `run_project` job;
  the worker claims the **oldest queued** project under a Postgres advisory lock
  and holds the lane until its analysis drains, so two projects never load models
  at once.
- Web: `/admin/projects` (stage stepper, progress, candidates, clips, queue,
  vision toggle) plus a Projects panel on the admin overview and a nav entry.
- Tests: `tests/unit/test_projects.py` (the stage machine) and
  `tests/acceptance/test_projects.py`, which proves the stage follows real
  clips → review → export and that two projects run one after the other.

### Setup wizard (Part 1)

- Migration `0017_setup_steps.sql`: per-user step progress, so a returning user
  skips completed steps.
- `api/app/wizard.py`: four steps (SSD, OBS, models, cloud). `GET /admin/wizard`
  and `POST /admin/wizard/{step}`; a step is pending/done/failed and the next
  unlocks only when the previous is done.
- Web `/admin/wizard`: each **Verify** calls the real endpoint (SSD bridge, OBS
  WebSocket, model bridge, provider config) and only then records done. The
  models step embeds the real Models page. "You're ready" when all four are done.
- Tests: `tests/acceptance/test_wizard.py`.

### Verification

- Acceptance `test_projects.py` + `test_wizard.py` — **11 passed**.
- Unit `test_projects.py` — **9 passed**; `make check` — **2 passed**.

### In-window clip editor (Part 4)

- Migration `0018_caption_override.sql`: `clips.captions_override`.
- `GET /clips/{id}/captions` returns the caption events an editor should show —
  the stored override, or the cached transcript grouped the way the worker burns
  it (`api/app/caption_events.py`).
- `PATCH /clips/{id}` with `captions` validates and stores the override, then
  re-renders. The render reuses the cached transcript; **nothing is
  re-transcribed**.
- `worker/clip/engine.py` takes `caption_override` and burns those events
  instead of the transcript-derived ones.
- Web: a **Captions** card in clip review edits text, start and end per line,
  adds/removes lines and saves. Trim, layout, caption style and voice-over were
  already there.
- Caption grouping now breaks on a pause > 1 s, so a caption never spans silence
  (worker and API grouping match).
- Tests: `tests/unit/test_caption_editor.py` (6),
  `tests/acceptance/test_caption_editor.py` (3).

### Clean machine, visible process (Part 5)

- Migration `0019_engine_events.sql`: `engine_events`.
- `worker/worker_app/events.py` logs model loads/unloads, job start/done/failed and
  render cleanup. It is best-effort — a logging failure never breaks a job.
- The worker logs: whisper load/unload around detection, vision load/unload around
  the sampled pass, and render start/cleanup. The API exposes
  `GET /admin/engine-events`; the admin overview shows the recent activity.
- The Models page still shows the live memory readout (host RAM, Ollama VRAM, MLX
  peak), so the user can see the Mac return to idle.

## Ship sprint — cloud web, desktop app, vision suggestions

Status: **the split is built and documented; the cloud deploy and the desktop
capture need the owner's host and a human at a Mac.**

### Architecture

- `docs/architecture.md`: the cloud (web + API + managed Postgres) and the
  desktop (worker, models, capture, SSD) with a Mermaid diagram and the one API
  contract between them.

### Cloud web

- `docs/deploy-web.md`: managed Postgres, Caddy TLS, `docker compose up api web`,
  health check, backups, hardening.
- Rate limiting: per-IP sliding window, stricter on `/auth` and `/admin`
  (`api/app/ratelimit.py`, 8 unit tests).
- Error reporting: the browser posts to `/client-error`; an admin reads them on
  the overview (`api/app/errors.py`, migration 0014).
- Backups: `scripts/backup.sh` + `make backup` (pg_dump gzip).

### Desktop app

- `desktop/` — a Tauri v2 shell. Builds a **2.37 MB** `.dmg`
  (`make desktop`); the artifact mounts and verifies.
- Rust commands: `app_url`, `app_home`, `start_stack`, `capture_start`,
  `capture_stop`, `read_file_b64`, `recordings_dir`. ACL-managed
  (`build.rs` + `capabilities/default.json`).
- The web UI shows a **Desktop engine** card only inside the app: start the
  local stack, record the screen, import the recording into the studio.
- OBS remains the reliable capture default (Go Live); the bundled FFmpeg
  recorder is the no-OBS path.

### Vision suggestions

- `worker/clip/vision.py`: a bounded, sampled pass (one frame / 5 s, max 40).
  The VLM scores each window for JSON; suggestions carry a reason and the frame.
- The VLM unloads after the pass and the unload is verified against the model
  inventory. Off by default; a studio toggle turns it on.
- Migration 0015 adds `source`/`thumb_key`; the studio shows vision suggestions
  with a thumbnail and the pass time.
- Unit tests use a fake VLM (4 tests) + the bridge endpoint (2 tests). An
  acceptance test runs the real sampled pass end to end.

### Models & Setup

- A **Suggested engine** card shows transcription, writing and vision models
  with state, size, fit and one-click install, plus an approximate total.

### Real vision run (2026-11-23)

`qwen2.5vl:7b` (6.0 GB, Apache-2.0), on `fixtures/gameplay_4min.mp4`:

- **40 frames sampled** (one every 5 s, capped at 40) — not every frame.
- **447 s** for the 4-minute recording; **unloaded: true** (verified against the
  model inventory; Ollama unloads asynchronously, so the check polls).
- **5 ranked suggestions**, each with a reason and the frame it judged, e.g.
  - `94–106 s · 0.8` — "The character is rappelling down a building, showcasing a
    tense and action-packed moment in the game."
  - `9–21 s · 0.8` — "The dramatic silhouette of the character against the dark,
    ruined backdrop creates a visually striking moment."

This is a real VLM run on a real recording (the publisher trailer already in the
repo). It is **not** the owner's gameplay, so it proves the pass works, not clip
quality. Reproduce with `make vision-model` then `make vision-run FILE=...`.

### Verification

- Acceptance — **69 passed, 2 skipped** (run in bounded chunks; the only failure
  was a missing Playwright browser, installed).
- Unit — **63 passed, 1 skipped** fast, plus the detect/transcribe suites;
  vision **9/9**; `make check` **2 passed**; `make doctor` **14/14**.
- Desktop — `make desktop` builds a **2.37 MB** `.dmg` that mounts and verifies.
- Contract — regenerated (`make contract`); 111 paths.

## Final sprint — clean, fast, demo-ready

Status: **the product is demo-ready; the demo clip and live AI/research await the
owner.**

### Part 1 — cleanup

- Render scratch (42 MB) moved to `trash/` (listed in `trash/README.txt`);
  `.DS_Store` removed.
- The nav is trimmed to the core flow. `docs/pages.md` lists the core pages first
  and the supporting pages (styleguide, templates, jobs, AI usage, audit, public
  community) separately as reachable-by-URL but off the nav.

### Part 2 — navigation

- **Admin**: Overview, then Plan (Games, Pool), Create (Studio, Calendar,
  Long-form), Manage (Models, Setup status, Users, Invites). Current page
  highlighted; the page search filters the groups.
- **Gamer**: Play (Dashboard, Today, Go Live, Remote), Review (Clips, History,
  Results), Account (Settings). No admin controls.

### Part 3 — speed

- `/today`: the three sequential Neon queries are now two (dares + assignments in
  one join), and the generated card image is cached for 60 s (warm 3 ms). The
  shell already streams via Suspense.
- `/clips`: the thumbnail is served in place (no temp copy) with a cache header,
  and the grid thumbnails lazy-load.
- Numbers: `docs/screens/budgets.json` (`make budgets`).

### Part 5 — demo

- `docs/START_HERE.md`: run it, add a game, generate ideas, import from SSD, make
  clips, review/schedule, results, local models, and what still needs the owner.

### Final verification

- `make accept` — **67 passed, 2 skipped** (30.5 min).
- Unit — **60 passed, 1 skipped**; `make check` **2 passed**; `make doctor`
  **14/14**.
- a11y — **0 serious/critical on 30 pages** at phone + desktop.
- `make budgets` — PASS. Cold LCP: `/today` 1760/1828 ms, `/clips` 752/736 ms,
  `/remote` 24/36 ms, `/admin` 60/64 ms, `/` 864/820 ms; TBT 0 ms everywhere.
  Warm `/today` paints in **60 ms**.
- `make flow` — **11 steps**, every handoff a real route, screenshots in
  `docs/screens/flow/`.

## Polish sprint — one product, end to end

Status: **the journey walks end to end on real data; the owner's visual verdict
is pending.**

### Part 1 — the flow is one product

- A persistent **Up next** affordance on every step: Today, Go Live, Remote,
  Clips, Clip review, Studio, Calendar, Results, the games list and the game
  profile. Each reflects real state and leads to the next real screen;
  self-referential links were removed.
- `tests/screenshots/flow.py` (`make flow`) seeds a real game, sourced ideas and
  an assignment, then the admin runs the real studio (upload → find moments →
  generate), reviews with commentary, schedules, builds a long-form and records
  metrics; a creator walks Today → Go Live → Remote with real Start/Done taps.
  It asserts every step has a real next link and saves 11 screenshots to
  `docs/screens/flow/`.
- The studio reopens the latest session on load, so a session is already pointed
  at.

### Part 2 — signature moments

- One shared `DareCard` (hook, question, win condition, generated card image,
  sources) on Today, the dashboard and the pool/profile surfaces.
- The studio shows the real compute path, live system load, ranked candidates
  with scores and reasons, the finished clip and the next step.
- Results shows swipe-through, saves/shares per 1k and a data-driven summary;
  the recorded provider's canned numbers are never presented as real.

### Part 3 — half-built features finished

- Calendar: drag a clip onto a 7-day grid, with the cadence guardrail on the day
  cells; the queue and the manual-publish label are real.
- Long-form: optional intro/outro title cards burned by FFmpeg, matched to the
  clip format.
- Commentary: a real field in review, fed into the AI export prompt.
- Models: per-model “Fits this Mac”, real MLX download status, pull/unload/free.
- SSD: process-and-release deletes the inbox copy after a safe import.

### Part 4 — speed and docs

- `docs/performance.md` reconciled with `docs/screens/budgets.json`.
- Doc drift fixed: `worker/worker_app` paths, the contract path count (105) and
  the piper-tts licence.
- a11y: 0 serious/critical on 30 pages at phone and desktop.

### Owner verdict pending

The honest bar is a human looking at `docs/screens/flow/` and the page
screenshots. The clip-quality bar and the launch demo still need the owner's own
gameplay footage.

### Sprint verification

- `make accept` — **66 passed, 2 skipped**, then `test_contract` **2 passed**
  after regenerating the contract for the new routes (67 passed, 2 skipped).
- `make screens` / a11y — **0 serious/critical on 30 pages** at phone + desktop.
- Unit — **60 passed, 1 skipped**; `make check` **2 passed**; `make doctor`
  **14/14**.
- `make budgets` — LCP/TBT within budget on the five main pages; the numbers are
  in `docs/performance.md` and `docs/screens/budgets.json` (TBT 0 ms everywhere).
- `make flow` — **11 steps**, every handoff real, screenshots in
  `docs/screens/flow/`.

## Autonomous build session — model manager, memory discipline, content loop

Status: **P1 model manager, P3 memory discipline and P4 content loop are built
and committed; the full acceptance suite is running.**

### What was built this session

- **Fix: api/worker `app` package collision.** The worker package was renamed
  to `worker_app` (relative imports, Dockerfile, Makefile, tests), so the api
  and worker test suites can no longer shadow each other. Unit tests are
  hermetic (`tests/unit/conftest.py`: `MLX_WHISPER_URL=""`, `HF_HUB_OFFLINE=1`).
- **P1 — Models page (`/admin/models`).** `local/mlx_bridge.py` now exposes
  `/models`, pull with progress, unload, free-all and live host/Ollama/MLX
  memory. `api/app/models.py` proxies it; the page shows the provider, every
  Ollama model with size and loaded state, pull/unload/free controls and a live
  memory readout. Real values verified on this machine.
- **P3 — memory discipline.** `worker/clip/transcribe.py` gains `unload()`;
  detection and first-time renders free the ASR model after use. The MLX bridge
  serializes transcription, clears the MLX cache after each call, and a watchdog
  frees everything after `MLX_IDLE_MINUTES` (default 10).
- **P4 — content loop.**
  - `clips.commentary` (migration 0008): the added-value step in clip review,
    fed into the AI export prompt.
  - `/admin/calendar` (migration 0009): review-and-export queue, 2 Shorts/day
    cadence guardrail, TikTok/Instagram refused as approval-gated, publish is a
    manual marker marked `unproven: youtube-api`.
  - metrics gain `swiped`/`saves`/`shares` (migration 0010); `/results` shows
    swipe-through and saves/shares per 1k, and `missions.score` blends them
    (unit-tested in `tests/unit/test_results_score.py`).
  - `/admin/long-form` + `build_long_form` job (migration 0011): concatenates a
    session's finished Shorts into one video.
- **P5 — launch docs.** README rewritten (pitch, proof, demo slots), new
  `docs/licences.md`, new `docs/launch.md` with the git-history cleanup plan.

### Final verification

- `make accept` — **67 passed, 2 skipped** (31.6 min).
- `make web-accept` — Playwright page flows pass; axe-core **0 serious/critical**
  on 30 pages at phone and desktop (includes the new models, calendar and
  long-form pages).
- `make doctor` — **14/14**; `make check` — **2 passed**.
- Unit tests — **60 passed, 1 skipped**.
- Provider picker verified on the real API and in the worker: `asr=cpu` →
  `('cpu','int8')`, `asr=mlx` → `('mlx','metal')`.

### Real vs stand-in

- **Real:** the model inventory/controls/memory, the commentary field, the
  calendar queue and cadence rule, the leading indicators and ranking score,
  the long-form concat job, the memory unload/watchdog.
- **Stand-in / blocked:** YouTube API publishing (manual marker only), TikTok
  and Instagram (approval gated), the AI provider (recorded), research sources
  (sample feed), the real gameplay fixture.

### Blocked on the user

- The user's own gameplay recording with commentary — the clip-quality verdict.
- AI key credit and research source keys.
- **The copyrighted trailer `fixtures/gameplay_4min.mp4` is on `origin/main`.**
  `docs/launch.md` has the cleanup plan; a local `git rm` alone leaves it on the
  remote, so the owner must choose a fresh repo or an approved history purge.
- The GitHub token that was embedded in `origin` was removed from the remote URL;
  it still needs revoking on GitHub.

## Finish sprint — OBS, SSD, local MLX engine

Status: **Parts 1–3 built and proven on real devices; Part 0 still blocked.**

### Part 0 — security (BLOCKED, not done)

`.git/config`'s `origin` URL still embeds a live GitHub token
(`https://ghp_…@github.com/aneebiqbal/dare-engine.git`). **Rotate it and reset
the remote.** Nothing was pushed; all work is committed locally on
`research-brain`. Finish-line item 5 stays false until the remote is clean.

### Part 1 — OBS live view (done)

- `api/app/obs.py` over obs-websocket 5.x (`simpleobsws`, MIT): real connection,
  OBS version, stream/record state, program scene, mic mute.
- `GET /live/obs/snapshot` returns a real `GetSourceScreenshot` JPEG of the
  program scene, labelled on the page as a **periodic snapshot, not a live feed**.
- Go-Live checklist now has real OBS signals (connected, recording) plus the
  manual HDCP / mic / radio ticks; unreachable OBS shows how to enable it.
- **Proven on real OBS 33.0.1 / WebSocket 5.7.6:** `connected:true`, scene
  `Scene`, `Mic/Aux` unmuted, 640×360 JPEG snapshot (4307 bytes).
- Unit tests: status mapping, snapshot decoding, unreachable state.

### Part 2 — SSD flow (done)

- Host bridge `local/ssd_bridge.py` (stdlib) lists `/Volumes`, ffprobes each
  video (size, duration, resolution) and copies the chosen file into a shared
  inbox; it refuses paths outside the mount dir.
- `GET /studio/ssd` and `POST /studio/ssd/import`: import registers a local
  studio recording **and enqueues a real `detect_moments` job**. No cloud.
- Studio page: "Import from SSD" with drive/video list and clear no-drive /
  no-video / bridge-down states.
- **Proven on a real mounted DMG** (`/Volumes/TestSSD/gameplay.mp4`): listed
  (291.8 s, 1280×720, 33 MB), imported, `detect_queued:true`, job `queued`.

### Part 3 — local MLX clip engine (done, human verdict still blocked)

- **MLX Whisper on Metal** via a host bridge (`local/mlx_bridge.py`); the worker
  streams the file bytes (the container's storage is not on the host) and falls
  back to faster-whisper CPU when `MLX_WHISPER_URL` is empty. Compute path is
  stored and shown as `mlx / metal` with the GPU badge.
- **Measured:** 30.17 s to transcribe the 4.9-min fixture (593 words) on Metal.
- **Visual strikingness:** 1 fps 32×32 gray frame stats; dark (<8% luma) and
  blown-out (>95%) frames score 0 and are never the cold open. The trailer's top
  candidate (243–255 s, 6.91) carries the new `striking frame` reason.
- **Karaoke captions:** a `karaoke` style emits one ASS event per phrase with
  `{\k}` word timings (word-by-word highlight), added to the template list.
- Detection on the trailer with MLX returned 3 candidates, all carrying
  `striking frame`; the top (243–255 s, 6.91) also has commentary + marker +
  fast cuts + rising voice.
- **Rendered the 3 moments:** 14.5 s / 5.5 s / 16.5 s clips, all `ready`,
  `blur_fit`. 3 clips in parallel: **87.1 s wall** (≈29 s/clip). A warm karaoke
  re-render of one clip: **6.6 s** (transcript and window cached).
- Karaoke re-render stored `caption_style: karaoke`; the render calls
  `write_ass(caption_style=...)`, and the unit test proves the `{\k}` output.

### Per-clip verdict (the bar that is NOT met)

The only footage is a publisher trailer (`fixtures/gameplay_4min.mp4`, IGN
watermark), not the user's own gameplay with commentary. **No human has watched
the clips and recorded a verdict.** Per the Gate 0 rule, the clip-quality bar is
**unmet** until `fixtures/stream_10min.mp4` exists and a person watches the
output. The 3 trailer clips are in the studio (recording
`5cd6b8e9-70ef-4f7c-8f98-dbce9d1e4ec8`); watch them and record one line each.

### Re-prove after the source_ids change

- `tests/acceptance/test_games_research.py` + `test_contract.py` over HTTP:
  **4 passed.** The research path is proven over HTTP, not only by the unit test
  and the local-model run.

## Research-brain sprint — games + sourced daily ideas

Status: **built and green on the real stack.** The games grid, the game profile,
the daily research brain, sourced ideas, the approval gate and the gamer's Today
are wired end to end. The brain runs on the recorded provider + saved sample feed
and is flagged as a fallback; live source keys and AI credit are still missing.

### What was built

- **Games.** Migration `0006_games.sql` (games, `missions.game_id`,
  `mission_sources`, `research_runs`). `api/app/games.py`: admin grid, RAWG
  search/create (auto-builds genre/release/art), profile, enable/disable,
  on-demand research, gamer-facing list. Web: `/admin/games`,
  `/admin/games/[id]`, "Games" in the admin rail.
- **Research brain.** `api/app/research.py`: YouTube Data API + Reddit + gaming
  news RSS → one AI client → schema-validated ideas whose citations are checked
  against the fetched feed. An idea with no real source is dropped. Stored as
  candidates with `mission_sources`. A DB-gated daily loop runs it per enabled
  game; `RESEARCH_ENABLED` / `RESEARCH_HOUR` / `RESEARCH_TIMEZONE` in `.env`.
- **Card identity.** `GET /missions/{id}/card.svg` renders the idea's card as an
  SVG (hook, question, win condition, game, id) with no remote image.
- **Accuracy.** Sources are shown on the game profile, the pool and the dare
  editor. The admin approval gate is unchanged: nothing reaches a gamer
  unapproved.
- **Priority 1 audit.** `docs/pages.md` (one row per route), and the public
  leaderboard now shows a display name instead of a raw user id.
- **One env.** `.env.example` gains the research group; `docker-compose.yml`
  passes every new variable; `make doctor` is 14/14 with a research check that
  never fails and never prints a key.

### Ran and observed

- `make doctor` — **14/14**.
- New unit tests `tests/unit/test_research.py` — **7 passed**.
- `make check` (licence + no-mock) — **passed**.
- `tests/acceptance/test_games_research.py` + `test_contract.py` +
  `test_research.py` together — **11 passed**.
- `tests/acceptance/test_sprint2_interface.py` — **11 passed** (regression on
  the pool sources and the leaderboard display name).
- `tests/acceptance/test_games_research.py` — **2 passed** on the real stack:
  create game → research → 3 sourced candidates (2 youtube, 2 reddit, 1 news
  from the sample feed) → approve → assign → the creator's Today shows the
  assigned idea. One earlier run failed on a transient `psql`/Neon error in
  cleanup; it passed on rerun and on a combined rerun.
- `tests/acceptance/test_contract.py` — **2 passed** after regenerating
  `contracts/openapi.yaml` (89 paths).
- Manual smoke on the real stack: research returned
  `{"sources":{"youtube":2,"reddit":2,"news":1},"ideas":3,"fallback":true}`
  in 3.8 s; the card SVG served `image/svg+xml`.

### Real data vs stand-ins

- **Real:** the API, the database, the accounts, the approval/assign flow, the
  schema validation, the citation check, the SVG renderer.
- **Stand-in:** the research sources (saved sample feed) and the AI response
  (recorded provider). Marked `fallback: true`. Not proven on live YouTube /
  Reddit / news, and not proven with a live AI key.

### Blocked on the user

- `YOUTUBE_API_KEY`, the Reddit app, `RAWG_API_KEY` — live research and live game
  search.
- AI key credit — the live idea-writing call.
- The user's own gameplay recording with commentary — the clip-quality bar.
- `origin` exists but its URL embeds a GitHub token. Rotate it and use a
  credential helper; do not push until then.

### Next three tasks

1. **Priority 1c — OBS live view.** Connect the Go-Live page to obs-websocket,
   show real connection/recording state, and document the preview path.
2. **Priority 3a — SSD flow.** Detect an external drive, list its videos, load
   one into the local studio; nothing uploads.
3. **Priority 3b/3c — local models.** `make setup-engine` (MLX Whisper on Metal,
   MPS game-aware detection with a CPU fallback) and the word-synced caption
   engine; measure seconds-per-clip.

## Local models + cleanup sprint

Status: **local Chinese open-weight models are wired in and the machine is
stopped and cleaned.**

### Local models (the user's choice: local open-source, no cloud)

- **Ollama 0.40 is on the host** with `qwen3.8:27b-mlx` (Qwen3.5 27.8B, nvfp4,
  MLX, vision + tools + thinking), `qwen2.5-coder:14b`, `qwen2.5-coder-16k`
  and `kimi-k2.6:cloud`. Ollama serves the OpenAI chat format, so the existing
  `shared/llm.py` client works with **no code change** — only `.env`.
- `.env.example` documents the local block: `LLM_PROVIDER=openai`,
  `LLM_BASE_URL=http://localhost:11434/v1`, `LLM_API_KEY=ollama`,
  `LLM_MODEL=qwen3:8b`.
- `make setup-engine ENGINE_MODEL=...` pulls a model and prints the `.env`
  lines. `make research-local` runs the real `api/app/research.py` pipeline
  against Ollama (`local/research_local.py`) — no Docker, no key.
- `docs/local-models.md` records the wiring, the models and the limitation:
  **Metal is host-only**, so a Linux container cannot run MLX/Ollama; the
  container reaches a host model at `host.docker.internal:11434`. Transcription
  is still `faster-whisper` CPU in the container — the remaining P3 work.
- **Accuracy fix.** The brain now cites sources by short id (`s1`, `s2`, …), not
  by long URL. A 27B model copies ids reliably and mangles URLs; an unknown id
  is dropped. Same schema validated, same filter.
- **Ran:** `make research-local` → `qwen3.8:27b-mlx` produced **3 ideas, each
  citing real sample-feed sources, fallback=false**. The local path is proven
  end to end (prompt → schema → citation filter → stored-shape ideas).

### Cleanup (the user asked for it)

- Stack stopped (`make down`); both Android emulators killed; Colima stopped.
- Docker pruned: **20.19 GB reclaimed** (build cache 17.4 GB + images). Volumes
  kept (they hold local recordings).
- Repo artifacts removed: `m1-render-*` (except the two named review dirs),
  `ssd-test/`, `web/.next/`, `.pytest_cache/`. Repo 1.1 GB → 948 MB.
- Not touched (the user chose "nothing"): Docker Desktop data (63 GB), Android
  SDK/AVDs (44 GB), Xcode (24 GB), `~/Desktop/not active` (30 GB), caches.

## Completion sprint — one committed, proven application

Status: the accumulated work is committed and the full acceptance suite passes
on the managed Neon database with the mock off. Three things remain blocked on
the user.

### Branches (local only — no git remote)

- `sprint-6` — `1fa80dd` "Sprint 1 foundation, clip studio and Sprint 2
  interface": the accumulated uncommitted work (foundation, connected interface,
  studio, grammar, tests, docs, screenshots, the trailer stand-in).
- `completion` — `HEAD`: the tour replay test-id fix, the Part 3 full-flow
  acceptance test, `docs/BUILD_STATE.md`, and the `ssd-test/` ignore.

### Part 2 milestones

| Milestone | Built | Tested locally | Proven | Blocker |
| --- | --- | --- | --- | --- |
| M2 end-to-end UI path | yes | yes | yes (Neon, real accounts) | — |
| Studio path (Sprint 7) | yes | yes | yes (stand-in + trailer) | real gameplay fixture |
| M7 community | yes | yes | yes (real attempts) | — |
| Results and metrics | yes | yes | yes (manual entry) | YouTube API key (collector) |
| Admin portal | yes | yes | yes | — |
| Two portals connected, role boundary | yes | yes | yes | — |

### Part 3 — the one full-flow test

`tests/acceptance/test_full_flow.py` walks create admin → invite → creator
signs up → write + approve + assign → accept → upload + marks → render →
approve → export zip → metrics → results → leaderboard → role boundary, on the
managed database with the mock off. **Passed.** Real inputs: Neon, real
accounts, the real render engine. Stand-in: the 45 s synthetic recording (the
clip-quality verdict still needs the user's gameplay).

### Part 4 — finish line

1. Everything committed — **true** (two local commits; no remote).
2. Full-flow test passes on the managed DB — **true**.
3. Both portals real, connected, role boundary holds — **true**.
4. Acceptable speed — **true**: `/` 924/692 ms, `/today` 2808/2472 ms,
   `/remote` 2484/2448 ms, `/clips` 2276/2176 ms, `/admin` 776/664 ms
   (phone/desktop LCP, budget 5000 ms; TBT 0 ms); one Neon round trip ~670 ms.
5. `docs/BUILD_STATE.md` matches reality — **true**.

Acceptance: **67 tests, 65 passed, 2 skipped, 0 failed** (the two skips are the
voice-over tests, off unless the GPL add-on is installed). The suite was run in
two chunks (53 + 23, with overlap) because the harness loses long shells.
Unit **36 passed, 1 skipped**; `make check` **2 passed**; `make doctor` **13/13**.

### Blocked on the user

- The user's own gameplay recording with commentary — the only thing that makes
  the clip-quality verdict meetable.
- Credit on the AI key — the account returns 402/429, so every AI path runs on
  the recorded provider.
- A git remote — commits are local only; nothing to push or review.

## Sprint 2 — the complete, polished, connected interface

Status: **built and green on the managed Neon database.**

| Suite | Result |
| --- | --- |
| `tests/acceptance/test_sprint2_interface.py` | **11 passed** |
| `test_m2_missions.py` | **5 passed** |
| full acceptance (`make accept`, three chunks) | **64 passed, 2 skipped** |
| `test_web_pages.py` | **11 passed** |
| `make check` | **2 passed** |
| unit tests | **36 passed, 1 skipped** |
| axe-core, every creator and admin page, 390 px + 1280 px | **0 serious/critical** (`docs/screens/a11y.json`) |
| `make budgets`, five most-used pages | **pass** (`docs/screens/budgets.json`) |

The two acceptance skips are the voice-over tests, off unless the GPL add-on is
installed. `tests/screenshots/capture.py` wrote 116 screenshots (29 pages ×
phone/desktop × light/dark) into `docs/screens/`. The shared Neon database is
also used by another session; the numbers above are from runs made while that
session was idle.

### What changed

- **Design system.** `docs/design.md` now names the three signature moments
  (dare card, live job progress, leaderboard). `web/components/ui.tsx` adds
  `StatusDot`, gives `PageState` real loading/error/empty announcements and
  custom empty copy, gives `Table` a caption and `scope`, and gives `Dialog`
  focus management, a focus trap and `aria-labelledby`. The shell gains a
  skip link, an accessible mobile drawer and an account menu that closes on
  Escape and outside click. `/styleguide` now shows Select, Progress, Stat,
  StatusDot and Notice in both themes.
- **Creator pages.** Dashboard: real first-steps state, a ready-to-review list
  and a recent-results list. Today: swap (real `POST /assignments/{id}/swap`),
  assigned state, on-demand AI suggestions. Go Live: pre-stream checklist, a
  per-stream connection indicator, an error state. Remote: next dare, real
  status announcements. Clips: real thumbnails, labelled progress, the false
  "Resumable" claim removed. Clip review: a real `<video>` preview. Results:
  retention per dare type and a real metric-entry dialog. History: real
  search (`GET /history?q=`) and question column. Settings: real loading and
  error states, no fabricated defaults. Help: the guide renders as headings
  and lists, and the tour follows the role.
- **Admin pages.** Overview: loading/error states, live system health, token
  and latency totals, links into each section. Pool: labelled textarea,
  actionable merge, assign to a gamer (`POST /admin/pool/{id}/assign`),
  approve/reject error handling. Users: labelled role select. Invites:
  confirmable revoke, copy, error handling. Jobs: a real `stage` column
  (migration `0005_job_stage.sql`, worker sets it). AI usage: totals and the
  configured flag. Audit: actor name and formatted detail. Setup: loading and
  empty states.
- **Performance.** The API opened a fresh TLS connection to Neon for every
  request (~1.9 s), which dominated LCP. It now uses a `psycopg_pool`
  connection pool (`api/app/db.py`, `max_idle=60`, `max_lifetime=300`), which
  also survives the server closing an idle connection.
- **Real data.** `GET /clips/{id}/thumbnail` serves the real render poster;
  `/admin/pool/{id}/assign` and `/history?q=` added; `/streams/{id}/status`
  now checks this stream's path, not every relay path; the public leaderboard
  and creator pages read real missions and attempts instead of `m_0214` and a
  fabricated rank.
- **Tests.** `tests/acceptance/test_sprint2_interface.py` drives the full
  admin→gamer loop on real data (invite, write, approve, assign, accept,
  record, job, audit, role boundary, admin-only clip), plus error/loading/
  empty states, page flows at both widths, and the styleguide in both themes.
  `tests/screenshots/a11y.py` now covers every creator and admin page at both
  widths. `tests/screenshots/budgets.py` measures LCP and blocking time on the
  five most-used pages (`make budgets`).

### Pages: real data or still mocked

Every creator and admin page reads the real API. No page imports the mock layer;
`web/lib/mock.ts` is reachable only through `NEXT_PUBLIC_API_MOCK=1`, which
`make screens` uses for the screenshot harness, and `make check` fails if app
code imports it.

| Page | Data | Blocker |
| --- | --- | --- |
| `/` Dashboard | real | — |
| `/today` | real | — |
| `/missions/[id]` | real | — |
| `/live` | real | a real relay stream is needed to show “connected” |
| `/remote` | real | mid-stream marks need a real stream |
| `/clips`, `/clips/[id]`, `/export/[id]` | real | — |
| `/results` | real | the YouTube collector is out of sprint; manual entry works |
| `/history` | real | — |
| `/settings`, `/help` | real | — |
| `/admin` + all `/admin/*` | real | — |
| `/m/[slug]`, `/leaderboard`, `/creators/[id]` | real | — |
| AI panels (Today, pool, clip review, results, help) | recorded provider | live AI key has no credit (402/429) |

### Three worst screens, and the fix

1. **Go Live on a phone.** The stream address and key were two cards with the
   connection indicator at the bottom, and the indicator was global (any relay
   path lit it, not this stream). Fixed: the status is per-stream
   (`GET /streams/{id}/status` now matches this stream’s path), the key is
   masked until revealed, and a pre-stream checklist shows the real signals
   (address issued, relay reachable) plus two manual ticks, with a labelled
   progress bar.
2. **Admin overview.** Twelve undifferentiated stat tiles and no live health.
   Fixed: three grouped rows with links into each section, a live system tile
   (CPU, memory, GPU from `/studio/system`), token and average-latency totals,
   and a job-queue panel that shows each job’s real stage.
3. **Public creator page.** It showed a fabricated “Rank #12”. Fixed: it reads
   the real `/creators/{id}` attempts and shows the dare question and result;
   the leaderboard no longer hardcodes `m_0214` either. The clip-review preview
   was a gradient placeholder; it now plays the real rendered Short
   (`<video>`) with the thumbnail as the fallback.

### Needs human

- A live AI key with credit. The AI paths run on the recorded provider; every
  AI panel shows its fallback notice.
- The real gameplay fixture with commentary (`fixtures/stream_10min.mp4`).
- A Git remote, so the review rule can be satisfied.
- A person to look at the final screenshots and record a verdict. The
  screenshots in `docs/screens/` were captured with `NEXT_PUBLIC_API_MOCK=1` so
  every page shows a filled state; the app itself never uses the mock layer
  (`make check` fails if it does).

## Sprint 7 — automatic moments and a clip grammar

Status: built, tested and hardened. **The quality bar is unmet**: the only
footage available is a publisher's trailer (`fixtures/gameplay_4min.mp4`,
4.9 min, IGN watermark) and a personal trip video, not the user's own gameplay
with commentary. Per Gate 0 a trailer cannot validate gameplay clipping, so the
per-clip verdict is missing.

- **Part A — detector.** `worker/clip/detect.py` scores the whole file once
  (transcript word density, configurable marker phrases, per-second RMS,
  scene-cut density, silence-then-burst), ranks windows, merges overlaps and
  centres each on its peak. It reports the compute path: CUDA Whisper when a
  GPU is present, else CPU int8. Tests: `tests/unit/test_detect.py`.
- **Part B — grammar.** `worker/clip/grammar.py` + `worker/clip/templates.json`
  (5 visual templates, 3 caption styles, added without code). The cold open is
  the payoff's peak and plays first; the hook text sits over it; an optional
  tight context beat is a flash-back; the payoff is the longest beat. Captions
  are mapped onto disjoint beat ranges, so word sync stays monotonic. Tests:
  `tests/unit/test_grammar.py`.
- **Part C — studio.** `/admin/studio` (`api/app/studio.py`, a `detect_moments`
  worker job, `web/components/studio.tsx`): upload, Find moments, ranked
  candidates with score and reason, play/accept/trim/reject, Generate, inline
  preview, swap template/captions. The compute path is stored before the
  expensive pass so the panel shows it live, with real CPU/memory/GPU load.
- **Part D — local and clean.** No cloud render, no upload of source or clips
  (`docs/decisions.md`). Upload/playback/detect/render temp directories are
  removed after use; the retention sweep covers
  `recordings/<user_id>/studio-…`.
- **Part E — trailer run (this machine).** Detector on the 4.9-min trailer:
  **CPU int8 / libx264, no GPU** (CUDA absent; MPS exists but the spec asks for
  CUDA); detection **26 s** warm / 39 s cold. Top picks: 240–252 s (6.87,
  commentary + marker phrase + fast cuts + rising voice), 131–143 s (4.28),
  256–268 s (3.53). Rendered the top 3 with the new grammar: 18.5 s / 6.5 s /
  13.5 s, **12.7–26.1 s per clip**. Frames inspected: each opens on the
  word-dense peak (cold open), then the context flash-back, then the payoff;
  captions are word-synced and the hook text sits over the cold open. On this
  trailer the peaks are dark/blown-out cinematic frames — the detector has no
  visual-strikingness signal, so the cold open is not always the most striking
  frame. **No human verdict**: the trailer is not the user's gameplay.

**Fixed this session.** The cold open now plays first (the old grammar opened
3 of 5 templates on the slow context beat); the reported Whisper path is honest
(transcription used the static CPU setting even when a GPU was present); the
compute path shows live during detection; `vad_filter` is off because it dropped
real dialogue from short windows and the spoiler guard then discarded the
detector's #1 moment (`tests/unit/test_transcribe.py`); the web shell's
account-menu handler had a parenthesis bug that broke the web build; and
`contracts/openapi.yaml` was regenerated (9 implemented routes were missing).

**Verification.** Unit **36 passed, 1 skipped**; `make check` **2 passed**;
`make doctor` **13/13**; `test_contract` **2 passed** after regenerating the
contract. The studio acceptance + Playwright suite (**4 passed**: upload, detect,
generate, and the screen driving a recording to a finished clip) passes when the
stack is not being rebuilt under it. A full `make accept` pass is **62 passed,
2 failed, 2 skipped**; the two failures are the M2 `/today` pick read (the Neon
pooler intermittently serves a stale read right after the write, so the approved
mission is missing) and the pre-existing keyboard-tour test, neither in the
studio path. The render path is proven by the local run above and by the four
real-gameplay clips in `~/Desktop/clipdesk-test-clips/`.

### Needs human

- The user's own gameplay recording with commentary. Until it exists, the
  sprint's one hard measure (a human calls the clips good) cannot be met.

## Gate 0 — human supplies (checked at the start of this session)

| Item | Status |
| --- | --- |
| `fixtures/stream_10min.mp4` (real gameplay + commentary) | **PARTIAL** — `fixtures/gameplay_4min.mp4`, 4.9 min, 33 MB, real GTA V gameplay (a trailer; IGN watermark, not the owner's own stream) |
| Managed database URL (Neon or Aiven) | **CONNECTED** — Neon project `clipdesk` (`flat-bar-18096907`, `aws-us-east-2`, PG16); pooled + direct connection strings in `.env` (gitignored) |
| AI provider key (`LLM_API_KEY`) | **MISSING** (`LLM_PROVIDER=recorded` used) |
| Git remote on the organisation's Git host | **MISSING** (`git remote -v` empty) |
| Google OAuth client + test YouTube channel | **MISSING** (not in Sprint 6) |
| YouTube Data API key | **MISSING** (not in Sprint 6) |
| Payment provider test-mode keys | **MISSING** (not in Sprint 6) |

**Accepted on stand-in data only:** M1. Because the real fixture is missing, M1,
M3 and M4 are **not accepted** and will not be until `fixtures/stream_10min.mp4`
exists and the run is made.

## Sprint 6 — the complete working application

Status: built against a local Postgres container and the recorded AI provider.
Nothing is reported as proven on a managed database or with live AI: no managed
URL and no key exist.

- `make accept` — **44 passed** (0 failed), including the real Piper voice-over
  run and the transcript-cache trim re-render.
- `make web-accept` — **11 passed**; axe-core **0 serious/critical** on eight
  pages at phone and desktop.
- Migrations on an empty database — **26 tables**, no errors.
- `make doctor` — 11/13 (the two failures are the missing AI key and model).
- `make create-admin` — prompts for email and password, creates a real admin,
  signs in. Tested.
- Unit tests — 17 passed, 1 skipped.
- Committed on branch `sprint-6` (no git remote, so no pull request yet).

### Parts A–G

| Part | Built | Tested locally | Proven on managed DB | Proven with live AI |
| --- | --- | --- | --- | --- |
| A accounts and roles | yes | yes (10 tests) | no | n/a |
| B backend and API | yes | yes (`make accept`, empty-DB migrations) | no | n/a |
| C AI on every page | yes | yes (recorded provider) | no | no |
| D clipping and voice-over | yes | yes on the stand-in, with the real voice model | no | n/a |
| E interface redesign | yes | yes (11 web tests + axe) | no | n/a |
| F first-run guide | yes | yes (keyboard-only tour test) | no | n/a |
| G setup and keys | yes | yes (`make doctor`, Setup page) | no | no |

### Needs human

- An AI provider key, base URL and model.
- `fixtures/stream_10min.mp4`, the real gameplay recording with commentary.
- A Git remote, so the review rule can be satisfied.

### What runs now

- Email/password accounts, Argon2id, server sessions, CSRF, invite-only sign-up,
  admin role gating, lockout, admin-issued reset links, sign out everywhere.
- Migrations on an empty database; the job queue retries with backoff and keeps
  its error; an audit log of admin actions.
- One OpenAI-compatible AI client with JSON schema validation, one retry and a
  visible fallback; tokens and latency logged per call.
- Chunked resumable upload, render stages, trim re-render with the transcript
  cached, layout/caption picker, local Piper voice-over with ducking, export zip.
- Full-width app shell, creator and admin dashboards, all creator and admin
  pages, tours driven by `web/data/tours.json`.
- `make doctor`, `docs/SETUP_KEYS.md`, `.env.example`, admin Setup status.

### Design round 1 — five weakest screens, and the fix

1. **Admin overview** showed the creator hint ("Your day…") because the `/`
   hint prefix matched every path. Fixed: `/` matches exactly, other prefixes
   match by `startsWith`.
2. **Sidebar** used text glyphs (▦ ◎ ◉). Replaced with 1.5 px stroke line icons
   in `web/components/icons.tsx`.
3. **Admin overview** was two rows of stats and a lot of empty space. Added a
   recent-jobs panel and a recent-AI-calls panel.
4. **Public pages** still used the Sprint 3 narrow `max-w-5xl` column. Widened
   to the same `1600px` canvas as the app shell.
5. **Progress bars** had no accessible name (axe serious). Added `aria-label`;
   `make web-accept` now reports 0 serious/critical on eight pages at phone and
   desktop.

Screenshots for human review: `docs/screens/` (29 pages × phone/desktop ×
light/dark). Rounds 2 and 3 are not done.

### Not done / unproven

- The real fixture run (Part D acceptance is not met).
- A live AI call and a managed-database run (Parts B, C, G).
- Publishing to YouTube/TikTok/Instagram (out of sprint, `POST /clips/{id}/post`
  still flips state and is marked unproven).
- Google sign-in, payments, the question miner (kept off by flags).

## Sprint 1 — make it real and fix the foundation

Gate 0: managed Postgres **connected** (Neon project `clipdesk`,
`flat-bar-18096907`, `aws-us-east-2`, PG16; pooled + direct in `.env`). Still
missing: the real gameplay fixture, a live AI key, a Git remote.

| Item | Built | Tested locally | Proven on real inputs |
| --- | --- | --- | --- |
| M1 one real clip | yes | three Shorts rendered from the real fixture; ffprobe 1080×1920, 9.5/16.5/16.5 s, AAC, captions | **technical yes; human verdict pending** |
| M2 real end-to-end UI path | blocked | — | **blocked**: another session keeps rebuilding/restarting the stack (concurrent uncommitted "studio" work); the API/web containers change under the test |
| M3 managed database | yes | `make accept` / `make doctor` | **yes** (Neon, both connections pass) |
| M4 live AI | client shared | stub HTTP test | **no** — key present, account has no balance/quota (402/429) |
| F1 worker uses the one AI client | yes | unit tests (client, fallback, no Gemini) | partial (live call needs credit) |
| F2 retention and cleanup | yes | acceptance tests | n/a |
| F3 security gaps | yes | acceptance tests | n/a |
| F4 GPL voice engine | yes | licence check + optional add-on; voice tests pass when enabled | n/a |
| F5 dead and misleading code | yes | unit tests + README | n/a |

Sprint 1 acceptance on the managed Neon database: **51 passed, 0 failed**
(run in chunks because the harness loses long shells). `make check` 2 passed;
unit tests 31 passed, 1 skipped; `make web-accept` 11 passed + axe clean.

Needs human: **a verdict on the three real Shorts** (watch
`m1-render-real/clip{1,2,3}/short.mp4` and record one line each), a longer
owner-recorded gameplay fixture if the trailer is not acceptable, **credit on
the AI account** (the key works but returns 402/429), a Git remote, and
**serialization**: another session is editing `api/app/studio.py`,
`worker/clip/detect.py`, `worker/clip/grammar.py`, `web/components/studio.tsx`
and rebuilding the stack in the same working tree.

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
