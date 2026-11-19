# Pages — why each exists

One row per route. "Target" maps the page to the master build prompt's target
set. Every kept page reads real data; the only mocked data is behind
`NEXT_PUBLIC_API_MOCK=1`, which app code may not import (`make check`).

## Shared / public

| Route | Why it exists | User does | Target |
| --- | --- | --- | --- |
| `/signin` | The only way in. | Signs in with email + password (dev sign-in in tests). | Sign-in |
| `/signup` | Invite-only account creation. | Redeems an invite code and sets a password. | Sign-in |
| `/reset` | Admin-issued password reset. | Sets a new password from a signed link. | Sign-in |
| `/welcome` | Public landing, linked as "Home" on every public page. | Reads the pitch, goes to sign-in or the leaderboard. | Public |
| `/terms`, `/privacy` | Legal pages linked from sign-up. | Reads the terms. | Public |
| `/leaderboard` | Public daily board. | Sees ranked attempts on the daily dare. | Public |
| `/m/[slug]` | Public dare page. | Reads the dare and its ranked attempts. | Public |
| `/creators/[id]` | Public creator profile. | Sees a creator's attempts per dare. | Public |
| `/styleguide` | Design-system preview for the team, not a user page. | Inspects every component in both themes. | Internal |

## Gamer / creator

| Route | Why it exists | User does | Target |
| --- | --- | --- | --- |
| `/` | Dashboard: today's assigned dares and the one next action. | Opens Today or the next dare. | Dashboard |
| `/today` | The daily dare plus three picks. | Accepts or swaps a dare. | Dashboard / idea |
| `/missions/[id]` | Idea detail and dare editor. | Reads what to do, edits hook/setup/win condition. | Idea detail |
| `/live` | OBS / Go Live: stream address, key, connection status, checklist. | Connects OBS and checks HDCP, mic, radio. | OBS/Go-Live |
| `/remote` | Phone remote. | Taps Start and Done; the clip window is stored. | OBS/Go-Live |
| `/clips`, `/clips/[id]`, `/export/[id]` | Clip review and export. | Watches, retitles, restyles, exports a zip. | Clip studio |
| `/results` | Metrics and AI summary. | Reads views/retention per dare type. | Session history |
| `/history` | Session history with search. | Finds a past session and its result. | Session history |
| `/settings` | Caption style, layout, voice-over defaults. | Sets preferences. | Settings |
| `/help` | Guide and AI help. | Reads the guide, asks a question. | Settings |

## Admin

| Route | Why it exists | User does | Target |
| --- | --- | --- | --- |
| `/admin` | Overview: system health, jobs, AI usage. | Triages the platform. | Setup status |
| `/admin/users` | Gamer management. | Changes roles, issues reset links. | Gamer management |
| `/admin/invites` | Invite codes. | Creates and revokes invites. | Gamer management |
| `/admin/pool` | Idea pool: type questions, approve/reject/assign. | Runs the approval queue. | Game profile |
| `/admin/studio` | Clip studio: upload, find moments, generate. | Cuts clips from a recording. | Clip studio |
| `/admin/templates` | Clip templates and caption styles. | Picks the render grammar. | Clip studio |
| `/admin/jobs` | Job queue. | Retries failed jobs. | Setup status |
| `/admin/ai` | AI usage and provider config. | Checks tokens, latency, fallback. | Setup status |
| `/admin/audit` | Audit log. | Reviews admin actions. | Setup status |
| `/admin/setup` | Setup status (same checks as `make doctor`). | Confirms every key and connection. | Setup status |

## Added with the research brain

| Route | Why it exists | User does | Target |
| --- | --- | --- | --- |
| `/admin/games` | Games grid. | Adds a game from RAWG, enables/disables it, runs research. | Games grid |
| `/admin/games/[id]` | Game profile. | Reviews today's sourced ideas, approves/rejects/assigns, sees runs. | Game profile |

The idea pool (`/admin/pool`) now filters by game and shows each idea's real
sources; the dare editor (`/missions/[id]`) shows them too.

## Trimmed

No page was deleted: every route above has a real user and real data. The
legacy `web/components/nav.tsx` "Home" link points at `/welcome`, which is the
public landing, so `/welcome` stays.
