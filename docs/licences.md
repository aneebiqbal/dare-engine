# Licences

Manifest of every shipped dependency and its licence. Generated from
`tests/licence_check.py` (`make licence`) and
`docs/context/13-dependencies-and-licences.md`, cross-checked against the
manifests in this repo.

Scope: the direct dependencies of the default build. Transitive dependencies
are not individually audited; the two that matter are listed where relevant.
Regenerate the audit with `make licence`; `make check` and CI fail if a
GPL/AGPL package appears in the core requirements.

## Core application (shipped)

### API — `api/requirements.txt`

| Package | Version | Licence | Use |
| --- | --- | --- | --- |
| `fastapi` | 0.115.6 | MIT | HTTP framework |
| `uvicorn[standard]` | 0.34.0 | BSD-3-Clause | server |
| `psycopg[binary]` | 3.2.3 | LGPL-3.0 | PostgreSQL driver |
| `psycopg-pool` | 3.2.3 | LGPL-3.0-only | connection pool |
| `pydantic-settings` | 2.7.1 | MIT | config |
| `jsonschema` | 4.23.0 | MIT | AI / schema validation |
| `boto3` | 1.37.1 | Apache-2.0 | S3 |
| `python-multipart` | 0.0.20 | Apache-2.0 | upload parsing |
| `argon2-cffi` | 23.1.0 | MIT | password hashing |
| `pyyaml` | 6.0.2 | MIT | contract export |
| `simpleobsws` | 1.4.3 | MIT | OBS WebSocket client |

### Worker — `worker/requirements.txt`

| Package | Version | Licence | Use |
| --- | --- | --- | --- |
| `fastapi` | 0.115.6 | MIT | health / worker service |
| `uvicorn[standard]` | 0.34.0 | BSD-3-Clause | server |
| `psycopg[binary]` | 3.2.3 | LGPL-3.0 | PostgreSQL driver |
| `pydantic-settings` | 2.7.1 | MIT | config |
| `jsonschema` | 4.23.0 | MIT | schema validation |
| `faster-whisper` | 1.2.1 | MIT | transcription |
| `av` | 16.1.0 | BSD-3-Clause | media decode for Whisper |
| `boto3` | 1.37.1 | Apache-2.0 | S3 |

`faster-whisper` wraps OpenAI Whisper (MIT) and CTranslate2 (MIT). No GPL.

### Web — `web/package.json`

| Package | Version | Licence | Use |
| --- | --- | --- | --- |
| `next` | 15.1.6 | MIT | App Router framework |
| `react` / `react-dom` | 19.0.0 | MIT | UI |
| `geist` | 1.3.1 (installed 1.9.2) | SIL OPEN FONT LICENSE 1.1 | font |
| `typescript` | 5.7.3 | Apache-2.0 | types |
| `tailwindcss` | 3.4.17 | MIT | styling |
| `autoprefixer` | 10.4.20 | MIT | CSS |
| `postcss` | 8.4.49 | MIT | CSS |
| `@types/node` | 22.10.5 | MIT | types |
| `@types/react` | 19.0.5 | MIT | types |
| `@types/react-dom` | 19.0.2 | MIT | types |

Not in the manifest but used by `make types`: `openapi-typescript` (fetched with
`npx --yes`; MIT).

### System tools

| Tool | Licence | Note |
| --- | --- | --- |
| FFmpeg | LGPL-2.1-or-later when built without GPL-only components | invoked as a separate binary, not linked. The Debian package may include `libx264` (GPL). Flagged for legal review before commercial launch; a Cisco OpenH264 (BSD) build is the fallback. |
| MediaMTX | MIT | relay |
| PostgreSQL | PostgreSQL Licence | database |
| DejaVu Sans | Bitstream Vera / public domain | installed so libass has a font |
| Piper voice models | repository front matter: MIT | individual voice cards vary |

## Tests and development only (not shipped)

| Package / file | Licence | Note |
| --- | --- | --- |
| `pytest` 8.3.4 | MIT | test runner |
| `jsonschema` | MIT | contract test |
| `pyyaml` | MIT | contract test |
| `playwright` 1.65.2 | Apache-2.0 | page flows |
| `argon2-cffi` | MIT | auth tests |
| `pydantic-settings`, `fastapi`, `python-multipart` | MIT / Apache-2.0 | API unit tests import the API app |
| `psycopg[binary]`, `psycopg-pool` | LGPL-3.0 | test env only (unpinned in `tests/requirements.txt`) |
| `tests/screenshots/lib/axe.min.js` | MPL-2.0 | axe-core 4.14.1, vendored; dev/test only, never copied into an image |

## Optional add-on — voice-over (not in the default build)

| Package | Version | Licence | Note |
| --- | --- | --- | --- |
| `piper-tts` | >= 1.8.0 | **GPL-3.0-or-later** | local TTS. Lives in `worker/requirements-voice.txt`, not in `worker/requirements.txt`. `make voice` installs it into the running worker on demand. |
| `onnxruntime` | 1.32.0 | MIT | transitive runtime of Piper |

The voice model repository declares MIT at the repo level; individual voice
cards vary. The UI tells the creator that their own voice is safer for
monetisation.

## Flags

1. **No GPL or AGPL in the core.** The only GPL package is the optional
   `piper-tts` voice add-on, isolated in `worker/requirements-voice.txt` and
   installed only by `make voice`. `tests/licence_check.py` fails if
   `piper-tts` appears in a core requirements file or if the optional file is
   missing.
2. **LGPL (weak copyleft):** `psycopg` and `psycopg-pool` (LGPL-3.0). Used as
   a client over a socket; no linking into a distributed binary. Lower risk
   than GPL, noted for the legal review.
3. **FFmpeg** may be a GPL build; see `docs/decisions.md`. Legal review before
   any commercial launch.
4. **Check gap:** `tests/licence_check.py` does not list `psycopg-pool`, so
   `make licence` prints `WARN requirements.txt: psycopg-pool licence unknown`.
   The installed metadata says `LGPL-3.0-only`. Add it to the check's table to
   clear the warning.
5. **Doc drift:** `docs/context/13-dependencies-and-licences.md` still lists
   `piper-tts` in `worker/requirements.txt` and says `docs/decisions.md` calls
   Piper MIT. Both are out of date: the package is in the optional file, and
   `docs/decisions.md` has a MIT row in its Sprint 6 table next to a GPL note.
   This file is the current manifest.
6. **Geist** is OFL-1.1 (font) and **TypeScript** Apache-2.0 — both permissive.
