# 06 — Web app

Next.js 15 App Router (`web/app`), TypeScript, Tailwind, Geist font. Server
components load data through `web/lib/api.ts` (`API_URL` → the API, session
cookie forwarded); client components call the same API through the same-origin
proxy `web/app/api/[...path]/route.ts` (so the cookie stays on the web origin).
The proxy forwards the whole `Cookie` header, `Content-Type`, `X-CSRF-Token`,
and the raw request/response body (binary-safe).

Two page wrappers:

- `web/components/page.tsx` (`Page`) — public pages, simple centred header + nav.
- `web/components/app-page.tsx` (`AppPage`) → `web/components/shell.tsx`
  (`AppShell`) — authenticated pages: collapsible sidebar, sticky top bar with
  search and account menu, full-width content up to `1600px`, theme toggle,
  replay-tour button, first-visit hint.

`web/lib/server.ts` provides `getMe`, `requireUser` (redirects to `/signin`)
and `requireAdmin` (redirects to `/`).

## Pages

| URL | Role | Component | Shows | Main API calls |
| --- | --- | --- | --- | --- |
| `/` | session | `dashboard.tsx` | stats, today's missions, next step, first-steps checklist | `/today`, `/clips`, `/history`, `/results` |
| `/today` | session | `today.tsx` | Daily Mission + picks, accept, AI suggestions | `/today`, `/assignments`, `/ai/suggest` |
| `/missions/[id]` | session | `mission-editor.tsx` | question, hook, setup, win condition, titles; AI rewrite/spoiler check | `/missions/{id}`, `PATCH /missions/{id}`, `/ai/mission-editor` |
| `/live` | session | `live.tsx` | stream address + masked key, reveal/copy, relay status | `POST /streams`, `/streams/{id}/status` |
| `/remote` | session | `remote.tsx` (standalone phone layout) | mission, Start/Done, result dialog, offline queue | `/assignments`, `/marks` |
| `/clips` | session | `clips.tsx` | upload form (chunked), clip grid with stage/progress | `/clips`, `/uploads/*`, `/today` |
| `/clips/[id]` | session | `clip-review.tsx` | preview, title/description/tags, trim, layout, captions, voice-over, AI review, export | `/clips/{id}`, `PATCH /clips/{id}`, `/trim`, `/voice-over`, `/voice-preview`, `/ai/clip-review`, `/ai/export`, `/clips/{id}/export` |
| `/export/[id]` | session | `export-package.tsx` | package metadata, AI titles, download | `/clips/{id}`, `/ai/export`, `/clips/{id}/export` |
| `/results` | session | `results.tsx` | totals, AI summary, per-clip and per-type tables | `/results`, `/ai/results-summary` |
| `/history` | session | `history.tsx` | mission history table | `/history` |
| `/settings` | session | `settings.tsx` | account, preferences, password, data export, delete | `/settings`, `PATCH /settings`, `/account/export`, `DELETE /account` |
| `/help` | session | `help.tsx` | guide text, "how do I" AI, replay tour | `/help/guide`, `/ai/help` |
| `/admin` | admin | `admin.tsx` `AdminOverview` | users/invites/jobs/pool/AI/storage/setup stats, recent jobs + AI | many `/admin/*` |
| `/admin/users` | admin | `AdminUsers` | users, role change, reset links | `/admin/users`, `PATCH /admin/users/{id}`, `/admin/users/{id}/reset-link` |
| `/admin/invites` | admin | `AdminInvites` | create/revoke invites | `/admin/invites` |
| `/admin/pool` | admin | `AdminPool` | type questions, write cards, AI pool review, approve/reject | `/admin/questions`, `/admin/pool`, `/ai/pool-review` |
| `/admin/templates` | admin | `AdminTemplates` | template table (always empty) | `/admin/templates` |
| `/admin/studio` | admin | `studio.tsx` `Studio` | upload a recording, Find moments, ranked candidates with score + reason, accept/trim/reject, generate, inline preview, swap template/captions, live compute path + system load | `/studio/upload`, `/studio/detect`, `/studio/recordings/{id}`, `/studio/generate`, `/studio/templates`, `/studio/system` |
| `/admin/jobs` | admin | `AdminJobs` | job queue with errors and retry | `/admin/jobs`, `/admin/jobs/{id}/retry` |
| `/admin/ai` | admin | `AdminAi` | provider/model/key presence, usage table | `/admin/ai-config`, `/admin/ai-usage` |
| `/admin/audit` | admin | `AdminAudit` | audit log | `/admin/audit` |
| `/admin/setup` | admin | `AdminSetup` | the same checks as `make doctor` | `/admin/setup`, `/admin/ai-config`, `/admin/storage` |
| `/welcome` | public | `app/welcome/page.tsx` | landing page, Daily Mission preview | `/today` (fails silently for anonymous) |
| `/signin` | public | `signin.tsx` | email/password + dev buttons | `/auth/csrf`, `/auth/sign-in`, `/auth/dev/sign-in` |
| `/signup` | public | `signup.tsx` | invite code, email, name, password | `/auth/sign-up` |
| `/reset` | public | `reset.tsx` | one-time token + new password | `/auth/reset-password` |
| `/terms`, `/privacy` | public | static | draft legal text | — |
| `/m/[slug]` | public | `app/m/[slug]/page.tsx` | public mission + attempts | `/m/{slug}` |
| `/leaderboard` | public | `app/leaderboard/page.tsx` | ranked attempts (hardcoded `m_0214`) | `/missions/m_0214/leaderboard` |
| `/creators/[id]` | public | `app/creators/[id]/page.tsx` | static placeholder | — |
| `/styleguide` | public | `app/styleguide/page.tsx` | component gallery in both themes | `/health` |

