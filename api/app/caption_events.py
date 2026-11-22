"""Turn a clip's transcript into editable caption events.

The worker burns captions grouped by style; the editor shows the same grouping
so what you edit is what was rendered. Plain dicts, so the API image does not
need the worker package.
"""
from __future__ import annotations

# Mirrors worker/clip/caption.py STYLES (per, max_words).
STYLES = {
    "word": ("word", 1),
    "line": ("phrase", 4),
    "pop": ("word", 1),
    "karaoke": ("phrase", 4),
    "none": ("word", 1),
}


def group(words: list[dict], caption_style: str = "word") -> list[dict]:
    per, max_words = STYLES.get(caption_style, STYLES["word"])
    if per == "word" or max_words <= 1:
        return [
            {"start": float(w["start"]), "end": float(w["end"]), "text": str(w.get("text", ""))}
            for w in words
        ]
    groups: list[dict] = []
    current: list[dict] = []
    for word in words:
        if current and (
            len(current) >= max_words
            or (float(word["start"]) - float(current[-1]["end"])) > 1.0
        ):
            groups.append(_merge(current))
            current = []
        current.append(word)
    if current:
        groups.append(_merge(current))
    return groups


def _merge(words: list[dict]) -> dict:
    return {
        "start": float(words[0]["start"]),
        "end": float(words[-1]["end"]),
        "text": " ".join(str(w.get("text", "")) for w in words),
    }
