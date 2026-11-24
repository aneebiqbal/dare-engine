# Redesign plan — Clipdesk as a workplace tool

Status: **Phase 1 (design) written; Phase 2 (build) and Phase 3 (QA) carried out
on top of it. The human visual verdict is pending.** See `PROGRESS.md` for the
build log and `docs/screens/README.md` for the before/after sets.

> **2026-11-24 addendum.** This plan was written before its build and still
> describes the intended design accurately, but it is not a picture of the
> current tree. Read `docs/audit.md` first for the real state and the gap list.
> Since this addendum the plan has three new requirements that postdate it:
> platform targeting (YouTube Shorts / Reels / TikTok drives length, aspect and
> caption style), a cover-art games showcase, and a public download landing
> page. Those are tracked in `docs/audit.md` §4 and `docs/decisions.md`.

The current pages render numbers in tiles. They answer "how many?" and never
"what is happening?". This plan turns every page into a surface that shows real
work: a research run fetching sources, a project advancing a stage, a clip
rendering through its stages, a queue that moves.

---

## 1. Theme decision

### Concept

**"Control room."** Not a marketing page, not a SaaS dashboard. A quiet,
dense, legible surface where the accent colour means *live* and every other
colour means a state. The layout is a pipeline: the left rail says where you
are, the top strip says what is running right now, the main column is the work,
and the right rail is what needs you.

Layout archetype: **asymmetrical bento with a persistent pipeline rail** — a
wide main column (the work surface) and a 320 px right rail (live status, needs
you, activity) on desktop, collapsing to one column under 1024 px. The old
`md:2 / xl:3 / 2xl:4` equal tile grid is gone.

### Colour

Light is the default working theme; dark is a first-class alternative. Neither
is pure black.

| Token | Light | Dark | Meaning |
| --- | --- | --- | --- |
| `--bg` | `#F3F4F6` (cool silver) | `#0A0C0F` | canvas |
| `--surface` | `#FFFFFF` | `#12151A` | card |
| `--surface-2` | `#EEF0F3` | `#1A1F26` | inset / secondary |
| `--surface-3` | `#E4E7EB` | `#232932` | raised control |
| `--border` | `ink 8%` | `white 10%` | hairline |
| `--text` | `#14181D` | `#E8ECF1` | ink |
| `--muted` | `ink 58%` | `ink 58%` | secondary |
| `--accent` | `#2F6BFF` (signal blue) | `#5B8CFF` | **running / live** |
| `--accent-2` | `#7C6CFF` | `#8B7CFF` | brand gradient end |
| `--needs` | `#B45309` | `#F59E0B` | **needs you** |
| `--success` | `#047857` | `#34D399` | **done** |
| `--danger` | `#B91C1C` | `#F87171` | **failed** |
| `--signature` | `#4F46E5` | `#C8FF3D` | dare card / brand only |

Status is a closed vocabulary: `running` (blue), `needs-you` (amber), `done`
(green), `failed` (red), `idle` (slate). A number is never coloured for
decoration; colour always carries one of those five meanings.

Depth: light cards sit on the silver canvas with a **diffused ambient shadow**
(`0 1px 2px rgb(16 24 40 / 0.04), 0 12px 32px -12px rgb(16 24 40 / 0.12)`) and
a hairline ring. Dark cards use a lighter surface plus a 1 px top highlight
(`inset 0 1px 0 rgb(255 255 255 / 0.04)`) instead of a glow. No more
flat-black tiles with a single border.

### Type

Geist Sans for UI, Geist Mono for numbers, timings, ids and stages (a tool
shows values in mono). Scale:

| Token | Size / line-height | Use |
| --- | --- | --- |
| `--step-display` | 3.5rem / 1.02 | the one live timer / hero number |
| `--step-h1` | 2.25rem / 1.1 | page title |
| `--step-h2` | 1.125rem / 1.35 | section / card title |
| `--step-body` | 0.9375rem / 1.55 | body |
| `--step-label` | 0.6875rem / 1.4 | eyebrows, badges (uppercase, +0.18em) |
| `--step-mono` | 0.8125rem / 1.4 | numbers, stages, timestamps |

### Spacing and radius

