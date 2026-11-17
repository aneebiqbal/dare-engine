# 02 — Services and how to run

## Docker Compose services

Source: `docker-compose.yml`.

| Service | Image | Host port | Container port | Volumes | Depends on | Health check |
| --- | --- | --- | --- | --- | --- | --- |
| `db` | `postgres:16-alpine` | — | 5432 | `pgdata` | — | `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB` |
| `api` | built from `api/Dockerfile` | 8000 | 8000 | `storage-data:/data/storage`, `voices:/data/voices` | `db` (healthy) | `GET /healthz/ready` == 200 |
| `worker` | built from `worker/Dockerfile` | 8001 | 8001 | `relayrecordings:/recordings:ro`, `storage-data:/data/storage`, `voices:/data/voices` | `db` (healthy) | `GET /healthz` == 200 |
| `web` | built from `web/Dockerfile` | 3100 | 3000 | — | `api` (healthy) | `GET /api/health` ok |
| `relay` | built from `relay/Dockerfile` (MediaMTX) | 1935 (RTMP), 8554 (RTSP), 19997 (API) | 1935, 8554, 9997 | `./relay/mediamtx.yml:/mediamtx.yml:ro`, `relayrecordings:/recordings` | — | `curl -f http://127.0.0.1:9997/v3/paths/list` |

Named volumes: `pgdata`, `storage-data` (local storage driver), `voices` (Piper
models), `relayrecordings` (fMP4 segments; read-only in the worker).

**Default run starts:** db, api, worker, web, relay. There is **no S3 mock
container** in the default run; storage is local disk. The previous
`adobe/s3mock` service was removed.

## `make` targets

Source: `Makefile`.

| Target | What it does |
| --- | --- |
| `up` | `docker compose up -d --wait --build` |
| `down` | `docker compose down` |
| `logs` | `docker compose logs --tail=100 -f` |
| `accept` | brings the stack up with `DEV_AUTH_ENABLED=true NEXT_PUBLIC_DEV_AUTH=1`, runs `pytest tests/acceptance --ignore=test_web_pages.py -v` |
| `test` | `pytest tests -v` (all tests; long) |
| `check` | runs `tests/unit/test_no_mock.py`; fails if `web/lib/mock.ts` is imported outside `web/lib/api.ts` |
| `web-accept` | brings the stack up (mock off), runs `tests/acceptance/test_web_pages.py` then `tests/screenshots/a11y.py` |
| `screens` | builds with `NEXT_PUBLIC_API_MOCK=1`, runs `capture.py` and `a11y.py`, restores mock off |
| `doctor` | `docker compose exec -T api python -m app.doctor` |
| `create-admin` | `docker compose exec -T api python -m app.create_admin` (prompts) |
| `voice` | `docker compose exec -T worker python -m app.voice en_US-amy-medium` |
| `contract` | regenerates `contracts/openapi.yaml` from the implemented routes |
| `types` | regenerates `web/lib/api-types.ts` from the contract with `openapi-typescript` |

## Start, stop, test, reset

```sh
cp .env.example .env          # fill in the values (see docs/SETUP_KEYS.md)
make up                       # start everything
make create-admin             # first admin, prompts for email + password
make doctor                   # environment + connection checks
make accept                   # API acceptance suite
make web-accept               # Playwright page flows + axe
make screens                  # screenshots into docs/screens/
make down                     # stop
```

Reset the database: `docker compose down -v` removes `pgdata`, `storage-data`,
`voices` and `relayrecordings`. `docker compose down` alone keeps them.
`make up` re-runs migrations on every start (`api/app/db.py:migrate`).

## Flags that change the run

| Variable | Default in compose | Effect |
| --- | --- | --- |
| `DEV_AUTH_ENABLED` | `false` | enables `POST /auth/dev/sign-in`; `make accept`/`web-accept` set it true |
| `NEXT_PUBLIC_DEV_AUTH` | `0` | shows the dev sign-in buttons in the web app; tests set it 1 |
| `NEXT_PUBLIC_API_MOCK` | `0` | `1` makes `web/lib/api.ts` call `web/lib/mock.ts` (screenshots) |
| `STORAGE_DRIVER` | `local` | `s3` switches both api and worker to the S3 client |
| `INVITE_REQUIRED` | `true` | `false` allows sign-up without a code |
| `APP_ENV` | `development` | `production` makes cookies `Secure` and refuses `DEV_AUTH_ENABLED` |
