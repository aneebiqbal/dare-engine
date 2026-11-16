"""M1 acceptance: a video file + a mission card + two timestamps -> a finished Short.

The stand-in fixture is a synthetic test pattern with real recorded speech,
clearly labelled, because `fixtures/stream_10min.mp4` has not been provided.
The real-fixture run is a manual step tracked in PROGRESS.md.
"""
import json
import pathlib
import subprocess
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/standin_speech_45s.mp4"
CARD = ROOT / "tests/fixtures/card.json"


@pytest.fixture(scope="module")
def render():
    # Colima only shares $HOME with the VM, so the output must live under the
    # repo rather than in the system temp dir.
    out = pathlib.Path(tempfile.mkdtemp(prefix="m1-render-", dir=ROOT))
    hf_cache = pathlib.Path.home() / ".cache/huggingface"
    cmd = [
        "docker", "compose", "run", "--rm",
        "-v", f"{FIXTURE}:/fixtures/standin.mp4:ro",
        "-v", f"{CARD}:/fixtures/card.json:ro",
        "-v", f"{out}:/out",
    ]
    if hf_cache.is_dir():
        cmd += ["-v", f"{hf_cache}:/root/.cache/huggingface"]
    cmd += [
        "-e", "HF_HUB_DISABLE_TELEMETRY=1",
        "worker", "python", "-m", "clip.cli",
        "/fixtures/standin.mp4",
        "--start", "5", "--end", "35",
        "--card", "/fixtures/card.json",
        "--out-dir", "/out",
        "--result", "0:41",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, f"clip render failed:\n{proc.stdout}\n{proc.stderr}"
    return out


def probe(path: pathlib.Path) -> dict:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type,codec_name,width,height",
            "-show_entries", "format=duration",
            "-of", "json", str(path),
        ],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def test_is_1080x1920_h264(render):
    data = probe(render / "short.mp4")
    video = [s for s in data["streams"] if s["codec_type"] == "video"][0]
    assert (video["width"], video["height"]) == (1080, 1920)
    assert video["codec_name"] == "h264"


def test_under_60_seconds(render):
    data = probe(render / "short.mp4")
    assert float(data["format"]["duration"]) < 60


def test_has_an_audio_track(render):
    data = probe(render / "short.mp4")
    assert any(s["codec_type"] == "audio" for s in data["streams"])


def test_caption_file_contains_transcript_words(render):
    srt = (render / "captions.srt").read_text().lower()
    assert "bicycle" in srt
    assert "stars" in srt


def test_metadata_written(render):
    meta = json.loads((render / "metadata.json").read_text())
    assert meta["mission_id"] == "m_0214"
    assert meta["title"]
    assert meta["duration_seconds"] < 60


def test_thumbnail_written(render):
    assert (render / "thumb.jpg").stat().st_size > 0
