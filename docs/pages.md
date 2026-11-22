# Pages — why each exists

One row per route in the product nav. Supporting pages that stay reachable by
URL but are off the nav are listed separately at the bottom. Every kept page
reads real data; the only mocked data is behind `NEXT_PUBLIC_API_MOCK=1`, which
app code may not import (`make check`).

## Gamer nav (Play / Review / Account)

| Route | Why it exists | User does |
| --- | --- | --- |
| `/` | Dashboard: today's assigned dares and the one next action. | Opens Today or the next dare. |
| `/today` | The daily dare plus three picks. | Accepts or swaps a dare. |
| `/missions/[id]` | Idea detail and dare editor. | Reads what to do, edits hook/setup/win condition. |
| `/live` | OBS / Go Live: stream address, key, connection status, checklist. | Connects OBS and checks HDCP, mic, radio. |
| `/remote` | Phone remote. | Taps Start and Done; the clip window is stored. |
| `/clips`, `/clips/[id]`, `/export/[id]` | Clip review and export, including the caption editor. | Watches, retitles, restyles, edits caption text/timing, adds commentary, exports a zip. |
| `/history` | Session history with search. | Finds a past session and its result. |
| `/results` | Metrics and summary. | Reads views, swipe-through, saves/shares per dare type. |
| `/settings` | Caption style, layout, voice-over defaults. | Sets preferences. |

## Admin nav (Plan / Create / Manage)

| Route | Why it exists | User does |
| --- | --- | --- |
| `/admin` | Overview: system health, jobs, AI usage. | Triages the platform. |
| `/admin/games` | Games grid. | Adds a game, enables/disables it, runs research. |
| `/admin/games/[id]` | Game profile. | Reviews today's sourced ideas, approves/rejects/assigns, sees runs. |
| `/admin/pool` | Idea pool. | Types questions, approves/rejects/assigns. |
| `/admin/studio` | Clip studio. | Imports a recording, finds moments, generates clips. |
| `/admin/projects` | Projects: each stream's stage and the analysis queue. | Creates a project, attaches a recording, queues analysis, tracks stages. |
| `/admin/calendar` | Posting calendar queue. | Schedules approved Shorts and marks them published. |
| `/admin/long-form` | Long-form builder. | Assembles a session's Shorts into one video. |
| `/admin/models` | Local models and provider. | Pulls/unloads Ollama models, reads MLX and memory. |
| `/admin/wizard` | First-run setup wizard. | Verifies the SSD, OBS, models and provider, one step at a time. |
| `/admin/setup` | Setup status (same checks as `make doctor`). | Confirms every key and connection. |
| `/admin/users`, `/admin/invites` | Gamer management. | Changes roles, issues invites and reset links. |

## Shared

| Route | Why it exists | User does |
| --- | --- | --- |
| `/signin` | The only way in. | Signs in with email + password. |
| `/signup` | Invite-only account creation. | Redeems an invite code and sets a password. |
| `/reset` | Admin-issued password reset. | Sets a new password from a signed link. |
| `/terms`, `/privacy` | Legal pages linked from sign-up. | Reads the terms. |

## Supporting — reachable by URL, off the nav

| Route | Why it stays |
| --- | --- |
| `/styleguide` | Design-system preview for the team. |
| `/admin/templates` | Clip template and caption-style editor. |
| `/admin/jobs` | Job queue and retry. |
| `/admin/ai` | AI usage and provider config. |
| `/admin/audit` | Audit log. |
| `/welcome`, `/leaderboard`, `/m/[slug]`, `/creators/[id]` | Public community pages. |
| `/help` | In-app guide. |

## Trimmed

The nav lists only the core flow above. The supporting pages remain reachable by
URL (the styleguide is explicitly kept for the team) but are out of the product
nav. Render scratch was moved to `trash/`; see `trash/README.txt`.

