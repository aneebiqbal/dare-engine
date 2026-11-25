# Execution prompt — Editorial Graphite + Burnt Coral re-theme

Input: `docs/design-direction.md` (the identity). This document is the build
order. Do not restyle component-by-component at random; run the phases in
order and keep every page on the shared tokens.

Hard constraints:

- Preserve all research, copy, data flow, API contracts, job behaviour,
  accessibility semantics and the existing component architecture.
- No new dependencies, no new fonts, no CSS frameworks.
- Dark is the default working theme; light is a first-class alternative.
- Accent is scarce: running state, the primary action, focus, live markers.
  Never decorate with coral.
- Editing/review surfaces stay neutral; footage must be judged accurately.
- Verify by looking at real renders at 390 px and 1280–1440 px, dark and light,
  before calling any phase done.

## Phase 0 — Tokens (foundation only)

Replace the token block in `web/app/globals.css` with the validated values:

```
dark: bg #171717 · surface #1E1E1C · surface-2 #292825 · surface-3 #33312D
      border #36332F · text #F2F0EB · muted #A49F99
      accent #E98D72 · accent-ink #221512 · accent-soft #2A211D
      needs #D9A441 / #2E2718 · success #8FB09C / #1F2A22 · danger #D3776A / #2E1E1C
light: bg #F6F2EA · surface #FDFAF3 · surface-2 #EFE8DC · surface-3 #E5DCCB
      border #DCD2C2 · text #221F1C · muted #6E675F
      accent #AD4B35 · accent-ink #FFF6EF · accent-soft #F7EBE2
      needs #8A5A1F / #F0E4CC · success #3F6B4F / #E3EAE0 · danger #A83A2C / #F2DED9
```

Also in that file:

- Radius scale: `--radius-sm: 2px; --radius: 4px; --radius-md: 6px; --radius-lg: 8px; --radius-sheet: 10px`.
- One shadow token for floating layers only; remove ambient card shadows from
  panels (panels are surface + hairline).
- Remove the `.dark body` radial mesh gradients, the `--signature` volt edge,
  `--accent-2`, and every glow/gradient rule.
- Redefine `.bezel` as outer hairline + flat core (2 px outer, 4 px inner);
  `.ring-surface` stays a 1 px inset hairline.
- Selection colour: accent background with accent-ink text. Caret: accent.
- Custom scrollbars and focus rings themed from tokens.
- Type scale tokens exactly as in the direction document.

Gate: `next build` green; grep shows no `#c8ff3d`, `#8b7cff`, `#7c6cff`,
`#2158e0`, no `radial-gradient` in `globals.css`.

## Phase 1 — Chrome and primitives

Files: `web/components/ui.tsx`, `web/components/shell.tsx`,
`web/components/icons.tsx`, `web/components/theme.tsx`,
`web/components/tour.tsx`.

- Card/panel: flat surface, 1 px border, small radii; header separated by a
  hairline; remove double-bezel nesting where it creates card-in-card.
- Buttons: squared 6 px, no shadow; primary accent fill/accent-ink; secondary
  surface-3 + border; danger uses the status token, not a hardcoded red.
- Inputs/selects: 4 px radius, surface-2 ground, hairline border, accent caret
  and accent focus ring.
- Badges: square 2 px, mono 10 px label, tinted soft only for status; no
  oversized pills.
- Progress: 2 px track, accent fill, no gradient.
- Shell: sidebar becomes a flat graphite rail separated by a hairline; nav
  items are quiet text rows with a 2 px accent indicator for the current page;
  the top bar keeps a 1 px bottom rule. No blur, no glow.
- Eyebrow/folio: render as a mono tracked muted label, no coloured pill.

Gate: capture `/signin`, `/admin`, `/admin/games` at 390 and 1440, both
themes. Panels read as paper/sheet, not rounded tiles.

## Phase 2 — Work surfaces

Files: `work.tsx`, `admin.tsx`, `games.tsx`, `projects.tsx`, `pipeline.tsx`,
`studio.tsx`, `pool`/`calendar`/`long-form`/`results`/`models`/`setup`/
`users`/`invites` as rendered through the kit.

- Apply the panel/hairline language; keep the four states (loading, error,
  empty, filled) and all polling.
- Live strip and activity feed: hairline-separated rows, mono numbers, accent
  only for running items.
- Tables: no outer box, hairline row rules, right-aligned mono numeric
  columns.
- Pipeline: keep stage text + ETA + converging percentage; progress fill is
  accent; connectors are hairlines, not thick rounded bars.
- Completion toast: quiet sheet with a 2 px accent edge.
- Games showcase: full-width media plate per card, art ≥ 60% of the card’s
  first screen, metadata below the image, no gradient overlay beyond a caption
  scrim. Fallback for missing art is a flat graphite monogram, never a grey
  tile or a drawn fake cover.
- Setup invite: a quiet editorial note, accent used once.

Gate: every admin route captured; no page still shows blue/violet/citron; no
page lost its loading/empty/error state.

## Phase 3 — Media surfaces

Files: `clip-review.tsx`, `caption-editor.tsx`, `clips.tsx`,
`export-package.tsx`, `landing/page.tsx`, `welcome/page.tsx`, `dare-card.tsx`.

- Clip review: neutral frame around the preview; captions/editor controls use
  surface-2 with hairlines; platform selector and action buttons follow the
  primitive rules; accent only for the running render state.
- Landing/welcome: replace the purple radial wash with flat paper/graphite and
  one coral rule; hero type in the display scale; download cards become
  editorial panels with hairline separators; artwork replaces decoration.
- Dare card: keep it as the one brand artefact, but recut in graphite + coral
  (no volt edge, no glow).

Gate: capture `/clips/<real-id>`, `/landing`, `/welcome`; the footage must
read neutral and the coral must feel scarce.

## Phase 4 — Real-data QA

- Restart the local API (Neon) + `next dev`; run
  `scripts/capture_after.py`-style captures into
  `docs/screens/after/<date>-editorial/`.
- Check 390 px and 1440 px, dark and light, on: dashboard, today, admin
  overview, games grid, game profile, pool, projects, studio, clip review,
  clips, calendar, landing, welcome, signin.
- Contrast: re-run the palette validation script and keep its table in
  `docs/design-direction.md`.
- Verify interactions on one page each: hover, focus, disabled, loading,
  empty, error.
- Fix in batches; two inspection rounds maximum.

Gate: screenshots show real data or honest empty states, real cover art, no
neon/blue/purple, no silent loader without explanation.

## Phase 5 — Documentation

- Update `docs/decisions.md` with the re-theme decision and what was preserved.
- Update `docs/BUILD_STATE.md` (design rows), `PROGRESS.md` (session log),
  `docs/pages.md` if any surface treatment changed.
- Record the palette validation table and the imagery findings.
- Leave `docs/design-direction.md` as the durable identity reference.

## Definition of done

Every surface rebuilt from the same tokens; accent scarce and meaningful;
gameplay artwork leads; editing surfaces neutral; both themes pass the
contrast table; no banned patterns survive; screenshots and docs current.
