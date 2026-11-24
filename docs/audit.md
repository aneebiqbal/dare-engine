# Audit — the real state before this work

Date: 2026-11-24. Branch: `ultra-ui-redesign` (work branch; `main` untouched).
Method: read `PROGRESS.md`, `docs/architecture.md`, `docs/pages.md`,
`docs/BUILD_STATE.md`, `docs/redesign-plan.md`, `docs/design.md`,
`docs/decisions.md`; read the API/worker/web source; queried the live Neon
database; ran the unit suite; inspected the screenshot sets.

The honest headline: **this is not a rough boilerplate.** A previous session
built the whole product and a first redesign. The user's brief describes an
earlier build. The remaining gap is not "flat tiles" — it is three concrete
missing features, a sparse showcase page, a missing distribution surface, and
a research brain that cannot read its own YouTube key.

---

## 1. What actually exists (verified)

### Services

| Piece | Where | State |
| --- | --- | --- |
| Web app | `web/` Next.js 15 + Tailwind + Geist | 29 routes, both roles, light/dark, phone/desktop |
| API | `api/app/` FastAPI, 26 migrations | accounts, sessions, games, research, missions, studio, projects, pipeline, calendar, models, keys, audit |
| Worker | `worker/` FastAPI + FFmpeg | job queue, clip engine, MLX bridge client |
| Local bridges | `local/mlx_bridge.py`, `local/ssd_bridge.py` | Metal Whisper, SSD copy |
| Desktop shell | `desktop/` Tauri | builds a `.dmg`; Rust commands compile |
| Contract | `contracts/openapi.yaml` | regenerated from routes; contract test enforces both directions |

### The clip engine (the hard part) is real

`worker/clip/pipeline.py` (1137 lines) runs nine stages:
`ingest → scan → regions → detect → signals → score → cut → render → done`.
It has converging ETAs, per-stage checkpointing, resume, a single-project lane
lease, one-model-at-a-time memory discipline, transcript-first rubric scoring
with head-to-head rerank, vision as a secondary signal, and a spoiler guard.
Measured on a real 4.9 min trailer and the owner's real 2 h 21 m GTA stream
(10 Shorts, 38.6 min) — see `PROGRESS.md`.

### The UI is already a "control room"

`web/components/work.tsx` is a 14-component kit (`WorkHeader`, `LiveStrip`,
`Pipeline`, `ProgressCard`, `StatusBadge`, `LiveDot`, `WorkQueue`,
`ActivityFeed`, `FilterBar`, `DataTable`, `Metric`, `Section`, `Rail`,
`WorkEmpty`). Every rebuilt page uses it. The old equal tile grid is gone.
Motion is one curve, three moves, `prefers-reduced-motion` respected.

### Verification assets

- Unit suite: 134 collected, 119 pass locally without FFmpeg; the 15 failures
  are all `FileNotFoundError: ffmpeg` plus one SSD env-key test — environmental,
  not logic. `test_encoder.py` also needs FFmpeg at collection time.
- Acceptance suite: ~30 files (needs Docker, unavailable on this machine).
- Screenshots: **568 PNGs** — `docs/screens/before/` (128, pre-redesign),
  `after/real/`, `after/mock/`; phone + desktop, dark + light.
- `make budgets`, `make flow`, Playwright + axe all exist.

---

## 2. What is weak (ranked)

### W1 — The research brain cannot read its own YouTube key (real bug)

`api/app/research.py::gather_sources()`:

```python
if settings.llm_provider == "recorded" or not live_keys:
    return sample_feed(), True
```

`.env` ships `YOUTUBE_API_KEY=…` and the key **works** (proved: HTTP 200 from
`youtube/v3/search`). But the source fetch is gated on the *AI provider* being
live. With the default `LLM_PROVIDER=recorded`, the key is never read and the
brain always serves the saved "car chase" sample feed. Source fetching and idea
writing are one flag, so they cannot be proved independently.

Consequence: the owner sees sample ideas and reasonably concludes the feature
is broken.

### W2 — No platform targeting anywhere

Only the calendar has a `platform` column (`youtube|tiktok|instagram`) and it is
a scheduling label. The engine is hard-coded to 9:16 / 1080×1920, one caption
vocabulary, no per-platform length or hook defaults. Adding a platform means
editing Python. Requirement #3 is unmet.

### W3 — Games is not a showcase

Live DB: **3 games, 1 with cover art.** `games.tsx` renders `art_url` only as a
20×56 px thumb beside the title. Cards show candidate counts but not a live
research state panel. RAWG key is present and works; the data was never
backfilled, and the layout wastes the best asset (real cover art).

### W4 — No distribution surface

No landing/download route exists (`web/app` has no `landing`/`download`).
`docs/desktop-app.md` says the Windows path is "documented, not built or
tested". No installer artifacts are committed. Requirement #6 is half-met
(mac `.dmg` documented + built previously; Windows and landing absent).

### W5 — Setup is reachable but never invited

`/admin/wizard` and `/admin/setup` are nav links. Nothing prompts a new user to
run them. The requirement is "optional and prompted", so this needs one
dismissible invitation, not a gate.

### W6 — Progress is good on the engine pages, thinner elsewhere

Projects/studio/clip-review have real stage + percentage polling. The games
research run polls, but the admin overview's live strip depends on
`/admin/overview`; pool/calendar/users are static tables (fine). The known hole
is the silent 20-minute hang: the pipeline has an ETA and stage text, but the
*upload* endpoint returns after storing the file, and the web upload button only
says "uploading…" until the response lands — a large file on a slow disk can
look frozen. Worth closing.

### W7 — Visual verdict is genuinely pending

568 screenshots exist, but no human has judged them. Clip quality is unproven on
the owner's footage (BUILD_STATE blocker #1).

### W8 — Housekeeping

- A GitHub personal access token was embedded in the `origin` remote URL.
  Removed from local git config this session; **the owner must revoke it**.
- Local `ffmpeg`/`ffprobe` absent, so 15 unit tests cannot run here.
- `docs/redesign-plan.md` was written *before* the build it describes; it needs
  a current-state addendum so the next reader is not misled.

---

## 3. Real vs stub (what not to overclaim)

| Real now | Stub / stand-in | Blocked on |
| --- | --- | --- |
| YouTube Data API key accepts requests | Ideas still generated by the recorded provider | AI key credit |
| RAWG search + art fetch | 2 of 3 games have no art | one backfill script |
| Full-video analysis pipeline | Clip virality verdict | owner's footage |
| Research run stage/progress | Live AI research writing | AI credit |
| Mac `.dmg` build | Windows installer | a Windows machine / signing |
| Web deploy recipe | Actual VPS + domain | owner |
| All 29 pages | Live YouTube/TikTok posting | platform approval |

---

## 4. The plan this audit implies

1. **Phase 2a** — split source-fetch from idea-writing; read the YouTube key;
   prove a real YouTube-fed run and record it. (W1)
2. **Phase 2b** — one data-driven platform registry shared by API and worker;
   carry `platform` through project → pipeline → render; clamp length and pick
   caption defaults per platform. (W2)
3. **Phase 3** — rebuild the games grid as pro cover-art cards with a live
   research panel; backfill RAWG art; add one dismissible setup invitation.
   (W3, W5)
4. **Phase 4** — public landing/download page with marked slots; Windows
   installer documented and scripted as far as a Mac allows. (W4)
5. **Phase 5** — unit + build green, screenshots refreshed, docs reconciled,
   verdicts labelled. (W6, W7)

Nothing here needs a new dependency. The stack is already right.
