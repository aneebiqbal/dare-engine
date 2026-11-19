"""The SSD bridge: list/probe a mounted volume, import locally, refuse escapes."""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "local"))

import ssd_bridge  # noqa: E402
from app import ssd  # noqa: E402

FIXTURE = ROOT / "fixtures" / "gameplay_4min.mp4"


def _video(path: pathlib.Path) -> None:
    path.write_bytes(FIXTURE.read_bytes())


def test_lists_and_probes_a_mounted_volume(tmp_path, monkeypatch):
    volume = tmp_path / "TestSSD"
    volume.mkdir()
    _video(volume / "gameplay.mp4")
    monkeypatch.setattr(ssd_bridge, "MOUNT", tmp_path)
    drives = ssd_bridge.drives()
    assert len(drives) == 1
    video = drives[0]["videos"][0]
    assert video["name"] == "gameplay.mp4"
    assert video["width"] == 1280 and video["height"] == 720
    assert video["duration_seconds"] > 200


def test_import_copies_into_the_shared_inbox(tmp_path, monkeypatch):
    source = tmp_path / "drive" / "clip.mp4"
    source.parent.mkdir()
    _video(source)
    monkeypatch.setattr(ssd_bridge, "MOUNT", tmp_path / "drive")
    inbox = tmp_path / "inbox"
    monkeypatch.setattr(ssd_bridge, "INBOX", inbox)
    out = ssd_bridge.import_file(str(source))
    copied = inbox / out["filename"]
    assert copied.exists() and copied.stat().st_size == FIXTURE.stat().st_size
    assert out["name"] == "clip.mp4"


def test_import_refuses_a_path_outside_the_mount(tmp_path, monkeypatch):
    outside = tmp_path / "outside.mp4"
    _video(outside)
    monkeypatch.setattr(ssd_bridge, "MOUNT", tmp_path / "drive")
    with pytest.raises(ValueError):
        ssd_bridge.import_file(str(outside))


def test_api_reports_a_clear_error_when_the_bridge_is_down(monkeypatch):
    monkeypatch.setattr(ssd.settings, "ssd_bridge_url", "http://localhost:1")
    monkeypatch.setattr(ssd, "current_user", lambda request: {"id": "u", "role": "admin"})
    out = ssd.ssd_drives(None)
    assert out["enabled"] is True
    assert out["error"]
    assert out["how_to"]
