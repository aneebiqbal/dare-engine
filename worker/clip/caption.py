"""Burn-in captions: an ASS file for FFmpeg/libass, and an SRT sidecar."""
from __future__ import annotations

from .transcribe import Word

HEADER = """[Script Info]
Title: Clipdesk Missions
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,DejaVu Sans,110,&H00FFFFFF,&H000000FF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,4,2,5,240,240,900,1
Style: Word,DejaVu Sans,84,&H0000FFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,0,2,180,180,260,1
Style: End,DejaVu Sans,76,&H00FFFFFF,&H000000FF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,3,1,5,180,180,700,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

EVENT = "Dialogue: 0,{start},{end},{style},{name},0,0,0,,{text}\n"


def _ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _ass_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")


def write_ass(
    path: str,
    hook_text: str,
    hook_dur: float,
    words: list[Word],
    end_lines: list[str],
    end_start: float,
    total_dur: float,
) -> None:
    lines = [HEADER]
    lines.append(
        EVENT.format(
            start=_ass_time(0),
            end=_ass_time(hook_dur),
            style="Hook",
            name="",
            text=_ass_text(hook_text),
        )
    )
    for w in words:
        lines.append(
            EVENT.format(
                start=_ass_time(w.start),
                end=_ass_time(w.end),
                style="Word",
                name="",
                text=_ass_text(w.text),
            )
        )
    if end_lines:
        lines.append(
            EVENT.format(
                start=_ass_time(end_start),
                end=_ass_time(total_dur + 0.5),
                style="End",
                name="",
                text="\\N".join(_ass_text(line) for line in end_lines),
            )
        )
    with open(path, "w") as fh:
        fh.write("".join(lines))


def _srt_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(path: str, words: list[Word]) -> None:
    blocks = []
    for i, w in enumerate(words, 1):
        blocks.append(
            f"{i}\n{_srt_time(w.start)} --> {_srt_time(w.end)}\n{w.text}\n"
        )
    with open(path, "w") as fh:
        fh.write("\n".join(blocks))
