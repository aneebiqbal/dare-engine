# 11 — Missions flow

## Create → review → approve

| Step | Actor | Route | Table | What happens |
| --- | --- | --- | --- | --- |
| 1 | admin | `POST /admin/questions` | `missions` | LLM writes cards; one row per card, `status='candidate'`, `card` jsonb |
| 2 | admin | `POST /ai/pool-review` | — | advisory merge/policy flags (not stored) |
| 3 | admin | `GET /admin/pool` | `missions` | lists `status='candidate'` |
| 4 | admin | `POST /admin/pool/{id}/approve` | `missions` | `status='unverified'` |
| 5 | admin | `POST /admin/pool/{id}/reject` | `missions` | `status='rejected'` |
| 6 | admin/creator | `PATCH /missions/{id}` | `missions` | edit the card |

The card shape is `contracts/mission-card.schema.json`; validated in
`api/app/missions.py:write_cards`.

## Assign → accept → mark → clip

| Step | Actor | Route | Table | What happens |
| --- | --- | --- | --- | --- |
| 1 | creator | `GET /today` | `missions`, `assignments` | daily + 3 picks from `unverified`; `accepted` map for today |
| 2 | creator | `POST /assignments` | `assignments` | `state='accepted'` |
| 3 | creator | `POST /assignments/{id}/swap` | `assignments` | `state='swapped'` |
| 4 | creator | `POST /streams` | `streams` | issues a key (relay path) |
| 5 | creator | `POST /marks` | `marks`, `clips`, `jobs` | start/done with `stream_time`; on done, one `render_clip` job |
| 6 | — | worker | `clips` | renders; `state='ready'` |
| 7 | creator | `POST /uploads` / `/uploads/{id}/complete` | `assignments`, `marks`, `clips`, `attempts`, `jobs` | one clip job per mark, plus an attempt |
| 8 | system | `attempts` | `attempts` | `result_value` from the result; ranked by `community.py` |
| 9 | creator | `POST /clips/{id}/trim`, `/voice-over` | `clips`, `jobs` | re-render |
| 10 | creator | `POST /clips/{id}/export` | `exports` | stores package metadata |
| 11 | creator | `POST /metrics` | `posts`, `metrics`, `missions` | manual views/retention; updates `missions.score` |
| 12 | creator | `GET /results`, `/ai/results-summary` | — | reads results + AI summary |

## What an admin does

Create the first admin (`make create-admin`), create invites, write and approve
missions, review the pool with AI, change roles, issue reset links, retry jobs,
read AI usage, the audit log and setup checks.

## What a creator does

Sign up with an invite, accept/swap/edit missions, go live or use the remote,
tap Start/Done, upload recordings, review/trim/style clips, add a voice-over,
export packages, enter results, read the AI summary.

## What nothing yet does

- **No daily pool refresh.** `daily_sets` has no writer; `/today` picks from all
  `unverified` missions by a date hash.
- **No question miner.** No YouTube Data API route or job.
- **No creator-submitted missions.** Only admins write questions.
- **No verification on completion.** A mission stays `unverified` after a
  creator completes it.
- **No automatic posting.** `POST /clips/{id}/post` only flips state and returns
  `unproven: "youtube"`; `posts`/`metrics` are manual.
- **No seasons or mission types grouping.** `missions.type` exists but is not
  set by the writer; `by_type` groups on `card->>'mode'`.
- **No plan limits.** `GET /settings` hardcodes `clips_limit: 5` but nothing
  enforces it.
