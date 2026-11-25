"""The window transcript must keep speech.

faster-whisper's VAD filter drops real dialogue from a short window (the same
audio transcribes fine as a whole file). That made the spoiler guard throw
`SpoilerError` on the detector's top moment and the studio render nothing.
"""
import pathlib
import subprocess
import sys
import tempfile
import types

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "worker"))

import clip.transcribe as transcribe_mod  # noqa: E402
from clip.transcribe import actual_compute, transcribe  # noqa: E402

# Local stand-in only: a publisher trailer, not committed.
TRAILER = ROOT / "fixtures" / "gameplay_4min.mp4"


def test_bridge_failure_falls_back_to_cpu(monkeypatch):
    from worker_app.config import settings

    monkeypatch.setattr(settings, "mlx_whisper_url", "http://127.0.0.1:1")
    monkeypatch.setattr(settings, "whisper_device", "cpu")
    monkeypatch.setattr(settings, "whisper_compute_type", "int8")
    monkeypatch.setattr(
        transcribe_mod,
        "_load",
        lambda *a, **k: types.SimpleNamespace(transcribe=lambda *a, **k: (iter([]), None)),
    )
    assert transcribe("unused.mp4") == []
    assert actual_compute() == ("cpu", "int8")


def test_mlx_configured_but_unreachable_still_uses_cpu(monkeypatch):
    """MLX_WHISPER_URL being set must not make the faster-whisper fallback try
    to open device='mlx'."""
    from worker_app.config import settings

    monkeypatch.setattr(settings, "mlx_whisper_url", "http://127.0.0.1:1")
    monkeypatch.setattr(settings, "whisper_device", "cpu")
    monkeypatch.setattr(settings, "whisper_compute_type", "int8")
    seen = {}

    class FakeModel:
        def __init__(self, model, device=None, compute_type=None):
            seen["device"] = device
            seen["compute_type"] = compute_type

        def transcribe(self, *a, **k):
            return iter([]), None

    monkeypatch.setattr("faster_whisper.WhisperModel", FakeModel)
    assert transcribe("unused.mp4") == []
    assert seen == {"device": "cpu", "compute_type": "int8"}
    assert actual_compute() == ("cpu", "int8")


def test_unload_drops_the_resident_model():
    transcribe_mod._model = object()
    transcribe_mod.unload()
    assert transcribe_mod._model is None


def test_window_transcript_keeps_speech():
    if not TRAILER.exists():
        return
    with tempfile.TemporaryDirectory() as tmp:
        window = str(pathlib.Path(tmp) / "window.mp4")
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "234", "-i", str(TRAILER), "-t", "27",
             "-c", "copy", window],
            check=True, capture_output=True,
        )
        words = transcribe(window)
    assert len(words) > 20, "window transcript lost the dialogue"
