# 03 — Configuration

All values come from environment variables. Sources: `api/app/config.py`,
`worker/worker_app/config.py`, `docker-compose.yml`, `.env.example`. No `.env` is
committed (`ls .env` → absent). `docs/SETUP_KEYS.md` explains how to create each
secret.

## API (`api/app/config.py`)

| Variable | Purpose | Required | Default | Read by |
| --- | --- | --- | --- | --- |
| `DATABASE_URL` | pooled connection for request handlers | yes in production | `postgresql://clipdesk:clipdesk@db:5432/clipdesk` | `db.connect()` |
| `DATABASE_URL_DIRECT` | direct connection for migrations | no (falls back to `DATABASE_URL`) | `""` | `db.migrate()` |
| `SESSION_SECRET` | secret for the session configuration | yes in production | `change-me` | `config.settings` (not yet used to sign tokens — see 07) |
| `COOKIE_SECURE` | force `Secure` on cookies | no | `false` (`true` when `APP_ENV=production`) | `auth.py` |
| `APP_ENV` | `development` / `production` | no | `development` | `main.py` (dev-auth guard), `config.cookies_secure` |
| `WEB_ORIGIN` | origin for reset/invite links and CORS | yes | `http://localhost:3100` | `admin.py`, `main.py` |
| `INVITE_REQUIRED` | invite-only sign-up | no | `true` | `auth.py` |
| `DEV_AUTH_ENABLED` | test-only dev sign-in | no | `false` | `auth.py`, `main.py` |
| `STORAGE_DRIVER` | `local` or `s3` | no | `local` | `storage.py` |
| `STORAGE_LOCAL_DIR` | local storage root | no | `/data/storage` | `storage.py` |
| `S3_ENDPOINT` | S3 endpoint URL | s3 only | `http://storage:9090` | `storage.py` |
| `S3_BUCKET` | bucket name | s3 only | `clipdesk` | `storage.py` |
| `S3_ACCESS_KEY` | access key | s3 only | `clipdesk` | `storage.py` |
| `S3_SECRET_KEY` | secret key | s3 only | `clipdesk-dev-secret` | `storage.py` |
| `S3_REGION` | region | no | `us-east-1` | `storage.py` |
| `LLM_PROVIDER` | `openai` / `recorded` / `stub` | no | `recorded` (compose) | `llm/__init__.py` |
| `LLM_BASE_URL` | OpenAI-compatible base URL | `openai` only | `https://opencode.ai/zen/v1` | `llm/openai_compat.py` |
| `LLM_API_KEY` | provider key | `openai` only | `""` (never printed) | `llm/openai_compat.py` |
| `LLM_MODEL` | model id | `openai` only | `""` | `llm/openai_compat.py` |
| `LLM_RECORDED_RESPONSE` | recorded response file | `recorded` only | `/app/app/llm_recorded.json` | `llm/recorded.py` |
| `LLM_TIMEOUT` | provider timeout seconds | no | `60` | `llm/openai_compat.py` |
| `TTS_COMMAND` | TTS executable | no | `piper` | `doctor.py` (worker owns TTS) |
| `TTS_VOICE` | Piper voice id | no | `en_US-amy-medium` | `doctor.py` |
| `TTS_MODEL_DIR` | voice model directory | no | `/data/voices` | `doctor.py` |
| `UPLOAD_TMP_DIR` | chunk staging directory | no | `/tmp/clipdesk-uploads` | `clips.py` |
| `RELAY_HOOK_SECRET` | shared secret for relay hooks | no | `""` (check disabled) | `hooks.py` |

Cookie names are fixed: `clipdesk_session` (HttpOnly) and `clipdesk_csrf`
(`api/app/config.py`).

## Worker (`worker/worker_app/config.py`)

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | fallback connection | local Postgres |
| `DATABASE_URL_DIRECT` | the worker always uses the direct URL | falls back to `DATABASE_URL` |
| `STORAGE_DRIVER`, `STORAGE_LOCAL_DIR`, `S3_*` | same as the API | same |
| `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_TIMEOUT` | declared but **not used** by `worker/clip/llm.py` (see 14) | `stub` / empty |
| `TTS_COMMAND`, `TTS_VOICE`, `TTS_MODEL_DIR` | Piper | `piper` / `en_US-amy-medium` / `/data/voices` |
| `WHISPER_MODEL` | faster-whisper model | `small` |
| `WHISPER_DEVICE` | `cpu` / `cuda` | `cpu` |
| `WHISPER_COMPUTE_TYPE` | int8 etc. | `int8` |
| `WORKER_CONCURRENCY` | render threads | `4` (compose); code falls back to CPU count |
| `WORKER_STALE_SECONDS` | stale-job reaper threshold | `600` |

`WHISPER_*`, `WORKER_CONCURRENCY` and `WORKER_STALE_SECONDS` are read straight
from `os.environ` in `worker/clip/transcribe.py` and `worker/worker_app/worker.py`, not
from `worker/worker_app/config.py`.

## Database (`db` service)

| Variable | Purpose | Default |
| --- | --- | --- |
| `POSTGRES_USER` | database user | `clipdesk` |
| `POSTGRES_PASSWORD` | database password | `clipdesk` |
| `POSTGRES_DB` | database name | `clipdesk` |

## Relay

| Variable | Purpose | Default |
| --- | --- | --- |
| `RELAY_HOOK_SECRET` | sent as `X-Relay-Secret` by the segment hook curl | `""` |

## Web (`web/Dockerfile`, `web/app/api/[...path]/route.ts`)

| Variable | Purpose | Default |
| --- | --- | --- |
| `API_URL` | server-side proxy target | `http://api:8000` |
| `NEXT_PUBLIC_API_URL` | browser API base (unused by the proxy path) | `http://localhost:8000` |
| `NEXT_PUBLIC_API_MOCK` | `1` uses `web/lib/mock.ts` | `0` |
| `NEXT_PUBLIC_DEV_AUTH` | `1` shows the dev sign-in buttons | `0` |
| `HOSTNAME` | compose sets `0.0.0.0` for the health probe | — |

## Feature flags and defaults

| Flag | Default | State |
| --- | --- | --- |
| `DEV_AUTH_ENABLED` | `false` | test-only route; production guard in `main.py` |
| `NEXT_PUBLIC_API_MOCK` | `0` | screenshots only |
| `INVITE_REQUIRED` | `true` | invite-only on |
| `STORAGE_DRIVER` | `local` | S3 off |
| `LLM_PROVIDER` | `recorded` | live `openai` off (no key) |
| publishing (`POST /clips/{id}/post`) | on but a stub | flips state only |
| Google sign-in | absent | no route |
| billing | absent | `plan` hardcoded `free` |
| question miner | absent | no job/route |
