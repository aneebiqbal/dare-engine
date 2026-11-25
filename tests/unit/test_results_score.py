"""The research-ranking score: views and retention, plus the leading indicators."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))

from app.account import _score  # noqa: E402


def test_base_score_is_unchanged_without_indicators():
    assert _score(1000, 50.0) == 1.5


def test_indicators_raise_the_ranking_score():
    base = _score(1000, 50.0)
    with_indicators = _score(1000, 50.0, swiped=300, saves=12, shares=8)
    assert with_indicators > base
    # retention 1000/1300 + engagement 20/1000
    assert with_indicators == round(base + 1000 / 1300 + 20 / 1000, 4)


def test_a_clip_that_holds_attention_outranks_a_flat_one():
    flat = _score(10_000, 10.0, swiped=90_000, saves=1, shares=0)
    held = _score(10_000, 80.0, swiped=1_000, saves=500, shares=100)
    assert held > flat
