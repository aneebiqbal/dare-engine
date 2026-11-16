"""Unit tests for the policy guards and layout rotation named in the spec."""
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "worker"))

from clip.beats import select_setup  # noqa: E402
from clip.layout import LAYOUTS, filtergraph, pick_layout  # noqa: E402
from clip.policy import SpoilerError, detect_letterbox, guard_window, title_flags  # noqa: E402
from clip.transcribe import Word  # noqa: E402

STANDIN = ROOT / "tests/fixtures/standin_speech_45s.mp4"


def _letterboxed(path: pathlib.Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=1920x816:rate=30",
            "-t", "2", "-vf", "pad=1920:1080:0:132:color=black",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            str(path),
        ],
        capture_output=True, check=True,
    )


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


def test_letterboxed_frame_is_flagged(tmp_path):
    video = tmp_path / "letterboxed.mp4"
    _letterboxed(video)
    flags = detect_letterbox(str(video), 1920, 1080)
    assert flags["letterbox"] is True
    assert flags["black_fraction"] > 0.15


def test_full_frame_is_not_flagged():
    flags = detect_letterbox(str(STANDIN), 1920, 1080)
    assert flags["letterbox"] is False


def test_setup_falls_back_to_word_density():
    words = [Word(float(i), float(i) + 0.4, f"w{i}") for i in range(0, 10)]
    spans = select_setup(words, 0.0, 10.0)
    assert spans
    assert all(0 <= s < e <= 10.0 for s, e in spans)


def test_setup_uses_the_llm_when_it_answers():
    class FakeLLM:
        def complete_json(self, system, user, schema=None):
            return {"setup": [{"start": 1.0, "end": 4.0}]}

    words = [Word(0.0, 0.4, "w")]
    assert select_setup(words, 0.0, 10.0, FakeLLM()) == [(1.0, 4.0)]


def test_setup_falls_back_when_the_llm_fails():
    class BadLLM:
        def complete_json(self, system, user, schema=None):
            raise RuntimeError("no key")

    words = [Word(float(i), float(i) + 0.4, f"w{i}") for i in range(0, 10)]
    assert select_setup(words, 0.0, 10.0, BadLLM())
