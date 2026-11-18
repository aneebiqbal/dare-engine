"""Part A: the detector returns ranked windows and reports its compute path."""
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "worker"))

from clip.detect import detect_compute_path, detect_moments, _marker_seconds  # noqa: E402
from clip.transcribe import Word, whisper_compute  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "standin_speech_45s.mp4"


def test_compute_path_is_explicit():
    cp = detect_compute_path()
    assert cp.whisper_device in ("cpu", "cuda")
    assert cp.whisper_compute_type
    assert cp.encoder


def test_whisper_compute_uses_cuda_when_a_gpu_is_present(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "whisper_device", "cpu")
    monkeypatch.setattr(settings, "whisper_compute_type", "int8")
    fake = types.SimpleNamespace(get_cuda_device_count=lambda: 1)
    monkeypatch.setitem(sys.modules, "ctranslate2", fake)
    assert whisper_compute() == ("cuda", "float16")


def test_whisper_compute_falls_back_to_cpu_int8(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "whisper_device", "cpu")
    monkeypatch.setattr(settings, "whisper_compute_type", "int8")
    fake = types.SimpleNamespace(get_cuda_device_count=lambda: 0)
    monkeypatch.setitem(sys.modules, "ctranslate2", fake)
    assert whisper_compute() == ("cpu", "int8")


def test_compute_path_agrees_with_the_whisper_path(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "whisper_device", "cpu")
    monkeypatch.setattr(settings, "whisper_compute_type", "int8")
    fake = types.SimpleNamespace(get_cuda_device_count=lambda: 1)
    monkeypatch.setitem(sys.modules, "ctranslate2", fake)
    cp = detect_compute_path()
    assert (cp.whisper_device, cp.whisper_compute_type) == whisper_compute()


def test_marker_seconds():
    words = [
        Word(0.0, 0.5, "oh"),
        Word(0.5, 1.0, "my"),
        Word(1.0, 1.5, "god"),
        Word(2.0, 2.5, "wow"),
    ]
    assert _marker_seconds(words) == {0, 2}


def test_detect_moments_returns_ranked_non_overlapping_windows():
    candidates, compute = detect_moments(str(FIXTURE), top_n=3)
    assert candidates
    assert all(c.start < c.end for c in candidates)
    assert all(c.score > 0 for c in candidates)
    assert all(c.reasons for c in candidates)
    for a, b in zip(candidates, candidates[1:]):
        assert a.end <= b.start
    # deterministic: the same file gives the same top score
    again, _ = detect_moments(str(FIXTURE), top_n=3)
    assert round(again[0].score, 6) == round(candidates[0].score, 6)