4-point scale: 1 2 3 4 6 8 12 16 24 32. Section rhythm is `24px` between major
regions (a tool is denser than a landing page; the old `py-24` marketing rule
becomes `gap-6` between sections and `p-5` inside a card). Cards keep the
double-bezel (outer shell + inner core). Radius scale: `0.75rem` controls,
`1.25rem` inner core, `2rem` outer shell, pills for buttons and badges.

### Motion language

One curve, `cubic-bezier(0.22, 1, 0.36, 1)`. Three moves only:

1. **Progress** — a pipeline connector or bar fills (`transform: scaleX` on a
   track, or `width` on a thin bar). This is the signature motion.
2. **Live** — the running dot breathes (opacity 1 → 0.35 → 1, 1.6 s loop) and
   only while something is actually running.
3. **Arrive** — a finished item settles (`translateY(8px) + opacity` → none,
   420 ms) when a job completes or a clip lands.

Nothing else animates. No hover lifts on tiles, no animated numbers, no
scroll-reveal on every card. `prefers-reduced-motion: reduce` kills all of it.

---

## 2. Component kit

One file, `web/components/work.tsx`, imported by every rebuilt page. Built on
`ui.tsx` primitives (Button, Input, Badge, Table, PageState) so nothing is
duplicated.

| Component | Job | Props |
| --- | --- | --- |
| `WorkHeader` | Page title, live status chip, primary actions | `eyebrow, title, status?, actions?` |
| `LiveStrip` | The global "what is running" bar, from `/admin/overview` | `overview` |
| `Pipeline` | Ordered stages, current stage highlighted, connector fill | `steps, current, done?` |
| `ProgressCard` | One unit of work: title, status, bar, stage, elapsed, action | `title, status, progress, stage, meta?, action?` |
| `StatusBadge` | Dot + label, one of the five states | `status, label?` |
| `LiveDot` | Pulsing dot, `aria-label` | `tone, label` |
| `WorkQueue` | A list of jobs/runs/projects with state and a per-row action | `items` |
| `ActivityFeed` | Chronological engine/job events | `items` |
| `FilterBar` | Search, filters, selection count, bulk action | `filters, selected, actions` |
| `DataTable` | Sortable, selectable table used by Pool/Jobs/Users/Results | `columns, rows, selected, onSort` |
| `Metric` | Inline number + label + delta (never a floating tile) | `label, value, delta?` |
| `Section` | Titled region with an optional action and a live count | `title, count?, action?, children` |
| `Rail` | The 320 px right column | `children` |
| `WorkEmpty` | Empty state with the one action that starts work | `title, body, action` |

Every page is `WorkHeader` → `LiveStrip` (admin only) → main column + `Rail`.
Every async region renders all four states through `PageState`.

---

## 3. Per-page redesign

### Admin Overview — the command center

- **Job:** see what is running and what needs a decision, in one screen.
- **Primary action:** open the thing that needs you.
- **Work happening:** the `LiveStrip` (running jobs with stage, active research
  runs, the project currently analyzing, Mac memory, source-key health, today's
  clips), a **Needs you** rail (ideas awaiting approval, clips awaiting review,
  failed jobs, unreachable keys), and a **Projects pipeline** strip.
- **Key actions:** retry a failed job, approve the top idea, open the analyzing
  project, fix a key.
- **Before/after:** before = 12 undifferentiated `Stat` tiles and three flat
  lists. After = one live strip, one needs-you rail, one pipeline strip, one
  activity feed. Every number is a link to the page that acts on it.

### Games / Research — watch the brain work

- **Job:** keep the game list healthy and run research on a game.
- **Primary action:** run research and watch it.
- **Work happening:** a game card shows the last run, idea count and a live
  research panel. `Research now` starts a real run and the page polls it: a
  `Pipeline` of **fetch sources → write ideas → store**, with the source counts
  filling in as they arrive and the produced ideas appearing under it with
  their virality score. The game profile's *Research runs* tab becomes a run
  history with a live progress row, not a static table.
- **Key actions:** add/enable/disable, research now, open profile.
- **Before/after:** before = a button that blocked until the run finished and
  then printed one sentence. After = the run is visible as it moves, and its
  output is on the same screen.
- **Backend:** `research_runs` gains `stage`/`detail`; the run is started in a
  background thread and `POST /admin/games/{id}/research` returns `{run_id}`
  immediately; `GET /admin/research/{run_id}` reports progress.

### Pool — the idea review workspace

