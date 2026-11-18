# Design direction

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
