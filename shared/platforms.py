"""Platform presets: what each social target wants from a clip.

One registry, imported by the API and the worker, so adding a platform is a
data change and never a code fork. The worker reads `max_seconds` when it grows
windows and `caption_style` when it renders; the API validates user input against
the same dict.
"""
from __future__ import annotations

DEFAULT_PLATFORM = "youtube_shorts"

PLATFORMS: dict[str, dict] = {
    "youtube_shorts": {
        "label": "YouTube Shorts",
        "aspect": "9:16",
        "width": 1080,
        "height": 1920,
        "min_seconds": 14,
        "max_seconds": 60,
        "hook_seconds": 2.0,
        "caption_style": "word",
        "hint": "Cold open fast, word-by-word captions, under a minute.",
    },
    "instagram_reels": {
        "label": "Instagram Reels",
        "aspect": "9:16",
        "width": 1080,
        "height": 1920,
        "min_seconds": 14,
        "max_seconds": 90,
        "hook_seconds": 3.0,
        "caption_style": "line",
        "hint": "A beat longer to set the scene, clean line captions, up to 90 s.",
    },
    "tiktok": {
        "label": "TikTok",
        "aspect": "9:16",
        "width": 1080,
        "height": 1920,
        "min_seconds": 14,
        "max_seconds": 60,
        "hook_seconds": 1.5,
        "caption_style": "pop",
        "hint": "First second sells it, bold pop captions, under a minute.",
    },
}


def is_valid(platform: str | None) -> bool:
    return platform in PLATFORMS


def get(platform: str | None) -> dict:
    """The preset for a platform, falling back to the default (never raises)."""
    return PLATFORMS.get(platform or DEFAULT_PLATFORM) or PLATFORMS[DEFAULT_PLATFORM]


def public_list() -> list[dict]:
    """The registry as the web client sees it, default first."""
    items = [dict(id=name, **preset) for name, preset in PLATFORMS.items()]
    items.sort(key=lambda p: (p["id"] != DEFAULT_PLATFORM, p["id"]))
    return items
