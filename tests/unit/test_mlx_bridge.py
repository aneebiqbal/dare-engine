"""The host MLX Whisper bridge path, against a stub HTTP server."""
import http.server
import json
import pathlib
import sys
import tempfile
import threading

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "worker"))

from worker_app.config import settings  # noqa: E402
from clip.transcribe import transcribe, whisper_compute  # noqa: E402


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        assert self.headers.get("X-Filename") == "clip.mp4"
        assert body
        payload = {
            "words": [
                {"start": 0.1, "end": 0.4, "text": "hello"},
                {"start": 0.5, "end": 0.9, "text": "world"},
            ]
        }
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def test_mlx_bridge_transcribes_words(monkeypatch):
    server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(settings, "mlx_whisper_url", f"http://127.0.0.1:{server.server_port}")
    try:
        assert whisper_compute() == ("mlx", "metal")
        with tempfile.TemporaryDirectory() as tmp:
            clip = pathlib.Path(tmp) / "clip.mp4"
            clip.write_bytes(b"not really video")
            words = transcribe(str(clip))
    finally:
        server.shutdown()
        thread.join()
    assert [(w.text, w.start, w.end) for w in words] == [
        ("hello", 0.1, 0.4),
        ("world", 0.5, 0.9),
    ]
