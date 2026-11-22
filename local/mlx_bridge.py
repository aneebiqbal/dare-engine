"""Host-side engine bridge: MLX Whisper transcription + local model manager.

The worker runs in a Linux container and cannot reach Metal, so transcription
runs here on the Mac and the worker calls this over HTTP. The same bridge
exposes the local model inventory (Ollama + MLX), pull progress, unload/free
and a live memory readout, so the admin Models page is never a fake gauge.

    make mlx-bridge      # runs with ~/.clipdesk-engine/bin/python
"""
from __future__ import annotations

import gc
import json
import os
import pathlib
import subprocess
import tempfile
import threading
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = os.environ.get("MLX_WHISPER_MODEL", "mlx-community/whisper-large-v3-mlx")
VISION_MODEL = os.environ.get("VISION_MODEL", "qwen2.5vl:7b")
PORT = int(os.environ.get("MLX_WHISPER_PORT", "8798"))
COMPUTE = "mlx-metal"
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")

_state_lock = threading.Lock()
_state = {"transcribing": False, "last_elapsed_s": None}
_pulls: dict[str, dict] = {}
_pulls_lock = threading.Lock()
_model_lock = threading.Lock()
_last_activity = time.time()
IDLE_MINUTES = float(os.environ.get("MLX_IDLE_MINUTES", "10"))


def _touch() -> None:
    global _last_activity
    _last_activity = time.time()


def _clear_mlx() -> None:
    try:
        import mlx.core as mx

        mx.clear_cache()
        gc.collect()
    except Exception:
        pass


def transcribe(path: str) -> dict:
    import mlx_whisper

    with _model_lock:  # one model resident at a time
        _touch()
        with _state_lock:
            _state["transcribing"] = True
        started = time.time()
        try:
            result = mlx_whisper.transcribe(path, path_or_hf_repo=MODEL, word_timestamps=True)
        finally:
            with _state_lock:
                _state["transcribing"] = False
                _state["last_elapsed_s"] = round(time.time() - started, 2)
        words = [
            {"start": float(w["start"]), "end": float(w["end"]), "text": w["word"].strip()}
            for segment in result.get("segments", [])
            for w in segment.get("words", [])
            if w.get("word", "").strip()
        ]
    # Free the ASR model before the next pipeline stage loads its own.
    _clear_mlx()
    _touch()
    return {
        "words": words,
        "compute": COMPUTE,
        "model": MODEL,
        "elapsed_s": _state["last_elapsed_s"],
    }


def _http(method: str, url: str, payload: dict | None = None, timeout: float = 30) -> bytes:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _ollama_state() -> dict:
    out: dict = {"available": False, "error": None, "models": [], "running": []}
    try:
        tags = json.loads(_http("GET", OLLAMA + "/api/tags", timeout=5))
        out["models"] = [
            {
                "name": m.get("name", ""),
                "size_bytes": int(m.get("size", 0) or 0),
                "modified_at": m.get("modified_at"),
            }
            for m in tags.get("models", [])
        ]
        out["available"] = True
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out
    try:
        ps = json.loads(_http("GET", OLLAMA + "/api/ps", timeout=5))
        out["running"] = [
            {
                "name": m.get("name", ""),
                "size_bytes": int(m.get("size", 0) or 0),
                "size_vram_bytes": int(m.get("size_vram", 0) or 0),
                "expires_at": m.get("expires_at"),
            }
            for m in ps.get("models", [])
        ]
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def _host_memory() -> dict:
    total = used = 0
    try:
        total = int(
            subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()
        )
    except Exception:
        pass
    try:
        out = subprocess.run(
            ["ps", "-Ao", "rss="], capture_output=True, text=True, timeout=5
        ).stdout
        used = sum(int(x) for x in out.split() if x.strip()) * 1024
    except Exception:
        pass
    return {
        "total_bytes": total,
        "used_bytes": used,
        "percent": round(100.0 * used / total, 1) if total else 0.0,
    }


def _mlx_state() -> dict:
    out = {
        "model": MODEL,
        "transcribing": _state["transcribing"],
        "last_elapsed_s": _state["last_elapsed_s"],
        "peak_memory_bytes": None,
        "downloaded": False,
        "error": None,
    }
    slug = MODEL.replace("/", "--")
    cache = pathlib.Path.home() / ".cache" / "huggingface" / "hub"
    out["downloaded"] = any(cache.glob(f"models--{slug}*"))
    try:
        import mlx.core as mx

        out["peak_memory_bytes"] = int(mx.get_peak_memory())
    except Exception as exc:
        out["error"] = type(exc).__name__
    return out


