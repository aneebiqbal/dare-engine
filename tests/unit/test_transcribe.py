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
    from app.config import settings

    monkeypatch.setattr(settings, "mlx_whisper_url", "http://127.0.0.1:1")
    monkeypatch.setattr(settings, "whisper_device", "cpu")
    monkeypatch.setattr(settings, "whisper_compute_type", "int8")
    monkeypatch.setattr(
        transcribe_mod,
        "_load",
        lambda: types.SimpleNamespace(transcribe=lambda *a, **k: (iter([]), None)),
    )
    assert transcribe("unused.mp4") == []
    assert actual_compute() == ("cpu", "int8")


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