- **Job:** decide which ideas become dares, and hand them to creators.
- **Primary action:** approve / reject / assign, fast.
- **Work happening:** a filterable, sortable table (search, game, source kind,
  min score, sort by score/date/source) with checkboxes and **bulk
  approve / reject / assign**. Expanding a row shows the card, the hook, the
  real sources with links, and the virality score with its parts.
- **Key actions:** bulk approve, bulk assign, write cards, review with AI.
- **Before/after:** before = a 3-up card grid, one button per card, no filters,
  no bulk. After = a dense review table with a real filter bar and bulk actions.
- **Backend:** `GET /admin/pool` gains `q`, `source`, `min_score`; new
  `POST /admin/pool/bulk` (`{ids, action, user_id?}`).

### Projects — the pipeline board

- **Job:** move each stream from planned to exported and see where it is stuck.
- **Primary action:** queue analysis / re-run a stage.
- **Work happening:** each project is a `ProgressCard` with the full
  `Pipeline` (Planned → Recording → Imported → Analyzing → Clips Ready →
  Reviewed → Exported), the current stage pulsing, the real job stage and
  candidate/clip counts, and the queue position. The list polls while any
  project is analyzing or queued. A board view groups projects by stage.
- **Key actions:** create, attach recording, run analysis, vision toggle,
  resume/re-run, delete.
- **Before/after:** before = badges in a flex-wrap row and a flat progress bar.
  After = a real pipeline with connectors and a live stage.

### Studio — the clip workspace

- **Job:** turn one recording into finished Shorts.
- **Primary action:** find moments, accept, generate.
- **Work happening:** the detect job's real stages (upload → transcribe →
  detect → rank), live system load, then candidates appearing one by one with
  score, reason and thumbnail, vision suggestions labelled, and the generated
  clips rendering through their real stages (fetch → transcribe → select →
  render → store) with the worker's live percentage.
- **Key actions:** upload, import from SSD, find moments, vision pass, accept
  top N, per-candidate trim/template, generate, re-render.
- **Before/after:** before = two flat cards for compute/system plus a candidate
  list with no progress. After = a live job pipeline at the top and a candidate
  rail that fills as detection proceeds.

### Captions / clip editor — live caption generation and styling

- **Job:** make the words and the look right, then approve.
- **Primary action:** edit captions, restyle, approve.
- **Work happening:** the caption editor shows the source (override vs
  transcript), the caption style being burned, and a live re-render progress
  bar when a save triggers one; the render's real stage and percentage show
  next to the preview.
- **Key actions:** edit text/timing, add/remove line, save, trim, layout,
  caption style, voice-over, AI review, approve, export.
- **Before/after:** before = the editor was a bare grid of inputs and the
  re-render was invisible. After = the editor states what it is editing, shows
  the render progress, and the preview updates in place.

### Calendar — the posting queue

- **Job:** keep the cadence and get Shorts out.
- **Primary action:** drag an approved Short onto a day.
- **Work happening:** the 7-day strip with the cadence guardrail lit, the queue
  as a table with state, and a per-platform export action. Shows the count
  already scheduled today and warns on over-cadence.
- **Key actions:** schedule, mark published, remove, export per platform.
- **Before/after:** before = a form + a drag list + a table, all in one card.
  After = the week as the primary surface, the queue beside it, and the
  guardrail visible before you drop.

### Long-form — the session recap builder

- **Job:** assemble a session's Shorts into one video.
- **Primary action:** pick clips and build.
- **Work happening:** the build job's real state (queued/running/ready/failed)
  with progress, and the clip picker shows each clip's duration and state.
- **Key actions:** build, download, retry a failed build.
- **Before/after:** before = a checkbox list and a static table. After = a
  picker with real durations plus a live build row.

### Results — what worked

- **Job:** read the leading indicators and feed them back into ranking.
- **Primary action:** read the best/worst and record metrics.
- **Work happening:** best and worst clips by swipe-through and saves/1k, the
  by-type breakdown, and the metric-entry dialog. No fabricated numbers; the
  recorded provider's canned figures stay labelled.
- **Key actions:** add metrics, filter by type, sort.
- **Before/after:** before = three tiles and a table. After = a best/worst
  comparison with a leading-indicator sort, and the AI summary kept but clearly
  labelled fallback.

### Models — the local engine

- **Job:** keep the local models installed, loaded and free.
- **Primary action:** pull / unload / free.
- **Work happening:** live host RAM, Ollama VRAM, MLX peak and the loaded-model
  list; a pull shows a real progress bar; the suggested engine shows install
  state and fit.
