"""Unit tests for the policy guards and layout rotation named in the spec."""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "worker"))

from clip.layout import LAYOUTS, filtergraph, pick_layout  # noqa: E402
from clip.policy import SpoilerError, guard_window, title_flags  # noqa: E402
from clip.transcribe import Word  # noqa: E402


def test_layouts_rotate():
    picks = {pick_layout(f"m_{i}") for i in range(24)}
    assert len(picks) > 1
    assert picks <= set(LAYOUTS)


def test_landscape_sources_are_never_letterboxed():
    picks = {pick_layout(f"m_{i}", landscape=True) for i in range(24)}
    assert "fit_height" not in picks


def test_layout_is_stable():
    assert pick_layout("m_0214:5:35") == pick_layout("m_0214:5:35")


def test_every_layout_has_a_filtergraph():
    for layout in LAYOUTS:
        assert filtergraph(layout).endswith("[v]")


def test_spoiler_guard_rejects_silence():
    with pytest.raises(SpoilerError):
        guard_window([], 0.0, 10.0)


def test_spoiler_guard_accepts_speech():
    guard_window([Word(1.0, 2.0, "hello")], 0.0, 10.0)


def test_title_flags_trademark():
    flags = title_flags("Can you escape 5 stars on a BIKE in GTA 6?")
    assert flags["trademark"] is True
    assert title_flags("Can you escape 5 stars on a bike?")["trademark"] is False
