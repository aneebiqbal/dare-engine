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
| Local open-weight models (Ollama: Qwen / Kimi, Metal) | yes | yes | yes (host, no cloud) | — |
| OBS live view (obs-websocket 5.x: connection, stream, record, scene, mic) | yes | yes | yes (real OBS 33.0.1) | — |
| SSD import (host bridge → list → local import → detect job) | yes | yes | yes (mounted DMG) | — |
| MLX Whisper transcription (host bridge, Metal) | yes | yes | yes (host, 30.17 s / 4.9 min) | — |
| Visual-strikingness cold-open check | yes | yes | yes (trailer) | real gameplay fixture |
| Karaoke word-by-word captions | yes | yes | yes (unit + render) | — |
| Models admin page (Ollama/MLX inventory, pull, unload, memory) | yes | yes | yes (real bridge) | — |
| Memory discipline (unload + idle watchdog) | yes | yes | yes (unit + bridge) | — |
| Originality/commentary step | yes | yes | yes (API) | — |
| Posting calendar + cadence guardrail | yes | yes | partial (no YouTube API) | YouTube API key |
| Leading indicators + research-ranking score | yes | yes | yes (unit) | YouTube collector |
| Long-form builder | yes | yes | partial (no real session clips) | real gameplay fixture |
| Launch docs (README, licences, launch plan) | yes | yes | yes | history purge decision |
| START_HERE run guide | yes | yes | yes | — |
| Grouped admin/gamer nav (core flow only) | yes | yes | yes | — |
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
| Cloud web deploy (`docs/deploy-web.md`) | yes | yes (compose + Caddy) | no | a host + domain |
| Rate limiting (per-IP, stricter auth/admin) | yes | yes | yes (unit) | — |
| Client error reporting + admin view | yes | yes | yes (unit) | — |
| Database backup (`make backup`) | yes | yes | no | a real restore drill |
| Desktop app (Tauri shell, builds a .dmg) | yes | yes (build + mount) | partial (no human launch) | a human at a Mac |
| Desktop capture (OBS path) | yes | yes | yes (OBS 33.0.1) | — |
| Desktop capture (bundled FFmpeg recorder) | yes | yes (command) | no | a real recording |
| Vision clip suggestions (sampled VLM) | yes | yes | yes (real run, 4-min trailer) | owner's gameplay footage |
| Models & Setup suggested engine + one-click install | yes | yes | yes (real bridge) | — |
| Projects: derived stages, dashboard, sequential analysis queue | yes | yes | yes (acceptance, real stack) | — |
| First-run setup wizard (persisted, verified steps) | yes | yes | yes (acceptance, real endpoints) | — |
| In-window caption editor (text/timing, no re-transcribe) | yes | yes | yes (acceptance, real render) | — |
| Engine activity log (model load/unload, cleanup) on the dashboard | yes | yes | yes (acceptance, real worker) | — |
| Automatic upload-to-Shorts pipeline (scan→rank→vision→cut→transcribe→render) | yes | yes | partial (45 s stand-in, 4.9 min trailer, 2 h synthetic stress test; no owner gameplay) | owner's footage for quality + real 2 h audio |
| Converging ETA + live per-stage progress + clips appearing one by one | yes | yes | yes (acceptance, real API; 2 h run estimate 1181 s vs 1181.9 s actual) | — |
| One model resident at a time (shared advisory lock, unload verified) | yes | yes | yes (unit + real bridge memory readout) | — |
| Resume from the last completed stage after a kill/pause | yes | yes | yes (acceptance) | — |
| User timestamps added without replacing AI suggestions | yes | yes | yes (acceptance) | — |

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
4. **A host and a domain for the cloud website.** `docs/deploy-web.md` reproduces
   the deployment; the owner must supply the VPS/domain and the managed database.
5. **A git remote with a safe credential.** The token embedded in `origin` was
   removed from the remote URL; revoke it on GitHub and choose the real remote
   (the current one points at `dare-engine`). See `docs/launch.md`.
6. **Real 2 h gameplay footage.** The automatic pipeline is built and measured
   on a 45 s stand-in and the 4.9 min trailer with the real VLM and MLX Whisper;
   only the owner's own long recording proves the 2 h timing budget and clip
   quality.
