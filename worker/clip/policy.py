"""Policy guards.

Two cutscene signals: no speech (a cutscene has no commentary) and letterbox /
black bars (a cinematic crop). Letterbox is flagged for review rather than
dropped, because it has not been checked on real footage yet.
"""
from __future__ import annotations

import re
import subprocess

from .transcribe import Word

SPOILER_MIN_WORDS = 1
LETTERBOX_BLACK_FRACTION = 0.15


class SpoilerError(RuntimeError):
    """The window looks like a cutscene: no speech to caption."""


def guard_window(words: list[Word], lo: float, hi: float) -> None:
    spoken = sum(1 for w in words if lo <= (w.start + w.end) / 2 < hi)
    if spoken < SPOILER_MIN_WORDS:
        raise SpoilerError(
            f"no speech between {lo:.1f}s and {hi:.1f}s; treating it as a cutscene"
        )


def detect_letterbox(video_path: str, width: int, height: int, at: float | None = None) -> dict:
    """Use FFmpeg cropdetect to measure black bars. Flags, never drops."""
    cmd = ["ffmpeg", "-hide_banner", "-nostats"]
    if at is not None:
        cmd += ["-ss", f"{at:.3f}"]
    cmd += [
        "-i", video_path,
        "-vf", "cropdetect=limit=0.08:round=2",
        "-frames:v", "20", "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    crops = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", proc.stderr)
    if not crops:
        return {"letterbox": False, "black_fraction": 0.0, "crop": None}
    cw, ch, cx, cy = (int(v) for v in crops[-1])
    fraction = 1.0 - (cw * ch) / (width * height)
    return {
        "letterbox": fraction > LETTERBOX_BLACK_FRACTION,
        "black_fraction": round(fraction, 4),
        "crop": {"w": cw, "h": ch, "x": cx, "y": cy},
    }


# Titles are checked here too, so the rule lives in one place.
BANNED_TITLE_WORDS = ("GTA 6", "Grand Theft Auto", "Rockstar")


def title_flags(title: str) -> dict[str, bool]:
    low = title.lower()
    return {
        "trademark": any(w.lower() in low for w in BANNED_TITLE_WORDS),
        "too_long": len(title) > 100,
        "all_caps": title.isupper() and len(title) > 8,
    }