- **Key actions:** pull, unload, free all, save provider, install suggested.
- **Before/after:** before = four `Stat` tiles in a grid plus a table. After =
  one live engine panel (memory + loaded models + pull progress) and one
  provider panel.

### Setup — the health page

- **Job:** prove every key and connection works.
- **Primary action:** fix the failing check.
- **Work happening:** the doctor checks as a pass/fail list with detail, and the
  integration keys with status dots, masked values, a real Test call and a
  "where to get this" link.
- **Key actions:** save/test/remove a key, run a check.
- **Before/after:** before = a stat grid plus a flat pass/fail list. After =
  grouped checks (Database, AI, Research sources, Storage) with the failing
  one first and a direct fix action.

### Users / Invites — the roster

- **Job:** manage who can sign in.
- **Primary action:** change a role, issue an invite, reset a password.
- **Work happening:** locked accounts flagged, open invites counted, a created
  invite shown once with copy.
- **Before/after:** before = a plain table. After = a roster table with a
  signed-in/locked state, role changes that take effect immediately, and an
  invites panel with open/used/revoked state.

### Gamer pages

- **Dashboard `/`:** the command center for a creator — today's dare, the next
  action, and the clips awaiting review, with the render stage on any clip
  still working. Before: a stat wall.
- **Today `/today`:** the dare card plus the assigned state and the three
  picks; accept/swap. Work happening: the assignment state.
- **Go Live `/live`:** the pre-stream checklist with real OBS signals and a
  per-stream connection indicator; the stream's own status.
- **Remote `/remote`:** Start/Done with the clip window and the offline queue.
- **Clips `/clips`, `/clips/[id]`, `/export/[id]`:** a review queue with real
  render stages, the caption editor, commentary, export.
- **History `/history`:** real search.
- **Results `/results`:** shared with admin.
- **Settings `/settings`:** caption/layout/voice defaults.

---

## 4. Backend work required

1. **`GET /admin/overview`** — one batched read: jobs (counts + active with
   stage), research runs (active + recent), all projects (admin sees all), pool
   counts, results best/worst, key health, system load, engine events, today's
   clips. One round trip, so the overview paints fast.
2. **`GET /admin/projects`** — admin-only, all users' projects (the existing
   `/projects` stays user-scoped).
3. **Async research runs** — `research_runs.stage`, `research_runs.detail`;
   `POST /admin/games/{id}/research` returns `{run_id}` and runs the pipeline in
   a thread; `GET /admin/research/{run_id}` returns progress. This is what makes
   "research running with its sources" real.
4. **Pool filters + bulk** — `q`, `source`, `min_score`, `sort`; `POST
   /admin/pool/bulk`.
5. **Contract** regenerated; both directions enforced by
   `tests/acceptance/test_contract.py`.

---

## 5. Before / after summary

| Page | Before | After |
| --- | --- | --- |
| Overview | 12 flat stat tiles | live strip + needs-you rail + pipeline strip |
| Games | grid of tiles, blocking research button | game cards + live research pipeline with sources and output |
| Pool | 3-up cards, one button each | filterable table, row expansion, bulk actions |
| Projects | badge row + flat bar | pipeline with connectors, live stage, queue position |
| Studio | flat compute/system cards | live job pipeline, candidates arriving, render stages |
| Clip editor | bare input grid | sourced editor + live re-render progress |
| Calendar | form + list + table in one card | week-first surface, queue beside, guardrail lit |
| Long-form | checkbox list + static table | picker with durations + live build row |
| Results | three tiles + table | best/worst comparison, leading-indicator sort |
| Models | four stat tiles + table | live engine panel + provider panel + pull progress |
| Setup | stat grid + pass/fail list | grouped checks + integration keys with test |
| Users/Invites | plain tables | roster with state + invite panel |

---

## 6. Verification plan (Phase 3)

- Every page: real data, all four states, dark + light, 390 px + 1280 px.
- Screenshots: `docs/screens/before/` (this build) and `docs/screens/after/`.
- `make budgets` for LCP/TBT; unit + acceptance + contract green.
- A human visual verdict is **pending** — screenshots are saved, the verdict is
  not claimed.
- Honest labels: a page with no footage or no live keys must say so, not fake a
  filled state.
