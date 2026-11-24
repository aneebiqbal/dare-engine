"""The platform registry: one data source for API validation and worker output."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from platforms import DEFAULT_PLATFORM, PLATFORMS, get, is_valid, public_list  # noqa: E402


def test_registry_has_the_three_targets():
    assert set(PLATFORMS) == {"youtube_shorts", "instagram_reels", "tiktok"}
    assert all(p["aspect"] == "9:16" for p in PLATFORMS.values())
    assert all(p["min_seconds"] <= p["max_seconds"] for p in PLATFORMS.values())


def test_unknown_platform_falls_back_to_the_default():
    assert is_valid("youtube_shorts") is True
    assert is_valid("myspace") is False
    assert get(None)["caption_style"] == PLATFORMS[DEFAULT_PLATFORM]["caption_style"]
    assert get("myspace")["label"] == PLATFORMS[DEFAULT_PLATFORM]["label"]


def test_public_list_puts_the_default_first():
    items = public_list()
    assert items[0]["id"] == DEFAULT_PLATFORM
    assert {p["id"] for p in items} == set(PLATFORMS)


def test_platforms_pick_distinct_caption_styles():
    styles = {p["id"]: p["caption_style"] for p in public_list()}
    assert len(set(styles.values())) >= 2
