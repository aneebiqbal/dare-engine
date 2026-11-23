# Screenshots — before and after

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
