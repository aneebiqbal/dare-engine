"""Part 6 edge cases: a corrupt/too-short recording and a full disk say so."""
import pathlib
import sys

import pytest
from fastapi import HTTPException

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "worker"))

from app import studio  # noqa: E402


class _Result:
    def __init__(self, stdout):
        self.stdout = stdout


def test_probe_rejects_a_non_video(tmp_path):
    bad = tmp_path / "bad.mp4"
    bad.write_text("not a video")
    with pytest.raises(HTTPException) as exc:
        studio._probe(str(bad))
    assert exc.value.status_code == 422
    assert "not a readable video" in exc.value.detail


def test_probe_rejects_a_too_short_recording(monkeypatch):
    monkeypatch.setattr(
        studio.subprocess,
        "run",
        lambda *a, **k: _Result('{"format":{"duration":"0.4"},"streams":[]}'),
    )
    with pytest.raises(HTTPException) as exc:
        studio._probe("clip.mp4")
    assert exc.value.status_code == 422
    assert "too short" in exc.value.detail


def test_require_disk_raises_when_low(monkeypatch):
    class Usage:
        free = 100_000_000

    monkeypatch.setattr(studio.shutil, "disk_usage", lambda path: Usage())
    with pytest.raises(HTTPException) as exc:
        studio.require_disk("/tmp", needed_mb=500)
    assert exc.value.status_code == 507


def test_require_disk_passes_when_roomy(monkeypatch):
    class Usage:
        free = 10_000_000_000

    monkeypatch.setattr(studio.shutil, "disk_usage", lambda path: Usage())
    studio.require_disk("/tmp", needed_mb=500)


def test_worker_render_refuses_a_full_disk(monkeypatch):
    from worker_app import handlers

    class Usage:
        free = 100_000_000

    monkeypatch.setattr("shutil.disk_usage", lambda path: Usage())
    with pytest.raises(RuntimeError) as exc:
        handlers._require_disk("/tmp", needed_mb=2000)
    assert "not enough free disk space" in str(exc.value)
