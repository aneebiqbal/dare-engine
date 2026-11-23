# Design direction

## Rebuild sprint — identity: "Volt"

A bold gaming creator tool, not a SaaS dashboard. OLED black with a blue cast,
one **electric volt** accent (`#C8FF3D`) and a **deep violet** secondary
(`#8B7CFF`), a fixed radial mesh gradient behind the app, Geist Sans with a
tight display tracking, and a volt edge + soft glow reserved for the three
signature moments. Light mode swaps volt for indigo so the accent always clears
contrast. Motion is one curve, `cubic-bezier(0.22, 1, 0.36, 1)`, only
`transform` + `opacity`, and everything is disabled under
`prefers-reduced-motion: reduce`.

Signature moments: the **dare card** (volt edge, glow, the hook set large),
the **live render progress** (gradient bar with a volt glow), and the
**leaderboard** (large rank numerals, top three in the gradient).

## Concept, in three sentences

Clipdesk Missions turns a stream into a series: every mission is a card with a
hook, a win condition and a title, written before the game starts. The creator
taps Start and Done; the platform cuts that exact window into a 9:16 Short with
hook text, word captions and an end card. The mission mark and the pooled
attempts make the series recognisable across channels.

## Voice

Quiet, confident, broadcast-grade. Dark OLED surfaces with one accent, generous
whitespace, and type that reads from across the room. Nothing decorative
competes with the gameplay.

## Type scale

Geist Sans, one family, five steps. Tracks tight on display sizes, looser on body.

| Token | Size | Line height | Use |
| --- | --- | --- | --- |
| `--step-display` | 4.5rem | 1.02 | Hero, live timer |
| `--step-h1` | 3rem | 1.05 | Page titles |
| `--step-h2` | 1.5rem | 1.3 | Card titles, overlay mission |
| `--step-body` | 1rem | 1.55 | Body, captions |
| `--step-label` | 0.75rem | 1.4 | Eyebrows, badges (uppercase, +0.2em) |

## Colour roles

| Role | Light | Dark |
| --- | --- | --- |
| `--bg` | warm cream `#FDFBF7` | OLED `#050505` |
| `--surface` | white | `#0E0E0E` |
| `--surface-2` | `#F4F1EA` | white at 4% |
| `--border` | black at 8% | white at 9% |
| `--text` | `#141311` | `#FAFAFA` |
| `--muted` | text at 58% | text at 58% |
| `--accent` | indigo `#4F46E5` | indigo-400 `#818CF8` |
| `--success` / `--danger` | emerald / orange | emerald-400 / orange-400 |

One accent. Colour is for state (live, success, danger), never for decoration.

## Spacing and radius

4-point scale: 1, 2, 3, 4, 6, 8, 12, 16, 24. Cards use a double bezel: an outer
shell at `radius-lg` (2rem) with a hairline ring, and an inner core at
`calc(2rem - 0.375rem)`. Buttons are pills. Nothing is a hard rectangle.

## Motion

One curve: `cubic-bezier(0.22, 1, 0.36, 1)`, 300 ms for state, 400 ms for theme.
Only `transform` and `opacity` animate. Every transition is disabled under
`prefers-reduced-motion: reduce`.

## Signature moments

1. **The dare card.** One question, one hook, one win condition, one result
   type. The card is the unit of the product: it is drawn the same on Today, on
   the Dashboard, in the admin pool and on the public mission page. The hook is
   the largest text, the question carries the detail, and the result type is a
   badge, so a creator can judge a dare at a glance and an editor can scan the
   pool. The daily dare gets the accent; picks are muted.
2. **The live job progress.** A render is a queue of real stages (fetch,
   transcribe, select, render, store). The Clips grid and the clip review show
   the stage name and a thin accent bar that fills with the real percentage from
   the worker; the admin job queue shows the same stage per job. Waiting is the
   feeling we are replacing, so the numbers are the interface, not decoration.
   When the Short lands, the card rises and settles (`translateY` + `opacity`)
   and the thumbnail replaces the skeleton.
3. **The leaderboard.** Rank is a large numeral with the creator's name and
   result; the top three get the accent, everyone else is muted. The dare mark
   sits in the corner so the series is recognisable.

## What we do not do

