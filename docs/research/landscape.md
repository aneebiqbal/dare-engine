# Landscape — capture, clipping, local models, desktop shells

What is out there, read before the ship sprint. Sources are public project pages,
docs and repositories; this is a reading, not a code audit.

## Capture and clipping

| Project | Kind | What it does | Relevance |
| --- | --- | --- | --- |
| OBS Studio | open-source capture/stream (GPL-2.0) | Scenes, sources, replay buffer, encoders | The capture standard. We integrate it over obs-websocket rather than replace it. |
| obs-websocket | OBS remote control (MIT) | WebSocket API for status, record, scene, screenshots | Already the proven path in this repo (OBS 33.0.1). |
| Segra | open-source game recorder/clipper | Records through OBS/libobs; replay buffer, clip editor, auto highlights | Confirms “record through OBS, clip after” and per-game profiles. |
| OpenShorts | open-source short-video tooling | Vertical short output and caption-first framing | Validates the 9:16 caption-first output. |
| AutoClip | automatic clipping | Finds clips from a stream/recording | The auto-clip idea; the human still approves. |
| Cap | open-source screen recorder | One-click recording, automatic zoom | The no-OBS built-in recorder pattern: simple, MP4 out. |
| ShareX | open-source screen capture | Region capture, save a file, share | The “record a region, get a file” simplicity. |
| Insights Capture | OBS alternative | Automatic game recording and clipping | The replay-buffer + auto-highlight UX. |
| Medal / Outplayed | consumer clip tools | Replay buffers, instant clips | The consumer expectation: clip instantly, publish deliberately. |
| NVIDIA Highlights / ShadowPlay | driver-level | Automatic highlights while you play | The vision-detector idea: software watches and proposes. |
| Loom / Screen Studio | polished recorders | No-setup recording | The no-OBS path must be one click and produce a file. |

**Takeaway.** OBS is the reliable default; a built-in recorder is the fallback.
Automatic clipping is expected, but the admin decides what to publish.

## Local models and machine learning

| Thing | Why it matters here |
| --- | --- |
| MLX Whisper (`mlx-community/whisper-large-v3-mlx`) | Word-level transcription on Metal; MIT. Already the proven ASR path. |
| Ollama | Serves local LLMs and vision models over an OpenAI-compatible API and an HTTP API for images. |
| Qwen2.5-VL-7B-Instruct | Apache-2.0, stable JSON output, an MLX 4-bit build (~6–8 GB). The vision pass model. |
| MiniCPM-V | Apache-2.0 small VLM; an alternative if Qwen underperforms. |
| faster-whisper | MIT CPU fallback when no Metal bridge is available. |
| LM Studio / Jan | The model-manager UX: install state, size, fit, download progress, unload, live memory. We copy the pattern. |

**Takeaway.** Keep one model resident at a time. The vision model loads only for
its sampled pass and unloads, verified.

## Desktop application shells

| Shell | Size | Backend | Verdict |
| --- | --- | --- | --- |
| Tauri 2 | ~3–10 MB | Rust + system web view | **Chosen.** Small, light, sidecar-friendly. |
| Electron | ~150 MB | Node + bundled Chromium | Too heavy for a local engine companion. |
| NW.js / Electrobun / Deno Desktop | varies | varies | Viable, but Tauri is the best fit for FFmpeg and sidecars. |

**Takeaway.** Tauri. The window loads the existing web app; Rust owns the two
things a browser cannot do (start the stack, record the screen).

## Deployment

| Option | Trade-off |
| --- | --- |
| Managed Postgres (Neon) | Point-in-time recovery, pooled + direct connections. The default. |
| Small VPS + Caddy | Cheap TLS termination; the web half needs no GPU and little disk. |
| S3-compatible object storage | Required once the API and the worker are different machines. |
| Self-hosted Postgres | Works; you run `make backup` and keep the dumps. |

**Takeaway.** Cloud = web + API + managed DB. Desktop = everything heavy. Media
must be shared (S3) when the worker is not on the same machine as the API.
