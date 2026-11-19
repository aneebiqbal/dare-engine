# 08 — Video pipeline

## Upload → Short, step by step (local path)

1. **Start** — `POST /uploads/start` (`api/app/clips.py`) returns
   `upload_id` and `chunk_size` (1 MiB). A directory
   `UPLOAD_TMP_DIR/{upload_id}` is created.
2. **Chunks** — `PUT /uploads/{id}/chunks/{index}` writes the raw body to
   `{upload_id}/{index}.part`. No chunk is held in memory. `GET /uploads/{id}`
   reports which indexes arrived, so a client can resume.
3. **Complete** — `POST /uploads/{id}/complete` with `{marks[], filename}`
   (`upload_complete`): parts are sorted by numeric index and concatenated into
   `assembled{suffix}`.
4. **Store** — `_finalize_upload` computes
   `recordings/{user_id}/{upload_id}{suffix}` and calls `storage.put_file`
   (`api/app/storage.py`): local `shutil.copyfile` or S3 `upload_file`.
5. **Rows + jobs** — creates a `streams` row (`stream_key_hash='local-upload'`),
   then for each mark: an `assignments` row, `start`/`done` `marks`, a `clips`
   row (`state='queued'`, `stage='queued'`, `recording_key`, `source_start`,
   `source_end`), an `attempts` row, and a `render_clip` job with an
   idempotency key (`_enqueue_render`).
6. **Claim** — `worker/worker_app/jobs.py:claim` takes a queued job with
   `FOR UPDATE SKIP LOCKED`.
7. **Fetch** — `worker/worker_app/handlers.py:render_clip` sets stage `fetch` (10%),
   then `storage.get_file(recording_key, tmp/recording.mp4)` (whole file).
8. **Transcribe** — if the clip has a cached transcript covering this window it
   is reused; otherwise `render_short` cuts the window and calls
   `worker/clip/transcribe.py` (faster-whisper `small`, int8, CPU,
   `word_timestamps=True`). Stage `transcribe` (30%).
9. **Select** — `worker/clip/beats.py:select_setup` asks the LLM for setup
   beats when one is available, else word density. Stage `select` (50%).
10. **Render** — `worker/clip/engine.py:render_short`, stage `render` (90%):
    - window = `start-10s` … `end+5s` (`WINDOW_BEFORE`/`WINDOW_AFTER`);
    - `_cut` normalises to 1920×1080 and encodes the window;
    - spoiler guard (`policy.py:guard_window`) drops a window with no speech;
      `detect_letterbox` flags black bars;
    - hook = 2 s at the strongest second; setup = up to three 3 s pieces;
      payoff = the last 18 s; concatenated;
    - `layout.py:pick_layout` chooses `blur_fit` / `center_crop` / `fit_height`;
    - `caption.py:write_ass` (hook, word captions, end card) and `write_srt`;
    - FFmpeg renders 1080×1920 H.264 with the ASS subtitles filter, then a
      thumbnail and `metadata.json`.
11. **Voice-over** (optional) — `worker/clip/tts.py:speak` runs Piper
    (`piper --model … --output_file …`) for the hook and an outro line;
    `worker/clip/voice.py:mix_voice_over` delays each WAV to its cue, mixes the
    bed, and ducks the gameplay with `sidechaincompress`
    (`threshold=0.05 ratio=10 attack=20 release=250`).
12. **Store** — `clips/{id}/short.mp4`, `thumb.jpg`, `captions.srt`,
    `metadata.json`; the clip row becomes `state='ready'`, `stage='store'`,
    `progress=100`, with `transcript`, `source_start/end`, `render_key`.
13. **Read** — `GET /clips/{id}/download` (video) or `GET /clips/{id}/export`
    (zip built in a temp dir: `short.mp4`, `thumbnail.jpg`, `metadata.json`).

## Relay path

- `POST /streams` issues a key; `streams.storage_prefix = live/{key}`.
- MediaMTX records fMP4 to `/recordings/{path}/…` and calls
  `POST /hooks/relay/segment` (`api/app/hooks.py`) for each segment.
- `POST /marks` with `kind=done` calls `_enqueue_relay_clip`
  (`api/app/clips.py`), which enqueues a `render_clip` job with
  `recording_dir=/recordings/{prefix}`.
