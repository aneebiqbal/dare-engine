# 09 — Storage

Two drivers behind one interface (`api/app/storage.py`, `worker/app/storage.py`):
`local` (default) and `s3`. Keys are the same for both. The default run mounts
the `storage-data` volume at `/data/storage` in the api and worker.

## Where files are written

| Location | What | Written by | Retention |
| --- | --- | --- | --- |
| `recordings/{user_id}/{upload_id}{suffix}` | the uploaded recording | `api/app/clips.py:_finalize_upload` | until account deletion |
| `clips/{clip_id}/short.mp4` | rendered 1080×1920 H.264 Short | `worker/app/handlers.py` | until account deletion |
| `clips/{clip_id}/thumb.jpg` | thumbnail | same | same |
| `clips/{clip_id}/captions.srt` | caption sidecar | same | same |
| `clips/{clip_id}/metadata.json` | title/description/tags/layout/flags | same | same |
| `voice-overs/{voice_over_id}/preview.wav` | Piper preview | `worker/app/handlers.py:preview_voice` | never deleted |
| `/recordings/{stream_path}/{timestamp}.m4s` (volume `relayrecordings`) | relay fMP4 segments | MediaMTX | `recordDeleteAfter: 0s` — never deleted |
| `/tmp/clipdesk-uploads/{upload_id}/*.part` + `assembled{suffix}` | upload staging | `api/app/clips.py` | never deleted |
| `/tmp/clipdesk-*` (api container) | download/export temp copies | `api/app/clips.py`, `account.py` | never deleted |
| `/tmp/render-*` (worker container) | render workspace | `worker/app/handlers.py` | auto-deleted (`TemporaryDirectory`) |
| `/data/voices/{voice}.onnx{,.json}` | Piper voice model | `make voice` | until the volume is removed |

S3 driver: bucket `S3_BUCKET`, path-style addressing, keys identical. The API
also exposes `GET /admin/storage` → `{driver, bytes}`.

## Measured sizes

| Artefact | Size | Source |
| --- | --- | --- |
| stand-in recording (45 s) | 1,421,695 B (~1.4 MB) | `ls tests/fixtures/standin_speech_45s.mp4` |
| rendered Short (29 s, 1080×1920) | 2,448,449 B (~2.4 MB) | `m1-render-*/short.mp4` |
| thumbnail | 64,900 B (~65 KB) | `m1-render-*/thumb.jpg` |
| captions + metadata | a few KB | `worker/clip/caption.py` |

## Disk for one session

The code stores the **original recording** plus one Short per mission. The
recording size depends on the ingest bitrate. `docs/spec.md` assumes a 6 Mbps
stream ≈ **2.7 GB/hour**; the synthetic stand-in is 1.4 MB / 45 s (≈0.11 GB/h),
which is not representative. Working below uses the spec's 2.7 GB/h.

Upload staging peak = parts + assembled + storage copy = **3 × recording**
(parts and the assembled copy are never deleted, so steady state is also
3 × recording plus clips). Worker temp = 1 × recording per concurrent job.

| Session | Recording | Steady-state storage (3× + clips) | Upload peak | 4 workers' temp |
| --- | --- | --- | --- | --- |
| 10 min | 0.45 GB | 1.35 GB + ~8 MB | 1.35 GB | 1.8 GB |
| 1 hour | 2.7 GB | 8.1 GB + ~8 MB | 8.1 GB | 10.8 GB |
| 8 hours | 21.6 GB | 64.8 GB + ~8 MB | 64.8 GB | 86.4 GB |

Clips assumed: 3 missions × (2.4 MB Short + 65 KB thumb + sidecars) ≈ 8 MB.
The rendered Short is <60 s regardless of the recording length.

**Consequences:** an 8-hour local upload needs ~65 GB of free disk for one
creator, and the relay volume grows without bound. There is no lifecycle rule
and no cleanup job. The only deletion path is `DELETE /account`
(`api/app/account.py`), which removes `recordings/{user_id}/` and
`clips/{clip_id}/`.
