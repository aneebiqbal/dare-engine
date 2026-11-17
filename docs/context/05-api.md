# 05 — API

FastAPI app in `api/app/main.py`. Every mutating route except `/hooks/*`
requires a double-submit CSRF header (`X-CSRF-Token` == `clipdesk_csrf` cookie);
see `api/app/users.py:csrf_protect`. Errors have the shape
`{"detail": …, "error": {"status": …, "message": …}}`
(`api/app/main.py:http_error_handler`). List routes return
`{"items": […], "total": n, "page": p, "page_size": s}` (`api/app/paging.py`).

The route list below is the live `/openapi.json` (73 paths). The CI test
`tests/acceptance/test_contract.py` compares this set with
`contracts/openapi.yaml` in both directions; it passes, so **no route is
missing from the contract and no contract entry has no route**.

## Health — `api/app/main.py`

| Method | Path | Role | Response |
| --- | --- | --- | --- |
| GET | `/healthz` | public | `{"status":"ok"}` |
| GET | `/healthz/ready` | public | `{"status":"ready"}` after a pooled DB query |

## Auth — `api/app/auth.py`

| Method | Path | Role | Request → response |
| --- | --- | --- | --- |
| GET | `/auth/csrf` | public | sets `clipdesk_csrf`; `{"csrf": token}` |
| POST | `/auth/sign-up` | public | `{email,password,display_name,invite_code?}` → `{user}` + session cookie |
| POST | `/auth/sign-in` | public | `{email,password}` → `{ok}` + cookies |
| POST | `/auth/sign-out` | session | `{ok}` |
| POST | `/auth/sign-out-all` | session | deletes all user sessions |
| POST | `/auth/change-password` | session | `{current_password,new_password}` → `{ok}` |
| POST | `/auth/reset-password` | public | `{token,new_password}` → `{ok}` |
| POST | `/auth/dev/sign-in` | flag off | `{display_name}` → `{user,token}` |
| POST | `/auth/dev/sign-out` | flag off | `{ok}` |

## Missions — `api/app/missions.py`

| Method | Path | Role | Notes |
| --- | --- | --- | --- |
| POST | `/admin/questions` | admin | `{questions[]}` → `{cards,count,fallback}`; AI call `kind=cards` |
| GET | `/admin/pool` | admin | filter `status`, sort `created_at|id|score`, paging |
| POST | `/admin/pool/{id}/approve` | admin | → `{id,state}` |
| POST | `/admin/pool/{id}/reject` | admin | → `{id,state}` |
| GET | `/missions/{id}` | public | → `{id,card,score,state}` |
| PATCH | `/missions/{id}` | session | `{card}` → `{id,card}` |
| GET | `/today` | session | `{date,daily,picks,accepted}` |
| POST | `/assignments` | session | `{mission_id}` → `{id,mission_id,state}` |
| POST | `/assignments/{id}/swap` | session | `{mission_id}` → `{id,mission_id,state}` |
| GET | `/me` | session | `{user,channels:[]}` |

## Clips, marks, uploads — `api/app/clips.py`

| Method | Path | Role | Notes |
| --- | --- | --- | --- |
| POST | `/marks` | session | `{assignment_id,kind,result?,stream_time?}` → mark; on `done` enqueues a render |
| POST | `/uploads/start` | public (no session check) | `{upload_id,chunk_size}` |
| GET | `/uploads/{id}` | public (no session check) | `{upload_id,received:[indexes]}` |
| PUT | `/uploads/{id}/chunks/{index}` | public (no session check) | raw bytes; empty body |
| POST | `/uploads/{id}/complete` | session | `{marks[],filename}` → `{stream_id,clips,count}` |
| POST | `/uploads` | session | multipart `file` + `marks` (single-request path) |
| GET | `/clips` | session | filter `state`, sort, paging |
| GET | `/clips/{id}` | session | clip detail incl. `transcript` |
| PATCH | `/clips/{id}` | session | `{title,layout,caption_style,voice_over,voice,export_*}` |
| POST | `/clips/{id}/trim` | session | `{start,end}` → re-render with cached transcript |
| POST | `/clips/{id}/voice-over` | session | `{enabled,voice}` → re-render |
| POST | `/clips/{id}/voice-preview` | session | `{voice}` → `{id,state:"rendering"}` |
| GET | `/voice-overs/{id}` | session | `{id,state,voice,text,audio_url}` |
| GET | `/voice-overs/{id}/audio` | session | WAV |
| POST | `/clips/{id}/approve` | session | → `{id,state}` |
| POST | `/clips/{id}/post` | session | stub: flips state to `posted`, returns `unproven:"youtube"` |
| GET | `/clips/{id}/download` | session | video/mp4 |
| POST | `/clips/{id}/export` | session | `{title,description,tags}` → `{id,clip_id,state}` |
| GET | `/clips/{id}/export` | session | zip: `short.mp4`, `thumbnail.jpg`, `metadata.json` |
| POST | `/streams` | session | `{title}` → `{id,rtmp_url,stream_key}` |
| GET | `/history` | session | paged history entries |

