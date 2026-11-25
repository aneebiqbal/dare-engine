"""The host bridge's vision endpoint: it must return parsed JSON, or a clear error."""
import importlib.util
import json
import pathlib
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("mlx_bridge", ROOT / "local" / "mlx_bridge.py")
bridge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bridge)


class _Ollama(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        assert self.path == "/api/chat"
        assert body["messages"][0]["images"]
        raw = json.dumps({"message": {"content": self.reply}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def _serve(reply: str):
    handler = type("H", (_Ollama,), {"reply": reply})
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_vlm_describe_parses_json(monkeypatch):
    server, thread = _serve('{"clippable": true, "score": 0.8, "reason": "a win"}')
    monkeypatch.setattr(bridge, "OLLAMA", f"http://127.0.0.1:{server.server_port}")
    try:
        out = bridge.vlm_describe("AAAA", "prompt", "qwen2.5vl:7b")
    finally:
        server.shutdown()
        thread.join()
    assert out == {"clippable": True, "score": 0.8, "reason": "a win"}


def test_vlm_describe_reports_non_json(monkeypatch):
    server, thread = _serve("I cannot answer that")
    monkeypatch.setattr(bridge, "OLLAMA", f"http://127.0.0.1:{server.server_port}")
    try:
        out = bridge.vlm_describe("AAAA", "prompt", "qwen2.5vl:7b")
    finally:
        server.shutdown()
        thread.join()
    assert out["error"]
    assert out["raw"] == "I cannot answer that"
