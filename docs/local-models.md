# Local models on the M3 Max

The platform can run its AI on this Mac's GPU with Chinese open-weight models,
so idea generation and transcription never depend on a cloud key, credit or
latency. Ollama serves an OpenAI-compatible endpoint, so the existing
`shared/llm.py` client works unchanged — only `.env` changes.

## What is installed

Ollama 0.40 is on the host. Models already pulled:

| Model | Size | Use |
| --- | --- | --- |
| `qwen3.8:27b-mlx` | 18 GB | Qwen3.5 27.8B, nvfp4, MLX, vision + tools + thinking. General ideas. |
| `qwen2.5-coder:14b` | 9 GB | Coding. |
| `qwen2.5-coder-16k` | 9 GB | Coding, longer context. |
| `kimi-k2.6:cloud` | — | Kimi, cloud-backed. |

Add another with `make setup-engine ENGINE_MODEL=qwen3:8b` (or `deepseek-r1:7b`,
`qwen2.5:7b`, `kimi-k2`).

## Wire it into the product

```sh
make setup-engine ENGINE_MODEL=qwen3:8b
```

Then in `.env`:

```sh
LLM_PROVIDER=openai
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen3:8b
```

The API and the worker both read those three values, so the brain, the mission
editor, the clip review and the export copy all run locally. `make doctor`
reports the provider and model; it never prints the key.

## Prove it without Docker

```sh
make research-local
```

`local/research_local.py` runs the real `api/app/research.py` pipeline (same
prompt, schema and citation filter) with the one client pointed at Ollama. It
prints the sourced ideas. With no source keys it uses the saved sample feed, so
it is a deterministic proof of the local model path.

## Transcription on Metal (MLX Whisper)

The worker container cannot reach Metal, so transcription runs in a host bridge
(`local/mlx_bridge.py`, `mlx-whisper`, word timestamps). The worker calls it when
`MLX_WHISPER_URL` is set:

```sh
make setup-engine          # creates ~/.clipdesk-engine and installs mlx-whisper
make mlx-bridge            # serves ws-style HTTP on :8798
```

`.env`:

```sh
MLX_WHISPER_URL=http://host.docker.internal:8798
MLX_WHISPER_MODEL=mlx-community/whisper-large-v3-mlx
```

Leave `MLX_WHISPER_URL` empty to fall back to `faster-whisper` (CPU) in the
container. The compute path is stored per recording and shown in the studio as
`mlx / metal` with the GPU badge; `whisper_compute()` reports `("mlx", "metal")`
so the detector records it. **Measured:** 30.17 s for the 4.9-minute fixture
(593 words) after the model is cached; the first run also downloads the model.

## The container limitation (important)

The API and worker run in Linux containers. **Metal is only available on the
macOS host**, so a container cannot run MLX or Ollama. Two consequences:

- For a local model to serve the containerized API, Ollama must run on the host
  and the container must reach it at `host.docker.internal:11434` (Colima
  supports this). Set `LLM_BASE_URL=http://host.docker.internal:11434/v1` in
  that case.
- Transcription runs on the host through the MLX bridge above; the worker falls
  back to `faster-whisper` CPU when the bridge is not configured.

## Security

`LLM_API_KEY=ollama` is not a secret; it is a placeholder the local endpoint
ignores. Never put a real cloud key in `.env.example`.
