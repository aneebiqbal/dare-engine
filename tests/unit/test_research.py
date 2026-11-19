"""The research brain: sourced ideas, citation filtering and schema validation."""
import importlib.util
import json
import pathlib
import sys

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))

# The API imports the shared client as `llm_shared`; load it the same way the
# worker unit tests do.
_spec = importlib.util.spec_from_file_location("llm_shared", ROOT / "shared" / "llm.py")
llm_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(llm_shared)
sys.modules["llm_shared"] = llm_shared

from app import missions, research  # noqa: E402

RECORDED = json.loads((ROOT / "api" / "app" / "llm_recorded.json").read_text())


def _full_card(card: dict) -> dict:
    card = dict(card)
    card.setdefault("id", "m_1000")
    card.setdefault("status", "unverified")
    card.setdefault("evidence", {"askers": 0, "source_video_ids": []})
    card.setdefault("policy", {"spoiler": False, "online_exploit": False})
    return card


def test_sample_feed_has_all_three_sources():
    sources = research.sample_feed()
    assert {"youtube", "reddit", "news"} <= {s["kind"] for s in sources}
    assert len({s["url"] for s in sources}) == len(sources)


def test_gather_sources_uses_the_sample_feed_without_keys(monkeypatch):
    monkeypatch.setattr(research.settings, "llm_provider", "recorded")
    monkeypatch.setattr(research.settings, "youtube_api_key", "")
    monkeypatch.setattr(research.settings, "reddit_client_id", "")
    monkeypatch.setattr(research.settings, "reddit_client_secret", "")
    sources, fallback = research.gather_sources({"name": "X", "slug": "x"})
    assert fallback is True
    assert sources == research.sample_feed()


def test_generate_ideas_cites_only_real_sources(monkeypatch):
    sample = research.sample_feed()
    monkeypatch.setattr(research, "run_ai", lambda *a, **k: (RECORDED["research"], False))
    ideas, fallback = research.generate_ideas(
        {"name": "Grand Theft Auto V", "slug": "gta-v"}, sample
    )
    assert fallback is False
    assert len(ideas) == 3
    urls = {s["url"] for s in sample}
    for idea in ideas:
        assert idea["source_urls"], "an idea with no source must be dropped"
        assert set(idea["source_urls"]) <= urls
        jsonschema.validate(_full_card(idea["card"]), research.CARD_SCHEMA)


def test_generate_ideas_drops_an_uncited_idea(monkeypatch):
    sample = research.sample_feed()
    response = {
        "ideas": [
            {
                "question": "A real cited idea?",
                "hook_text": "REAL",
                "setup": "Do the thing.",
                "win_condition": "Finish it.",
                "result_type": "pass_fail",
                "est_minutes": 5,
                "title_options": ["A real cited idea?"],
                "mode": "free_roam",
                "source_urls": [sample[0]["url"]],
            },
            {
                "question": "An uncited idea?",
                "hook_text": "FAKE",
                "setup": "Do the thing.",
                "win_condition": "Finish it.",
                "result_type": "pass_fail",
                "est_minutes": 5,
                "title_options": ["An uncited idea?"],
                "mode": "free_roam",
                "source_urls": ["https://example.com/not-in-the-feed"],
            },
        ]
    }
    monkeypatch.setattr(research, "run_ai", lambda *a, **k: (response, False))
    ideas, _ = research.generate_ideas({"name": "X", "slug": "x"}, sample)
    assert len(ideas) == 1
    assert ideas[0]["source_urls"] == [sample[0]["url"]]


def test_generate_ideas_flags_a_fallback(monkeypatch):
    monkeypatch.setattr(research, "run_ai", lambda *a, **k: (None, True))
    ideas, fallback = research.generate_ideas({"name": "X", "slug": "x"}, research.sample_feed())
    assert ideas == []
    assert fallback is True


def test_card_svg_escapes_markup():
    svg = missions._card_svg(
        {
            "hook_text": "<b>HI</b>",
            "question": "Q",
            "win_condition": "W",
            "mode": "free_roam",
            "id": "m_1",
        },
        "Game",
    )
    # The hook is escaped before it is upper-cased and truncated.
    assert "&LT;B&GT;HI&LT;/B&GT;" in svg
    assert "<b>" not in svg


def test_wrap_breaks_long_lines():
    lines = missions._wrap("one two three four five", 10)
    assert lines
    assert all(len(line) <= 10 for line in lines)