- The worker concatenates `*.m4s`/`*.mp4` with `ffmpeg -f concat -c copy`, then
  cuts the window as above.

## Stages and progress

`worker/worker_app/handlers.py:STAGES` — `fetch` 10, `transcribe` 30, `select` 50,
`render` 90, `store` 100. The Clips page polls `GET /clips` every 3 s while a
clip is not ready.

## Tools and functions

| Step | Tool | Entry point |
| --- | --- | --- |
| chunk assembly | Python file IO | `api/app/clips.py:upload_complete` |
| storage | boto3 / `shutil` | `api/app/storage.py`, `worker/worker_app/storage.py` |
| concatenate | FFmpeg | `worker/worker_app/handlers.py:_run_ffmpeg` |
| cut / normalise | FFmpeg | `worker/clip/engine.py:_cut` |
| transcribe | faster-whisper 1.2.1 | `worker/clip/transcribe.py:transcribe` |
| beats | LLM / word density | `worker/clip/beats.py:select_setup` |
| captions | libass (FFmpeg `subtitles`) | `worker/clip/caption.py:write_ass` |
| layout | FFmpeg filtergraph | `worker/clip/layout.py:filtergraph` |
| encode | FFmpeg (`libx264` or hardware) | `worker/clip/engine.py:codec_args` |
| speech | Piper (`piper-tts>=1.8.0`) | `worker/clip/tts.py:speak` |
| ducking | FFmpeg `sidechaincompress` | `worker/clip/voice.py:mix_voice_over` |

## Measured times

From `docs/performance.md` (Colima VM, 4 CPU, 8 GB, faster-whisper small int8,
software H.264, synthetic stand-in):

| Work | Wall time |
| --- | --- |
| 3 clips, serial | 188.7 s |
| 3 clips, 4-way pool | 119.8 s |
| 3 clips, 4-way pool, warm | 70.9 s |

`test_m4_relay.py` asserts Done → finished file < 180 s. Web performance budgets
in `docs/performance.md` are **not measured** ("to be measured in D3").

## Largest file actually processed

`tests/fixtures/standin_speech_45s.mp4` — **1,421,695 bytes (~1.4 MB), 45 s**,
1080×1920 H.264 with AAC. `fixtures/stream_10min.mp4` is absent, so no real
gameplay file has been processed. Not verified beyond the stand-in.

## What would break on an 8-hour, 30 GB recording

- **Staging disk:** the chunked upload writes 30 GB of parts plus a 30 GB
  assembled copy in `UPLOAD_TMP_DIR` (container `/tmp`), then `put_file` copies
  it again into storage. Three full copies at once; no size limit.
- **Worker disk:** `storage.get_file` downloads the whole 30 GB per render job
  into a temp dir; with `WORKER_CONCURRENCY=4` that is 120 GB of temp space.
- **No retention:** recordings and clips are never deleted except by
  `DELETE /account` (`api/app/account.py`). Eight-hour streams accumulate
  without bound.
- **Transcription is window-only**, so it stays cheap; the expensive parts are
  the full-file download and the disk copies.
- **FFmpeg seeking** uses `-ss` before `-i`, so the render itself does not
  decode the whole file — but the file is still copied in full first.
- **No resumable upload across a server restart:** chunk parts live in the API
  container's `/tmp`, not in shared storage; a restart loses them.

## Sprint 7 — automatic moments and a clip grammar

The admin studio (`/admin/studio`) turns a recording into clips with no
timestamps. `worker/clip/detect.py` scores the whole file once — transcript word
density, configurable marker phrases, per-second RMS against a rolling
baseline, scene-cut density and silence-then-burst — ranks 12 s windows, merges
overlaps and centres each on its peak. It reports the compute path (CUDA Whisper
when `ctranslate2` sees a GPU, else CPU int8); the worker stores that path before
the expensive pass so the studio shows it live.

`worker/clip/grammar.py` + `worker/clip/templates.json` build each clip from a
beat template: cold open (the payoff's peak) → hook text → optional context
flash-back → payoff → result stamp. The payoff is the longest beat. Captions are
re-mapped onto the disjoint beat ranges, so word sync stays monotonic. The API
image copies `templates.json` to `/app/app/clip_templates.json` for
`GET /studio/templates`.
