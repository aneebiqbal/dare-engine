"""Beat selection: the LLM when a key exists, word density as the fallback."""
from __future__ import annotations

import json

from .transcribe import Word

SETUP_CLIP = 3.0
SETUP_COUNT = 3
SETUP_GAP = 2.0

SYSTEM = (
    "You edit gameplay Shorts. Pick the short setup moments that best explain "
    "what is about to happen. Return JSON only."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "setup": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {"start": {"type": "number"}, "end": {"type": "number"}},
                "required": ["start", "end"],
            },
        }
    },
    "required": ["setup"],
}


def transcript(words: list[Word], lo: float, hi: float) -> str:
    return " ".join(w.text for w in words if lo <= (w.start + w.end) / 2 < hi)


def _density_setup(words: list[Word], lo: float, hi: float) -> list[tuple[float, float]]:
    if hi - lo < SETUP_CLIP:
        return []
    candidates: list[tuple[int, float]] = []
    t = lo
    while t + SETUP_CLIP <= hi + 1e-6:
        n = sum(1 for w in words if t <= (w.start + w.end) / 2 < t + SETUP_CLIP)
        if n >= 2:
            candidates.append((n, t))
        t += 1.0
    candidates.sort(reverse=True)
    chosen: list[tuple[float, float]] = []
    for _n, start in candidates:
        if all(abs(start - c[0]) >= SETUP_GAP for c in chosen):
            chosen.append((start, start + SETUP_CLIP))
        if len(chosen) >= SETUP_COUNT:
            break
    chosen.sort()
    return chosen


def select_setup(
    words: list[Word], lo: float, hi: float, llm=None
) -> list[tuple[float, float]]:
    """LLM first; if it is missing or fails, fall back to word density."""
    if llm is not None and hi - lo >= SETUP_CLIP:
        try:
            result = llm.complete_json(
                SYSTEM,
                f"Window {lo:.1f}s to {hi:.1f}s. Transcript: {transcript(words, lo, hi)}",
                SCHEMA,
            )
            spans = [
                (float(s["start"]), float(s["end"]))
                for s in result.get("setup", [])
                if 0 < float(s["end"]) - float(s["start"]) <= SETUP_CLIP + 0.5
            ]
            if spans:
                return sorted(spans)[:SETUP_COUNT]
        except Exception:
            pass  # a missing key or a bad response falls back to density
    return _density_setup(words, lo, hi)