## Community — `api/app/community.py`

| Method | Path | Role | Notes |
| --- | --- | --- | --- |
| GET | `/m/{slug}` | public | `{slug,card,attempts[]}` |
| GET | `/missions/{id}/leaderboard` | public | paged, ranked ascending by `result_value` |
| GET | `/creators/{user_id}` | public | paged attempts with cards |

## Account — `api/app/account.py`

| Method | Path | Role | Notes |
| --- | --- | --- | --- |
| POST | `/metrics` | session | `{clip_id,views,avg_view_percentage}`; updates mission score |
| GET | `/results` | session | `{clips[],by_type[]}` |
| GET | `/settings` | session | plan, usage, preferences |
| PATCH | `/settings` | session | `{caption_style,layout_preference,voice_over_default,voice}` |
| GET | `/account/export` | session | JSON of the user and assignments |
| DELETE | `/account` | session | deletes rows and storage prefixes |

## Admin — `api/app/admin.py` (router-level `require_admin`)

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/admin/templates` | paged; table is empty (no writer) |
| GET | `/admin/users` | paged, filter `role` |
| PATCH | `/admin/users/{id}` | `{role}` |
| POST | `/admin/users/{id}/reset-link` | → `{url}` (one-time, 60 min) |
| GET | `/admin/invites` | paged |
| POST | `/admin/invites` | `{email?}` → `{id,code,url}` |
| POST | `/admin/invites/{id}/revoke` | → `{id,revoked}` |
| GET | `/admin/jobs` | paged, filter `state`; includes `error` |
| POST | `/admin/jobs/{id}/retry` | → `{id,state:"queued"}` |
| GET | `/admin/audit` | paged audit entries |
| GET | `/admin/ai-usage` | paged tokens/latency/fallback |
| GET | `/admin/ai-config` | `{provider,base_url,model,key_present,configured}` (never the key) |
| GET | `/admin/storage` | `{driver,bytes}` |
| GET | `/admin/setup` | the same checks as `make doctor` |

## AI — `api/app/ai.py`

| Method | Path | Role | Kind |
| --- | --- | --- | --- |
| POST | `/ai/suggest` | session | `suggest` |
| POST | `/ai/mission-editor` | session | `editor` |
| POST | `/ai/clip-review` | session | `clip_review` |
| POST | `/ai/export` | session | `export` |
| GET | `/ai/results-summary` | session | `results_summary` |
| POST | `/ai/pool-review` | session | `pool_review` |
| POST | `/ai/help` | session | `help` (quotes `api/app/help_guide.md`) |
| GET | `/help/guide` | public | `{guide}` |

All return a `fallback` boolean and, when true, a `notice`.

## Tours — `api/app/tours.py`

| Method | Path | Role | Notes |
| --- | --- | --- | --- |
| GET | `/tours` | session | array of progress |
| POST | `/tours/{tour_id}` | session | `{step_index,completed,skipped}` |
| DELETE | `/tours/{tour_id}` | session | reset |

## Relay hooks — `api/app/hooks.py` (CSRF-exempt)

| Method | Path | Role | Notes |
| --- | --- | --- | --- |
| POST | `/hooks/relay/auth` | shared secret + stream key | MediaMTX publish auth |
| POST | `/hooks/relay/segment` | shared secret + stream key | registers an fMP4 segment |
| GET | `/streams/{id}/status` | session | `{connected,paths}` from the relay API |
