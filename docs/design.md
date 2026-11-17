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

1. **The live mission timer.** On `/remote`, the mission card carries a running
   timer once Start is tapped: tabular numerals, a one-pixel accent bar that
   fills with elapsed time, and the connection indicator. It is the screen the
   creator glances at mid-game, so it is big, high-contrast and legible in
   peripheral vision.
2. **The moment a finished Short appears.** The Clips card flips from a skeleton
   to the thumbnail with a 300 ms rise-and-settle (`translateY` + `opacity`), and
   a "Ready" badge. The stage (fetch → transcribe → select → render → upload) is
   visible as a thin progress bar, because waiting is the feeling we are
   replacing.
3. **The leaderboard.** Rank is a large numeral with the creator's name and
   result; the top three get the accent, everyone else is muted. The mission
   mark sits in the corner so the series is recognisable.

## What we do not do

No default component-library look: no all-grey cards, no drop-shadow stacks, no
linear easing, no scrolling marquees. If a screen could be any dashboard, it is
not done.