Every data page uses `PageState` (`web/components/ui.tsx`) for loading, error,
empty and filled states. Forms show inline errors and toasts.

## Shared components (`web/components/`)

| Component | Used by |
| --- | --- |
| `ui.tsx` — Button, Input, Textarea, Field, Card, Badge, Eyebrow, Tabs, Dialog, Toast, Table, Tr, Td, EmptyState, Skeleton, PageState, Select, Progress, Notice, Stat | everywhere |
| `shell.tsx` — `AppShell`, `ShellHeader`, `RoleBadge` | all `AppPage` pages |
| `page.tsx` — `Page`, `Nav` | public pages |
| `icons.tsx` — 1.5 px stroke line icons | shell nav, top bar |
| `tour.tsx` — `Tour`, `replayTour` | shell, Help |
| `first-visit-hint.tsx` | `AppPage` |
| `theme.tsx`, `theme-script.tsx` | light/dark |
| `status-badge.tsx` | styleguide |
| `nav.tsx` | `Page` |

## Design tokens

`web/app/globals.css` defines light (warm cream) and dark (OLED) custom
properties: `--bg`, `--surface`, `--surface-2`, `--border`, `--text`,
`--muted`, `--accent`, `--danger`, `--success`, radius, spacing, `--ease`
(`cubic-bezier(0.22,1,0.36,1)`), ambient shadow. `web/tailwind.config.ts` maps
them to Tailwind colours/radius/spacing/shadow. Cards use a double bezel
(`rounded-lg` shell + inner core). Direction is in `docs/design.md`.

## Tours and hints

- `web/data/tours.json` — `creator` (6 steps) and `admin` (5 steps), each step a
  `selector` (`data-tour=…`), title and body. Edited without code changes.
- `web/components/tour.tsx` — anchored tooltip, accent ring, keyboard only
  (`→`/`Enter` next, `←` back, `Esc` skip), saves `step_index`/`completed`/
  `skipped` through `POST /tours/{tour_id}`. The shell auto-opens the role tour
  on first sign-in unless finished or skipped.
- `web/data/hints.json` — one first-visit hint per path prefix; dismissed in
  `localStorage` (`web/components/first-visit-hint.tsx`).

## Mock layer

`web/lib/mock.ts` is imported only by `web/lib/api.ts` when
`NEXT_PUBLIC_API_MOCK=1` (used by `make screens`). `tests/unit/test_no_mock.py`
fails if any other file imports it. The default run and all tests use mock off.
