# Design direction — Editorial Graphite + Burnt Coral

Status: **direction committed.** Written before the execution prompt and before
any code changes. Palette validated for WCAG contrast and checked against real
gameplay imagery (`docs/design/imagery/`).

This replaces the earlier "Control room" (signal blue) and "Volt" (electric
citron) identities. Product truth, research, typography family, component
architecture and functional decisions are preserved. The visual world is
replaced, not polished.

---

## 1. Product truth this identity serves

Clipdesk is a working tool for people who cut gameplay into Shorts. Two scenes
share the product:

- **Operate:** research, pool, calendar, models, setup — long sessions, dense
  information, judgment under time.
- **Experience/Persuade:** the games showcase, the landing page, the clip
  review — the surfaces where the owner decides whether the product is good.

The identity must therefore be calm and exact where people work, and
unmistakably authored where people look. Gameplay footage supplies the colour
and energy; the interface supplies the frame, the type and the grammar. The
brand accent is scarce because the work itself is loud.

**The one idea:** a printed editorial broadsheet rebuilt as a dark editing
desk — hairline rules instead of cards, running folios instead of badges, a
single coral rule marking what is live, and full-bleed artwork doing the
talking. The category default it refuses: the SaaS dashboard of rounded tiles,
blue accent and equal grids.

## 2. Colour (pinned by the brief, then validated)

Dark is the working scene (an editor judging footage at night, on a calibrated
display, next to bright gameplay). Light is the paper counterpart for reading
and planning in daylight.

### Dark

| Token | Value | Use |
| --- | --- | --- |
| `--bg` | `#171717` | Application background |
| `--surface` | `#1E1E1C` | Panels, tables, editor chrome |
| `--surface-2` | `#292825` | Inset wells, secondary columns |
| `--surface-3` | `#33312D` | Raised controls, inputs |
| `--border` | `#36332F` | Hairlines, table rules, panel edges |
| `--text` | `#F2F0EB` | Primary text |
| `--muted` | `#A49F99` | Secondary text, metadata, timestamps |
| `--accent` | `#E98D72` | Brand / running state / primary action only |
| `--accent-ink` | `#221512` | Text or ink on an accent fill |
| `--accent-soft` | `#2A211D` | Tinted well behind accent information |

### Light

| Token | Value | Use |
| --- | --- | --- |
| `--bg` | `#F6F2EA` | Warm paper ground |
| `--surface` | `#FDFAF3` | Sheets, panels |
| `--surface-2` | `#EFE8DC` | Inset wells |
| `--surface-3` | `#E5DCCB` | Raised controls |
| `--border` | `#DCD2C2` | Hairlines |
| `--text` | `#221F1C` | Ink |
| `--muted` | `#6E675F` | Secondary text |
| `--accent` | `#AD4B35` | Burnt coral, accessible on paper |
| `--accent-ink` | `#FFF6EF` | Ink on accent fills |
| `--accent-soft` | `#F7EBE2` | Tinted well |

### Status vocabulary (derived, not decorative)

Colour carries exactly one of five meanings everywhere: `running` (accent),
`needs-you` (ochre), `done` (sage), `failed` (brick), `idle` (neutral
`--muted`). No other chromatic use exists.

| State | Dark | Light |
| --- | --- | --- |
| needs-you | `#D9A441` / soft `#2E2718` | `#8A5A1F` / soft `#F0E4CC` |
| done | `#8FB09C` / soft `#1F2A22` | `#3F6B4F` / soft `#E3EAE0` |
| failed | `#D3776A` / soft `#2E1E1C` | `#A83A2C` / soft `#F2DED9` |

### Accessibility validation (WCAG relative luminance, computed)

| Pair | Dark | Light | Requirement |
| --- | --- | --- | --- |
| text on bg / surface | 15.7 / 14.7 | 14.7 / 15.7 | ≥ 4.5 ✓ |
| muted on surface / surface-2 | 6.4 / 5.6 | 5.4 / 4.6 | ≥ 4.5 ✓ |
| accent on surface (text) | 6.8 | 5.3 | ≥ 4.5 ✓ |
| accent on accent-soft | 6.4 | 4.7 | ≥ 4.5 ✓ |
| accent-ink on accent (buttons) | 7.2 | 5.1 | ≥ 4.5 ✓ |
| success on surface | 7.0 | 5.9 | ≥ 4.5 ✓ |
| needs on surface | 7.4 | 5.7 | ≥ 4.5 ✓ |
| danger on surface / surface-2 | 5.3 / 4.6 | 6.1 / 5.2 | ≥ 4.5 ✓ |

Rules that follow from the numbers:

- Never put white ink on coral in dark mode (2.5:1) — use `--accent-ink`.
- Never use coral for small text on an elevated surface without checking;
  the table above is the pre-check.
- Placeholder and disabled text use `--muted`, never a lighter gray invented
  per component.
- Focus ring is accent at 2 px with 2 px offset; it clears the surrounding
  surface at 6.8–7.3:1.

Re-run the check after any token change:

```sh
.venv/bin/python scripts/validate_palette.py   # exits non-zero on a failure
```


## 3. Typography

Family is preserved: **Geist Sans** for interface and display, **Geist Mono**
for data, timestamps, identifiers and stage names. No new face is added; the
ambition lives in scale, tracking and rhythm.

