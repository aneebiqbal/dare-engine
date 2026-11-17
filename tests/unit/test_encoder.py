"""S3: hardware H.264 encoding is detected, with libx264 as the fallback."""
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "worker"))

from clip.engine import codec_args, detect_encoder  # noqa: E402

KNOWN = ("h264_videotoolbox", "h264_nvenc", "h264_qsv", "h264_vaapi", "libx264")


def test_detector_returns_a_known_encoder():
    assert detect_encoder() in KNOWN


def test_libx264_fallback_args():
    assert codec_args("libx264")[:2] == ["-c:v", "libx264"]


def test_hardware_args_use_the_hardware_encoder():
    assert codec_args("h264_videotoolbox")[:2] == ["-c:v", "h264_videotoolbox"]
    assert codec_args("h264_nvenc")[:2] == ["-c:v", "h264_nvenc"]


def _render(encoder: str, out: pathlib.Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30",
            "-t", "1", *codec_args(encoder), "-pix_fmt", "yuv420p", str(out),
        ],
        capture_output=True, check=True,
    )


def test_software_path_produces_a_valid_file(tmp_path):
    out = tmp_path / "sw.mp4"
    _render("libx264", out)
    assert "h264" in subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(out)],
        capture_output=True, text=True, check=True,
    ).stdout


@pytest.mark.skipif(
    subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
    .stderr.find("h264_videotoolbox") < 0,
    reason="no hardware encoder on this machine",
)
def test_hardware_path_produces_a_valid_file(tmp_path):
    out = tmp_path / "hw.mp4"
    _render("h264_videotoolbox", out)
    assert "h264" in subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(out)],
        capture_output=True, text=True, check=True,
    ).stdout