def models_status() -> dict:
    return {
        "compute": COMPUTE,
        "model": MODEL,
        "ollama": _ollama_state(),
        "mlx": _mlx_state(),
        "host": _host_memory(),
    }


def start_pull(name: str) -> dict:
    task = {
        "id": uuid.uuid4().hex,
        "name": name,
        "done": False,
        "progress": 0.0,
        "status": "starting",
        "error": None,
    }
    with _pulls_lock:
        _pulls[task["id"]] = task
    threading.Thread(target=_run_pull, args=(task["id"], name), daemon=True).start()
    return dict(task)


def _run_pull(task_id: str, name: str) -> None:
    with _pulls_lock:
        task = _pulls[task_id]
    try:
        req = urllib.request.Request(
            OLLAMA + "/api/pull",
            data=json.dumps({"model": name, "stream": True}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3600) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if data.get("error"):
                    task["error"] = data["error"]
                    task["status"] = "error"
                    task["done"] = True
                    return
                total = data.get("total") or 0
                completed = data.get("completed") or 0
                if total:
                    task["progress"] = round(100.0 * completed / total, 1)
                task["status"] = data.get("status", "pulling")
        task["done"] = True
        task["progress"] = 100.0
        task["status"] = "done"
    except Exception as exc:
        task["error"] = f"{type(exc).__name__}: {exc}"
        task["status"] = "error"
        task["done"] = True


def pull_status(task_id: str) -> dict | None:
    with _pulls_lock:
        task = _pulls.get(task_id)
        return dict(task) if task else None


def vlm_describe(image_b64: str, prompt: str, model: str) -> dict:
    """Ask an Ollama vision model about one frame. Returns parsed JSON or an error."""
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt, "images": [image_b64]}],
            "stream": False,
            "format": "json",
        }
    ).encode()
    req = urllib.request.Request(
        OLLAMA + "/api/chat", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read())
    text = (data.get("message") or {}).get("content") or ""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "the model did not return JSON", "raw": text[:300]}


def _unload_ollama(name: str | None) -> None:
    if name:
        _http("POST", OLLAMA + "/api/generate", {"model": name, "keep_alive": 0}, timeout=60)
        return
    for model in _ollama_state()["running"]:
        _http("POST", OLLAMA + "/api/generate", {"model": model["name"], "keep_alive": 0}, timeout=60)


def free_all() -> dict:
    """Unload every Ollama model and clear the MLX cache. Real, verified."""
    error = None
    try:
        _unload_ollama(None)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    _clear_mlx()
    _touch()
    return {"ok": error is None, "error": error}


def _watchdog() -> None:
    """Free everything after N minutes idle (the #1 local-AI failure mode)."""
    while True:
        time.sleep(30)
        with _state_lock:
            busy = _state["transcribing"]
        if not busy and time.time() - _last_activity >= IDLE_MINUTES * 60:
            free_all()


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

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"ok": True, "compute": COMPUTE, "model": MODEL})
        elif self.path == "/models":
            self._send(200, models_status())
        elif self.path.startswith("/models/pull/"):
            task = pull_status(self.path.rsplit("/", 1)[-1])
            self._send(200, task or {"error": "unknown task"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/transcribe":
            self._transcribe()
        elif self.path == "/models/pull":
            name = (self._body().get("name") or "").strip()
            if not name:
                self._send(422, {"error": "name required"})
                return
            self._send(200, start_pull(name))
        elif self.path == "/models/unload":
            name = (self._body().get("name") or "").strip()
            try:
                _unload_ollama(name or None)
                self._send(200, {"ok": True})
            except Exception as exc:
                self._send(502, {"error": f"{type(exc).__name__}: {exc}"})
        elif self.path == "/models/free":
            self._send(200, free_all())
        elif self.path == "/vlm":
            body = self._body()
            image = body.get("image") or ""
            prompt = body.get("prompt") or ""
            model = body.get("model") or VISION_MODEL
            if not image or not prompt:
                self._send(422, {"error": "image and prompt required"})
                return
            try:
                self._send(200, vlm_describe(image, prompt, model))
            except Exception as exc:
                self._send(502, {"error": f"{type(exc).__name__}: {exc}"})
        else:
            self._send(404, {"error": "not found"})

    def _transcribe(self):
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
    threading.Thread(target=_watchdog, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Engine bridge on http://0.0.0.0:{PORT} (mlx {MODEL}, ollama {OLLAMA})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
