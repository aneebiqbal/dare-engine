"""Policy guards.

The spoiler guard drops windows with no speech (a cutscene has no commentary).
Detecting a cutscene by what is on screen needs a visual pass; that limit is
recorded in docs/decisions.md.
"""
from __future__ import annotations

from .transcribe import Word

SPOILER_MIN_WORDS = 1


class SpoilerError(RuntimeError):
    """The window looks like a cutscene: no speech to caption."""


def guard_window(words: list[Word], lo: float, hi: float) -> None:
    spoken = sum(1 for w in words if lo <= (w.start + w.end) / 2 < hi)
    if spoken < SPOILER_MIN_WORDS:
        raise SpoilerError(
            f"no speech between {lo:.1f}s and {hi:.1f}s; treating it as a cutscene"
        )


# Titles are checked here too, so the rule lives in one place.
BANNED_TITLE_WORDS = ("GTA 6", "Grand Theft Auto", "Rockstar")


def title_flags(title: str) -> dict[str, bool]:
    low = title.lower()
    return {
        "trademark": any(w.lower() in low for w in BANNED_TITLE_WORDS),
        "too_long": len(title) > 100,
        "all_caps": title.isupper() and len(title) > 8,
    }