| Token | Size / line | Use |
| --- | --- | --- |
| `--step-display` | clamp(2.75rem, 6vw, 4.5rem) / 1.0 | One live number or hero line per screen |
| `--step-h1` | clamp(2rem, 4vw, 3rem) / 1.05 | Page titles, weight 600, tracking −0.02em |
| `--step-h2` | 1.25rem / 1.3 | Section titles, weight 600 |
| `--step-body` | 0.9375rem / 1.6 | Body, measure ≤ 72ch |
| `--step-label` | 0.6875rem / 1.3 | Folio labels, tracked +0.16em, muted |
| `--step-mono` | 0.8125rem / 1.4 | Data, mono, tabular figures |

Editorial rules:

- Headings carry their own weight. No kicker pill above a page title; where a
  running label survives it is a folio marker (mono, muted, separated by a
  hairline), never a coloured chip.
- Numbers are always mono: counts, scores, durations, timestamps, queue
  positions.
- Uppercase exists only in the 0.6875rem folio labels, never for body copy.
- Display lines may be sentence case, tight-tracked, and large. No gradient
  text, no outline text.

## 4. Layout and composition

- **Grid:** a 12-column editorial grid with intentional asymmetry. Wide work
  surface plus a narrow 20–24 rem reading rail; the rail holds status and
  provenance, not duplicated metrics. Breakpoints: one column below 900 px.
- **Panels, not cards:** surfaces are separated by 1 px hairlines and space,
  not stacked rounded rectangles. Double-bezel survives only as an outer
  hairline shell at 2 px radius around an inner flat core — the frame is drawn
  once, never twice.
- **Radius scale:** 2 px (labels, chips), 4 px (controls), 6 px (buttons,
  inputs), 8 px (media frames), 10 px (large sheets). Nothing is a pill.
- **Depth:** a panel is a surface tone plus a hairline. Shadows are reserved
  for things that float above content (dialogs, menus, toasts):
  `0 1px 0 rgb(0 0 0 / 0.24), 0 12px 32px -16px rgb(0 0 0 / 0.55)`.
  No glow, no neon, no glass, no purple gradients.
- **Whitespace:** generous separation between regions (48–96 px on desktop),
  tight grouping inside them (8–16 px). More space above a heading than below.
- **Imagery-led zones:** the games grid and the clip review let artwork fill
  the frame edge-to-edge with a 1 px border; the interface recedes around it.

## 5. Component language

Everything is rebuilt from the existing kit (`web/components/work.tsx`,
`ui.tsx`) so behaviour and accessibility stay identical.

| Element | Treatment |
| --- | --- |
| Page header | Title in display scale; a quiet mono folio at the left margin; primary action right-aligned, squared 6 px |
| Panel | Flat `--surface`, 1 px `--border`; header row separated by a hairline, not padding alone |
| Buttons | 6 px radius, 1 px border, no shadow; primary = accent fill with accent-ink; secondary = surface-3 with border |
| Badges | Small square 2 px chips, mono label, tinted soft backgrounds only for status; brand accent badge only for “live” |
| Tables | Hairline row rules, no outer box, numeric columns right-aligned mono, generous row height |
| Progress | 2 px track, accent fill; percentage and ETA in mono beside it |
| Live state | Breathing 6 px dot in accent, used only while work runs |
| Covers | Full-width media plate, object-cover, hairline border, title set over a short gradient scrim only where legibility requires it |
| Editor surfaces | Neutral `--bg`/`--surface` with zero accent inside the preview frame; coral appears only in controls outside the image |
| Dialogs / toasts | Float above with the single allowed shadow; toast is a quiet sheet with a 2 px accent edge, not a pill |

## 6. Motion

One curve, `cubic-bezier(0.22, 1, 0.36, 1)`; durations 200–420 ms.

1. **Progress** — bars and pipeline connectors fill (transform/width).
2. **Live** — the running dot breathes, only while work runs.
3. **Arrive** — finished clips settle 12 px upward into place.

No hover lift, no staggered card entrances, no marquee, no scroll-reveal walls.
`prefers-reduced-motion: reduce` disables all three.

## 7. Imagery validation (real, checked)

Downloads of the live RAWG catalogue used by the product, stored beside this
document:

| File | What it proves |
| --- | --- |
| `imagery/gta-iv-cover.jpg` | Painted key art reads well against graphite; warm neutrals do not fight it |
| `imagery/gta-vi-cover.jpg` | Photographic cover is cool/saturated; the warm frame makes it stand out rather than blend |
| `imagery/flow-cover.jpg` | Abstract art; confirms the UI must supply structure when art is non-representational |
| `imagery/gta-iv-shot.jpg` | Real gameplay: bright, cool, high-energy — the interface must stay neutral around it for colour judgment |

Findings applied:

- Artwork is presented **without duotone or heavy overlays**; a scrim is used
  only behind captions.
- Editing/review surfaces stay neutral (no accent washes) so footage colour is
  judged accurately.
- Cover art must be served at card size. RAWG originals can be 3–4 MB; the
  games grid needs resized caches (follow-up: `scripts/cache_game_art.py`).
- The showcase page lets art occupy ≥ 60% of the first viewport of each card;
  metadata sits below, not on top.

## 8. Explicit refusals

No electric citron, no purple/violet, no blue signal accent, no glow borders,
no glassmorphism, no oversized pills/badges, no equal-card dashboards, no
generic shadcn defaults, no gradient text, no hard offset shadows, no emoji
icons, no coloured borders thicker than 1 px as decoration.

## 9. Execution

The build order, token mapping and per-surface checks live in
`docs/design-execution-prompt.md`. That document is the instruction set for
the re-theme; this document is the identity it must match.
