# 13 — Dependencies and licences

Versions are pinned in the manifests; licences were read from the installed
package metadata in the running containers today.

## Web (`web/package.json`)

| Package | Version | Licence | Use |
| --- | --- | --- | --- |
| `next` | 15.1.6 | MIT | App Router framework |
| `react` / `react-dom` | 19.0.0 | MIT | UI |
| `geist` | 1.3.1 (installed 1.9.2) | SIL OPEN FONT LICENSE | font |
| `typescript` | 5.7.3 | Apache-2.0 | types |
| `tailwindcss` | 3.4.17 | MIT | styling |
| `autoprefixer` | 10.4.20 | MIT | CSS |
| `postcss` | 8.4.49 | MIT | CSS |
| `@types/node`, `@types/react`, `@types/react-dom` | 22.x / 19.x | MIT | types |

Not in the manifest but used by `make types`: `openapi-typescript` (fetched with
`npx --yes`; MIT).

## API (`api/requirements.txt`)

| Package | Version | Licence | Use |
| --- | --- | --- | --- |
| `fastapi` | 0.115.6 | MIT | HTTP framework |
| `uvicorn[standard]` | 0.34.0 | BSD-3-Clause | server |
| `psycopg[binary]` | 3.2.3 | **LGPL-3.0** | PostgreSQL driver |
| `pydantic-settings` | 2.7.1 | MIT | config |
| `jsonschema` | 4.23.0 | MIT | AI/schema validation |
| `boto3` | 1.37.1 | Apache-2.0 | S3 |
| `python-multipart` | 0.0.20 | Apache-2.0 | upload parsing |
| `argon2-cffi` | 23.1.0 | MIT | password hashing |
| `pyyaml` | 6.0.2 | MIT | contract export |

## Worker (`worker/requirements.txt`)

| Package | Version | Licence | Use |
| --- | --- | --- | --- |
| `fastapi` | 0.115.6 | MIT | health/worker service |
| `uvicorn[standard]` | 0.34.0 | BSD-3-Clause | server |
| `psycopg[binary]` | 3.2.3 | **LGPL-3.0** | PostgreSQL driver |
| `pydantic-settings` | 2.7.1 | MIT | config |
| `faster-whisper` | 1.2.1 | MIT | transcription |
| `av` | 16.1.0 | BSD-3-Clause | media decode for whisper |
| `boto3` | 1.37.1 | Apache-2.0 | S3 |

## Optional voice add-on (`worker/requirements-voice.txt`)

| Package | Version | Licence | Use |
| --- | --- | --- | --- |
| `piper-tts` | >=1.8.0 | **GPL-3.0-or-later** | local TTS; installed by `make voice` |
| `onnxruntime` (transitive) | 1.32.0 | MIT | Piper runtime |

## Tests (`tests/requirements.txt`)

`pytest` MIT, `jsonschema` MIT, `pyyaml` MIT, `playwright` Apache-2.0,
`argon2-cffi` MIT.

## System tools

| Tool | Licence | Note |
| --- | --- | --- |
| FFmpeg | LGPL-2.1+ when built without GPL-only components | invoked as a binary; `docs/decisions.md` flags that the distro build may include libx264 (GPL) and recommends legal review / OpenH264 fallback |
| MediaMTX | MIT | relay |
| PostgreSQL | PostgreSQL Licence | database |
| Piper voice models | repository front matter: MIT | individual voice cards vary |

## Flags

1. **`piper-tts` is GPL-3.0-or-later** (package metadata,
   `Home-page: github.com/OHF-voice/piper1-gpl`). The old `rhasspy/piper` was
   MIT but is archived; the current package is GPL. The BUILD_PROMPT hard rule
   says "Do not use AGPL or GPL code inside the app", so voice-over is an
   optional add-on installed by `make voice`, never in the default build.
   `docs/licences.md` is the current manifest; an owner decision on the GPL
   add-on is still pending (replace the TTS engine, or accept GPL).
2. **`psycopg` is LGPL-3.0.** It is used as a client over a socket; no linking
   into a distributed binary. Lower risk than GPL, but noted.
3. **FFmpeg** may be a GPL build; see `docs/decisions.md`.
4. **Geist** is OFL-1.1 (font), **TypeScript** Apache-2.0 — both permissive.
