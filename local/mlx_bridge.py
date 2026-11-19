"""Host-side MLX Whisper bridge.

The worker runs in a Linux container and cannot reach Metal, so transcription
runs here on the Mac and the worker calls this over HTTP. Word-level
timestamps, the same shape the worker already consumes.

    make mlx-bridge      # runs with ~/.clipdesk-engine/bin/python
"""
from __future__ import annotations

import json
import os
import pathlib
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = os.environ.get("MLX_WHISPER_MODEL", "mlx-community/whisper-large-v3-mlx")
PORT = int(os.environ.get("MLX_WHISPER_PORT", "8798"))
COMPUTE = "mlx-metal"


def transcribe(path: str) -> dict:
    import mlx_whisper

    started = time.time()
    result = mlx_whisper.transcribe(path, path_or_hf_repo=MODEL, word_timestamps=True)
    words = [
        {"start": float(w["start"]), "end": float(w["end"]), "text": w["word"].strip()}
        for segment in result.get("segments", [])
        for w in segment.get("words", [])
        if w.get("word", "").strip()
    ]
    return {
        "words": words,
        "compute": COMPUTE,
        "model": MODEL,
        "elapsed_s": round(time.time() - started, 2),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"ok": True, "compute": COMPUTE, "model": MODEL})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/transcribe":
            self._send(404, {"error": "not found"})
            return
        tmp = None
        try:
            # The worker streams the file bytes; the bridge writes them to a
            # temp file because the container's storage is not on the host.
            length = int(self.headers.get("Content-Length", "0"))
            suffix = pathlib.Path(self.headers.get("X-Filename", "audio.mp4")).suffix or ".mp4"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                tmp = handle.name
                remaining = length
                while remaining > 0:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    handle.write(chunk)
                    remaining -= len(chunk)
            self._send(200, transcribe(tmp))
        except Exception as exc:
            self._send(500, {"error": f"{type(exc).__name__}: {exc}"})
        finally:
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass


def main() -> int:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"MLX Whisper bridge on http://0.0.0.0:{PORT} (model {MODEL})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
