"""F1: the worker uses the shared AI client; the legacy Gemini path is gone."""
import importlib.util
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "worker"))

_spec = importlib.util.spec_from_file_location("llm_shared", ROOT / "shared" / "llm.py")
llm_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(llm_shared)
sys.modules["llm_shared"] = llm_shared

from clip.llm import get_llm  # noqa: E402


def test_get_llm_is_none_without_a_key(monkeypatch):
    from worker_app.config import settings

    monkeypatch.setattr(settings, "llm_api_key", "")
    assert get_llm() is None


def test_get_llm_returns_the_shared_client_with_a_key(monkeypatch):
    from worker_app.config import settings

    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_api_key", "k")
    monkeypatch.setattr(settings, "llm_base_url", "http://example.invalid/v1")
    monkeypatch.setattr(settings, "llm_model", "model-x")
    llm = get_llm()
    assert llm is not None
    assert llm.model == "model-x"
    assert llm.provider == "openai"


def test_legacy_gemini_path_is_gone():
    source = (ROOT / "worker" / "clip" / "llm.py").read_text().lower()
    assert "generativelanguage" not in source
    assert "gemini" not in source


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Drain the request body, or the server's close can RST the client.
        self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
        body = json.dumps(
            {
                "choices": [{"message": {"content": '{"setup": [{"start": 1, "end": 4}]}'}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def test_shared_client_calls_the_provider_and_logs_usage():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    usage = {}
    llm = llm_shared.OpenAICompatibleLLM(
        f"http://127.0.0.1:{server.server_port}",
        "key",
        "model",
        log_usage=lambda **kw: usage.update(kw),
    )
    schema = {
        "type": "object",
        "properties": {"setup": {"type": "array"}},
        "required": ["setup"],
    }
    result = llm.complete_json("system", "user", schema, kind="beats")
    server.shutdown()
    assert result == {"setup": [{"start": 1, "end": 4}]}
    assert usage["kind"] == "beats"
    assert usage["prompt_tokens"] == 5
    assert usage["completion_tokens"] == 2
    assert usage["fallback"] is False


def test_shared_client_retries_once_then_raises():
    class Bad(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
            body = json.dumps({"choices": [{"message": {"content": "not json"}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Bad)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    llm = llm_shared.OpenAICompatibleLLM(f"http://127.0.0.1:{server.server_port}", "k", "m")
    with pytest.raises(llm_shared.LLMError):
        llm.complete_json("s", "u", None, kind="beats")
    server.shutdown()
