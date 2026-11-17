# Running Clipdesk Missions

## First time, once

1. Make a copy of the settings file:

   ```sh
   cp .env.example .env
   ```

   `.env` is gitignored. Keep your keys there.

2. Start the app (this builds and starts the database, API, worker, web and
   relay):

   ```sh
   make up
   ```

3. Download the local voice for voice-over (about 63 MB, once):

   ```sh
   make voice
   ```

4. Create the administrator account. It asks for an email and a password (the
   password is not shown as you type):

   ```sh
   make create-admin
   ```

## Every time

- Start: `make up`
- Open: **http://localhost:3100**
- Stop: `make down`
- Logs: `make logs`

The other ports, if you want them directly: API http://localhost:8000, worker
http://localhost:8001, relay control API http://localhost:19997.

## Go live with real AI

Edit `.env` and set these three (see `docs/SETUP_KEYS.md` for where to get each):

| Variable | Example |
| --- | --- |
| `LLM_PROVIDER` | `openai` |
| `LLM_BASE_URL` | `https://opencode.ai/zen/v1` or `https://api.x.ai/v1` |
| `LLM_API_KEY` | the key from the provider |
| `LLM_MODEL` | the model id from the provider |

Then restart: `make up`. To use a managed database instead of the local
container, also set `DATABASE_URL` and `DATABASE_URL_DIRECT`.

## Check it is healthy

```sh
make doctor
```

A healthy local run prints `PASS` for every line except `LLM_API_KEY present`
and `LLM_MODEL set` (those need a real key). It ends with `11/13 checks passed`.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `make up` says a port is already in use | The stack uses 3100 / 8000 / 8001 / 19997 on purpose because 3000 / 900 / 9997 are taken on this machine. Stop the other service, or change the port in `docker-compose.yml`. |
| Docker Desktop will not start | Use Colima: `colima start --runtime docker`, then `docker context use colima`. If the Colima VM disk is owned by root: `sudo chown $(whoami):staff ~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw`. |
| A service is not starting | `docker compose logs <service>` (for example `docker compose logs api`), then `make doctor`. |
| The web page cannot reach the API | Make sure `.env` exists and `make up` finished. The web proxy uses `API_URL=http://api:8000`. |
| Forgot the admin password | An admin can issue a reset link from **Admin → Users → Reset link**. |
| Tests fail because `.venv` is missing | `make accept` recreates it automatically. |
