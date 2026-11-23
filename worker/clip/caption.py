"""Burn-in captions: an ASS file for FFmpeg/libass, and an SRT sidecar.

Three caption styles (word, line, pop) are chosen so consecutive clips differ.
Captions are word-synced and kept clear of the platform's bottom UI zone.
"""
from __future__ import annotations

from .transcribe import Word

HEADER = """[Script Info]
Title: Short
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,DejaVu Sans,110,&H00FFFFFF,&H000000FF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,4,2,5,240,240,900,1
Style: Word,DejaVu Sans,84,&H0000FFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,0,2,180,180,260,1
Style: Line,DejaVu Sans,64,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,0,2,180,180,320,1
Style: Pop,DejaVu Sans,96,&H0000FFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,180,180,200,1
Style: Karaoke,DejaVu Sans,84,&H0000FFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,0,2,180,180,260,1
Style: End,DejaVu Sans,76,&H00FFFFFF,&H000000FF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,3,1,5,180,180,700,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

EVENT = "Dialogue: 0,{start},{end},{style},{name},0,0,0,,{text}\n"

# Bottom margins keep captions clear of the platform's UI zone.
STYLES = {
    "word": {"ass": "Word", "per": "word", "max_words": 1},
    "line": {"ass": "Line", "per": "phrase", "max_words": 4},
    "pop": {"ass": "Pop", "per": "word", "max_words": 1},
    # Animated word-by-word highlight: each word is a karaoke segment.
    "karaoke": {"ass": "Karaoke", "per": "karaoke", "max_words": 4},
}


def _ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _ass_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")


def group_words(words: list[Word], per: str, max_words: int = 4) -> list[Word]:
    """Group words into caption blocks: one word, or a short phrase."""
    if per == "word" or max_words <= 1:
        return words
    groups: list[Word] = []
    current: list[Word] = []
    for w in words:
        # Close before a word that would overflow the phrase or bridge a pause,
        # so a caption never spans silence.
        if current and (
            len(current) >= max_words or (w.start - current[-1].end) > 1.0
        ):
            groups.append(Word(current[0].start, current[-1].end, " ".join(c.text for c in current)))
            current = []
        current.append(w)
    if current:
        groups.append(Word(current[0].start, current[-1].end, " ".join(c.text for c in current)))
    return groups


def karaoke_groups(words: list[Word], max_words: int = 4) -> list[list[Word]]:
    groups: list[list[Word]] = []
    current: list[Word] = []
    for w in words:
        if current and (
            len(current) >= max_words or (w.start - current[-1].end) > 1.0
        ):
            groups.append(current)
            current = []
        current.append(w)
    if current:
        groups.append(current)
    return groups


def karaoke_text(group: list[Word]) -> str:
    """One ASS event whose words highlight in sequence with `\\k` tags."""
    return " ".join(
        f"{{\\k{max(1, int(round((w.end - w.start) * 100)))}}}{_ass_text(w.text)}"
        for w in group
    )


def write_ass(
    path: str,
    hook_text: str,
    hook_dur: float,
    words: list[Word],
    end_lines: list[str],
    end_start: float,
    total_dur: float,
    caption_style: str = "word",
) -> None:
    style = STYLES.get(caption_style, STYLES["word"])
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
    if style["per"] == "karaoke":
        for group in karaoke_groups(words, style["max_words"]):
            lines.append(
                EVENT.format(
                    start=_ass_time(group[0].start),
                    end=_ass_time(group[-1].end),
                    style=style["ass"],
                    name="",
                    text=karaoke_text(group),
                )
            )
    else:
        for w in group_words(words, style["per"], style["max_words"]):
            lines.append(
                EVENT.format(
                    start=_ass_time(w.start),
                    end=_ass_time(w.end),
                    style=style["ass"],
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


def write_srt(path: str, words: list[Word], caption_style: str = "word") -> None:
    style = STYLES.get(caption_style, STYLES["word"])
    blocks = []
    for i, w in enumerate(group_words(words, style["per"], style["max_words"]), 1):
        blocks.append(
            f"{i}\n{_srt_time(w.start)} --> {_srt_time(w.end)}\n{w.text}\n"
        )
    with open(path, "w") as fh:
        fh.write("\n".join(blocks))
