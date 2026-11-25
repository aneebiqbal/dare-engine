# Setup and keys

Numbered steps for a non-developer. Do them in this order. Every value goes in
`.env`, which is gitignored. Never commit `.env`.

## 1. Managed PostgreSQL

Clipdesk needs two connection strings: a pooled one for the API and a direct one
for migrations and the job worker.

**Neon**

1. Create a project at <https://console.neon.tech>.
2. Open **Connection details**. Copy the **Pooled connection string** (its host
   contains `-pooler`). It looks like
   `postgresql://user:pass@ep-xxx-pooler.us-east-2.aws.neon.tech/db?sslmode=require`.
3. Copy it again and remove `-pooler` from the host. That is the direct string.
4. Put the pooled string in `DATABASE_URL` and the direct string in
   `DATABASE_URL_DIRECT`.

**Aiven**

1. Create a PostgreSQL service at <https://console.aiven.io>.
2. Open the service **Overview** and copy the **Service URI**. It already ends
   in `sslmode=require`.
3. Put it in both `DATABASE_URL` and `DATABASE_URL_DIRECT`. Aiven's URI is
   direct; if you enable the Aiven pooler, use the pooler URI for
   `DATABASE_URL` and the direct URI for `DATABASE_URL_DIRECT`.

**Confirm:** `make doctor` prints `PASS pooled database connect` and
`PASS direct database connect`.

## 2. Session secret

1. Run `openssl rand -hex 32` in a terminal.
2. Copy the printed string into `SESSION_SECRET`.

**Confirm:** `make doctor` prints `PASS SESSION_SECRET changed`.

## 3. AI provider key

One client speaks the OpenAI-compatible chat completions format. Pick a
provider and set three variables.

**OpenCode Zen**

1. Sign in at <https://opencode.ai/> and add credit.
2. Copy the API key.
3. Fetch the model list: `curl https://opencode.ai/zen/v1/models`. Use an id from
   it, e.g. `opencode/<model-id>`.
4. Set `LLM_BASE_URL=https://opencode.ai/zen/v1`, `LLM_API_KEY=<key>`,
   `LLM_MODEL=<id>`.

**xAI Grok**

1. Create an API key at <https://x.ai/api>.
2. Set `LLM_BASE_URL=https://api.x.ai/v1`, `LLM_API_KEY=<key>`,
   `LLM_MODEL=grok-4-0709` (check <https://docs.x.ai> for the current model id).

**Confirm:** `make doctor` prints `PASS LLM_API_KEY present` and
`PASS LLM_MODEL set`. Open **Admin → AI usage**: it shows the provider, model
and whether the key is present, never the key itself. For a live call, type a
question on the admin pool page and click **Write cards**.

## 4. Optional S3 storage

Local disk is the default and needs nothing. To use S3-compatible storage:

1. Create a bucket (AWS S3, Cloudflare R2, or MinIO).
2. Create an access key and secret.
3. Set `STORAGE_DRIVER=s3`, `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`,
   `S3_SECRET_KEY`, `S3_REGION`.

**Confirm:** `make doctor` prints `PASS storage (s3)`.

## 5. Local voice-over model

1. Run `make voice`. It downloads `en_US-amy-medium` from
   `rhasspy/piper-voices` into the `voices` volume.
2. The `piper-tts` package is GPL-3.0-or-later; the voice repository declares
   MIT. Check the individual voice card before commercial use. For
   monetisation, your own voice is the safer choice.

**Confirm:** `make doctor` prints `PASS local TTS command` and
`PASS voice model present`.

## 6. Run it

```
cp .env.example .env   # then edit .env
make up
make create-admin      # prompts for the admin email and password
make doctor
```

Then open <http://localhost:3100>, sign in as the admin, and create an invite on
**Admin → Invites**. Give the code to a creator, who signs up at
`/signup?code=...`.
