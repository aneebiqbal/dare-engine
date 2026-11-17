# 14 — Gaps and risks

## Licence and compliance

- **`piper-tts` 1.8.0 is GPL-3.0-or-later**, while `docs/decisions.md` says
  "Piper is MIT". The old MIT `rhasspy/piper` is archived. This conflicts with
  the BUILD_PROMPT hard rule against GPL code in the app. See 13.
- FFmpeg may be a GPL build; `docs/decisions.md` flags it for legal review.
- `README.md` still advertises "S3 storage http://localhost:9100" and the old
  mock-storage port. The default run has no S3 container.

## Unproven / missing

- No managed database URL, no live AI key, no real gameplay fixture
  (`fixtures/` is empty). M1/M3/M4 are not accepted.
- S3 storage, Google sign-in, YouTube posting, payments and the question miner
  are absent or stubs.
- `POST /clips/{id}/post` is exposed and returns `unproven: "youtube"` but only
  flips a column.
- Web performance budgets in `docs/performance.md` are unmeasured.
- Design rounds 2 and 3 are not done.

## Dead / misleading code

- `api/app/schema.sql` is the old Sprint-5 schema. `db.migrate()` now reads
  `api/app/migrations/`; `schema.sql` is never applied.
- `api/app/llm/gemini.py` is unreachable; `get_llm()` never selects it.
- `worker/clip/llm.py` is a legacy Gemini client that reads `GEMINI_API_KEY`
  from the environment, ignores the new `LLM_*` worker config, does no schema
  validation or retry, and is not logged to `ai_usage`.
- `worker/app/config.py` declares `llm_*` fields that nothing reads, and
  `whisper_*` fields that `worker/clip/transcribe.py` bypasses (it reads
  `WHISPER_*` from `os.environ`).
- `web/lib/api-types.ts` is generated from the contract but unused; the UI uses
  the hand-written `web/lib/types.ts`.
- `channels`, `oauth_tokens`, `daily_sets`, `templates` have no writer; the
  Templates page is always empty, `missions.type` is never set.
- `login_attempts.ip` is never written.

## Data and cleanup

- **No retention or lifecycle.** Recordings, clips, relay segments and
  voice-over previews are never deleted except by `DELETE /account`.
- `DELETE /account` removes `recordings/{user_id}/` and `clips/{clip_id}/` but
  **not** `voice-overs/{id}/preview.wav`, so previews leak after deletion.
- The upload chunk endpoints are unauthenticated; the `upload_id` is a capability.
- Upload staging (`/tmp/clipdesk-uploads/{upload_id}/*.part` and the assembled
  copy) is never deleted, and lives in the API container's `/tmp`; a restart
  loses it, so an interrupted upload cannot resume across a restart.
- Download/export temp dirs (`tempfile.mkdtemp()`) are never removed.
- No size limit on uploads; an 8-hour 30 GB recording needs ~65 GB and three
  copies at once (see 09).

## Security weaknesses

See `07-auth-and-security.md#known-weaknesses`. The most important: the session
token is stored in plaintext and `SESSION_SECRET` is unused; rate limiting is
per email only; role changes do not invalidate sessions; the relay shared
secret is optional; the admin reset URL is returned in the API; the upload chunk
endpoints are unauthenticated (`upload_id` is the only capability).

## Operations

- No TLS termination (no Caddy in compose), no backups, no structured logging,
  no error reporting, no dependency/secret scanning in CI (CI runs only
  `make accept` and `make check`).
- `make test` runs every test including the long acceptance suite.
- The relay control API is published on host port 19997 with no auth
  (`authHTTPExclude: action: api`).

## Things a new engineer would be surprised by

- The job worker uses the **direct** database URL; the API uses the pooled one
  (`api/app/db.py`, `worker/app/db.py`).
- The API refuses to start if `DEV_AUTH_ENABLED=true` and `APP_ENV=production`.
- The web app talks to the API through a same-origin proxy, and the proxy had to
  forward the whole `Cookie` header for CSRF to work.
- `make accept` sets `DEV_AUTH_ENABLED=true`; a plain `docker compose up` has it
  off, so the dev sign-in buttons disappear.
- The first-visit hint for `/` originally matched every path; it now matches
  `/` exactly.
- `tests/fixtures/standin_speech_45s.mp4` is a synthetic test pattern with
  recorded speech, not gameplay.