No default component-library look: no all-grey cards, no drop-shadow stacks, no
linear easing, no scrolling marquees. If a screen could be any dashboard, it is
not done.

## Redesign — identity: "Control room"

Status: **built. Visual verdict pending a human looking at the screenshots.**

The first identity ("Volt") was a broadcast look: OLED black, one volt accent,
tiles in a grid. The pages showed counts, not work. The redesign keeps the
dare card as the one brand moment and turns every page into a working surface.

### Colour

Light is the default working theme (cool silver `#F3F4F6`, white surfaces,
diffused ambient shadows); dark is a first-class alternative (`#0A0C0F`,
`#12151A`). The accent is a **signal blue** (`#2158E0` light / `#8FB4FF` dark,
chosen to clear 4.5:1 on its own soft tint) and means *running*. Three more status colours complete the vocabulary: **needs-you**
amber, **done** green, **failed** red. A colour never decorates; it always
carries one of those five meanings. The volt accent survives only on the dare
card and the brand mark (`--signature`).

### Type

Geist Sans for UI, **Geist Mono for numbers, stages, ids and timestamps** — a
tool shows values in mono. Scale: 3.5rem display (the one live timer), 2.25rem
page title, 1.125rem section title, 0.9375rem body, 0.6875rem uppercase labels.

### Layout

A persistent left rail, a **live status strip** under the header on the admin
command center, a wide main column and a 320 px right rail (live status, needs
you, activity) on desktop, collapsing to one column under 1024 px. The equal
`md:2 / xl:3 / 2xl:4` tile grid is gone.

### Motion

One curve, `cubic-bezier(0.22, 1, 0.36, 1)`, three moves: **progress** (a
pipeline connector or bar fills), **live** (the running dot breathes, only while
work is actually running), **arrive** (a finished item settles). Nothing else
animates; `prefers-reduced-motion: reduce` kills all of it.

### Component kit

`web/components/work.tsx` — `WorkHeader`, `LiveStrip`, `Pipeline`,
`ProgressCard`, `StatusBadge`, `LiveDot`, `WorkQueue`, `ActivityFeed`, `Metric`,
`WorkEmpty`, `FilterBar`, `DataTable`, `Section`, `Rail`. Every rebuilt page is
built from these, so the states and the status vocabulary are the same
everywhere.

### Work is the interface

- Research runs in a background thread and reports `fetch → write → store`; the
  admin watches the pipeline, the source counts and the stored ideas.
- Projects show the full stage pipeline (Planned → … → Exported) with the real
  job stage and queue position.
- The studio shows the detection job's real stage and the render stages
  (`fetch → transcribe → select → render → store`) with the worker's percentage.
- The clip editor states its source (override vs transcript) and shows the
  re-render progress it triggered.
- The overview is one batched `/admin/overview` read: live strip, needs-you,
  projects, job queue, activity, best/worst results, key health.

## Sprint 6 — the app shell and layout system

**Concept.** A quiet broadcast desk: one persistent rail for where you are, one
wide canvas for the work, and a single accent that means "this is live". The
shell is the same on a phone and on a wide monitor; only the rail moves.

**Shell.** A collapsible left rail (2 rem, hairline right border) with icon +
label links; the label collapses to the icon under `md`. On phones the rail
becomes an overlay from a top-bar menu button. The top bar is sticky, blurred,
and holds page search, the account menu and the theme toggle. Content uses the
full window width up to `1600px`, in a responsive card grid
(`md:2`, `xl:3`, `2xl:4`). No narrow centred column on desktop.

**States.** Every page renders the same four: a skeleton grid while loading, an
error card with the message, an empty state with one action, and the filled
grid. A fallback notice is shown whenever an AI path is used.

**Motion.** One curve, `cubic-bezier(0.22, 1, 0.36, 1)`; rail width 300 ms,
theme 400 ms, scroll entry 800 ms. Only `transform` and `opacity` animate,
except the rail's width, which is a layout property but a systemic chrome
element. `prefers-reduced-motion: reduce` disables all of it.

**Tour.** Tooltips anchor to `data-tour` elements, highlight the target with an
accent ring, and are keyboard-only operable: `→`/`Enter` next, `←` back,
`Esc` skip. Progress is stored per user and never blocks work.
