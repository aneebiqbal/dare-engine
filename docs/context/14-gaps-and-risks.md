# 14 — Gaps and risks

Updated after Sprint 1. The five foundation blockers (F1–F5 below) are closed in
code with tests; the remaining gaps are listed at the end.

## Licence and compliance

- **Voice-over is now an optional add-on.** `piper-tts` is GPL-3.0-or-later and
  is no longer in `worker/requirements.txt`. It lives in
  `worker/requirements-voice.txt` and `make voice` installs it into the running
  worker. `tests/licence_check.py` (run by `make check` and CI) fails if a
  GPL/AGPL package appears in the core requirements. See 13.
- FFmpeg may be a GPL build; `docs/decisions.md` flags it for legal review.

## Security (F3 — closed)

- Upload chunk routes (`POST /uploads/start`, `GET /uploads/{id}`,
  `PUT /uploads/{id}/chunks/{index}`) require a session.
- Sessions store `HMAC-SHA256(SESSION_SECRET, token)`; a database dump no
  longer yields usable cookies. `SESSION_SECRET` is actually used.
- Login rate limiting counts per email **and** per IP (failed attempts only).
- Changing a user's role away from admin deletes their sessions immediately.

## Data and cleanup (F2 — closed)

- Upload staging is deleted after assembly; download/export/preview temp files
  are removed after the response.
- `retention.sweep()` runs on startup and from `make cleanup` /
  `POST /admin/cleanup`: raw recordings older than `recording_retention_days`
  (default 7) are deleted once their clips are ready; old voice-over previews
  are deleted too.
- `DELETE /account` also removes voice-over previews.
- Tests: staging gone after assembly; a past-retention recording removed while
  its clip remains; a deleted account leaves no files.

## Dead and misleading code (F5 — closed)

- `api/app/schema.sql` and `api/app/llm/gemini.py` are removed.
- `worker/clip/transcribe.py` reads `settings.whisper_*`; `worker/clip/llm.py`
  uses the shared client and `settings.llm_*`.
- `README.md` matches reality (ports 3100/8000/8001/19997, local storage,
  `make doctor`/`make accept`).

## AI in the worker (F1 — closed)

- `shared/llm.py` is the one OpenAI-compatible client, copied into both images.
  The API and the worker use it; the worker falls back to word density when
  `LLM_PROVIDER` is not `openai` or no key is set. Usage is logged to
  `ai_usage`. The legacy Gemini path is gone.

## Remaining gaps

- **No real gameplay fixture.** `fixtures/` is empty; M1/M2 are not accepted.
- **No live AI run.** The supplied key authenticates but the account has no
  usable balance/quota (HTTP 402/429), so every AI feature falls back. Top up
  the OpenCode Models balance to prove M4.
- **No Git remote** (`git remote -v` empty), so no pull request.
- S3 storage, Google sign-in, YouTube posting, payments and the question miner
  are absent or stubs.
- `POST /clips/{id}/post` only flips state and returns `unproven: "youtube"`.
- Web performance budgets in `docs/performance.md` are unmeasured.
- No TLS termination, backups, structured logging or error reporting.
- The relay control API is published on host port 19997 with no auth.
