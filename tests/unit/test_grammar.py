"""Part B: the grammar is config-driven and opens on the moment."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "worker"))

from clip.grammar import build_beats, get_template, load_templates, pick_template  # noqa: E402


def test_at_least_four_templates_and_three_caption_styles():
    styles, templates = load_templates()
    assert len(templates) >= 4
    assert len(styles) >= 3
    assert all(t.layout and t.captions in styles for t in templates)


def test_pick_template_never_repeats_the_previous_one():
    previous = None
    for i in range(12):
        chosen = pick_template(f"seed-{i}", previous)
        assert chosen.id != previous
        previous = chosen.id


def test_cold_open_is_first_then_context_then_payoff():
    template = get_template("cold_open")
    beats = build_beats(template, peak=30.0, payoff_start=20.0, payoff_end=40.0,
                        context_range=(10.0, 18.0))
    assert [b.kind for b in beats] == ["cold_open", "context", "payoff"]
    # The cold open is the most striking slice of the payoff, on screen first.
    assert abs(beats[0].src_start - (30.0 - template.cold_open / 2.0)) < 1e-6
    assert beats[0].length == template.cold_open


def test_payoff_is_the_longest_beat():
    template = get_template("cold_open")
    beats = build_beats(template, peak=30.0, payoff_start=20.0, payoff_end=40.0,
                        context_range=(10.0, 18.0))
    payoff = beats[-1]
    assert payoff.kind == "payoff"
    assert payoff.length > max(b.length for b in beats[:-1])


def test_no_context_when_there_is_no_setup_range():
    template = get_template("clean")
    beats = build_beats(template, peak=5.0, payoff_start=0.0, payoff_end=20.0,
                        context_range=None)
    assert all(b.kind != "context" for b in beats)


def test_context_is_skipped_when_it_would_overlap_the_payoff():
    template = get_template("clean")
    beats = build_beats(template, peak=5.0, payoff_start=0.0, payoff_end=20.0,
                        context_range=(4.4, 4.5))
    assert all(b.kind != "context" for b in beats)
