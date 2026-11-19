# Build state

One row per major feature. "Proven on real inputs" means it ran against the
managed Neon database and a real recording, not only the synthetic stand-in.
Last updated after the research-brain sprint.

| Feature | Built | Tested locally | Proven on real inputs | Blocked on user |
| --- | --- | --- | --- | --- |
| Accounts, sessions (hashed), CSRF, roles, invites, lockout, reset | yes | yes | yes (Neon) | — |
| Managed PostgreSQL (Neon, pooled + direct) | yes | yes | yes | — |
| Migrations on an empty database | yes | yes | yes | — |
| Job queue, backoff, errors, stale recovery | yes | yes | yes | — |
| Games: admin grid, RAWG search, profile, enable/disable | yes | yes | yes (recorded RAWG fallback) | RAWG key for live search |
| Research brain: YouTube + Reddit + news → sourced ideas | yes | yes | partial (sample feed, recorded AI) | source keys + AI credit |
| Idea accuracy: citations stored and shown, schema-validated | yes | yes | yes (sample feed) | live sources |
| Admin approval gate + assign + gamer Today | yes | yes | yes (real accounts) | — |
| Generated idea card image (SVG, no remote image) | yes | yes | yes | — |
| Mission cards from typed questions (AI) | yes | yes (recorded provider) | no | AI key credit |
| Live AI on every page | yes (one client) | stub/recorded only | no | AI key credit |
| Upload → render → 9:16 Short | yes | yes (stand-in) | partial (trailer, not gameplay) | real gameplay fixture |
| Automatic moment detection + clip grammar | yes | yes (stand-in + trailer) | partial (trailer) | real gameplay fixture |
| Admin clip studio (`/admin/studio`) | yes | yes | partial (trailer) | real gameplay fixture |
| Community: daily dare, leaderboard, public pages | yes | yes | yes (real attempts) | — |
| Results and manual metrics | yes | yes | yes (manual entry) | YouTube API key (collector) |
| Admin portal (users, invites, pool, jobs, AI usage, audit, setup) | yes | yes | yes | — |
| Creator ↔ admin handoff and role boundary | yes | yes | yes | — |
| Web app, all pages, light/dark, phone/desktop | yes | yes (Playwright + axe) | yes | — |
| Performance budgets | yes | yes (`make budgets`) | yes (Neon round trip ~670 ms) | — |
| Voice-over (Piper) | yes | yes (2 tests) | no | GPL add-on install (`make voice`) |
| S3 storage | yes | no | no | S3 credentials |
| Publishing to YouTube/TikTok/Instagram | stub only | no | no | out of scope |
| Google sign-in | no | no | no | OAuth client |
| Billing | no | no | no | payment keys |

## Blocked on the user (cannot be closed by code)

1. **The user's own gameplay recording with commentary.** The only thing that
   makes the clip-quality verdict meetable. Until then the detector and grammar
   are validated on a publisher trailer and a synthetic stand-in.
2. **Credit on the AI key.** The account returns 402/429, so every AI path runs
   on the recorded provider. The client, schema validation, retry and fallback
   are tested; the live call is not.
3. **Research source keys.** `YOUTUBE_API_KEY` and the Reddit app (or RAWG for
   live game search). Without them the brain runs on the saved sample feed and
   flags the run as a fallback.
4. **A git remote with a safe credential.** `origin` exists but its URL embeds a
   GitHub token; rotate it and use a credential helper before pushing.
