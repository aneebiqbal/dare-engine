# Screenshots — before and after

## `after/gamer/`

The rebuilt gamer section on the real stack: 44 shots, phone/desktop ×
dark/light. Every image is either a real frame from a rendered clip (six real
renders seeded into local storage for this run) or the clean graphite
`Thumb` fallback — no broken icons, no cropped frames. Captured with
`scripts/capture_gamer.py`.

## `after/2026-11-25-editorial/`

The Editorial Graphite + Burnt Coral re-theme, captured against the real Neon
database on the locally running stack: 68 shots, phone/desktop × dark/light.
Cover art leads, panels are flat sheets with hairlines, coral marks running
state and primary actions only. Capture script: `scripts/capture_after.py`
(shared session per viewport/theme; the QA admin used for these runs must be
deleted before launch).

## `before/`

The pre-redesign build, captured with the screenshot mock layer on so every page
shows a filled state. This is the reference for what changed: the admin overview
is twelve flat stat tiles, pages are equal card grids, and nothing shows work in
progress. 128 shots (29 pages × phone/desktop × dark/light).

## `after/real/`

The redesigned build on the **real stack and database** (no mock). Every page
reads the live API. Pages with no data say so. This is the honesty reference: it
shows which surfaces are empty because the owner's footage or live keys are
missing.

## `after/mock/`

The redesigned build with the screenshot mock layer on, so every page shows its
filled, working state (research running, jobs in flight, projects analysing,
clips rendering). This is the layout reference.

Every shot is phone (390×844) and desktop (1280×900), dark and light.

## `after/2026-11-24/`

Fresh shots of this session's changes, captured against a locally running API
and `next dev` on the real Neon database (not the mock): cover-art games cards,
the platform selectors, the clip editor opening a real pipeline clip, and the
`/landing` download page. 68 shots, phone/desktop × dark/light.

```sh
# terminal 1 — API against Neon, with a writable storage dir
PYDIR=$(cat /tmp/clipdesk_pydir)
PYTHONPATH="api:shared:$PYDIR" STORAGE_LOCAL_DIR="$PYDIR/storage" \
  .venv/bin/python -m uvicorn app.main:app --port 8001
# terminal 2 — web
cd web && API_URL=http://127.0.0.1:8001 NEXT_PUBLIC_DEV_AUTH=1 npm run dev -- -p 3200
# terminal 3 — capture
.venv/bin/python scripts/capture_after.py
```

The QA admin (`qa-admin@example.com`) is created in the shared dev database by
hand for these runs; delete it before launch.

**Capture caveat.** These were taken against `next dev`, not the production
build. Two artefacts of dev mode are visible: the admin overview was caught in
its skeleton state (client hydration/polling under dev compilation), and a few
documents fell back to the signed-out shell mid-run. The dark set and
`after/mock/` show the same routes filled; the product build itself is green.
The visual verdict is a human call either way.

## Honest labels

- **Real work:** jobs, projects, clips, research runs, calendar, users, invites,
  models and keys all read the live API/database.
- **Clip / export in `after/real`:** those two routes are user-scoped
  (`GET /clips/{id}` joins the clip's assignment to the session user). The
  signed-in admin owns no clip, and the shared database was being truncated by a
  concurrent test run, so those four shots are the real 404 page. The mock set
  (`after/mock`) shows the same routes filled.
- **Stand-in:** the AI provider is the recorded provider unless a live key is
  stored; research uses the saved sample feed unless YouTube/Reddit keys are
  stored; publishing is a manual marker.
- **Empty because it needs the owner:** clip quality (no owner gameplay fixture),
  live source trends (keys), real metrics (a YouTube collector).

## How they were captured

```sh
# before (pre-redesign commit, mock on)
git archive d5673fc docs/screens | tar -x -C /tmp/old
cp /tmp/old/docs/screens/*.png docs/screens/before/

# after, real data
.venv/bin/python tests/screenshots/redesign.py --label after/real

# after, mock-filled
NEXT_PUBLIC_API_MOCK=1 docker compose up -d --wait --build
CLIPDESK_SCREENS_DIR=docs/screens/after/mock .venv/bin/python tests/screenshots/capture.py
NEXT_PUBLIC_API_MOCK=0 docker compose up -d --wait --build
```
