"""Transcript-first moment selection: sentences, windows, fusion, rubric."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "worker"))
sys.path.insert(0, str(ROOT / "shared"))

from clip import local_scoring, pipeline, regions, select  # noqa: E402
from clip.transcribe import Word  # noqa: E402


def _words(script, wpm=150):
    """Rough word list with timings, one word every ~0.4s."""
    out = []
    t = 0.0
    for token in script.split():
        out.append(Word(t, t + 0.35, token))
        t += 0.4
    return out, t


def test_sentences_split_on_punctuation_and_pauses():
    words, _ = _words("I lost everything. Then I found it! And we won?")
    sentences = select.segment_sentences(words)
    joined = " ".join(s.text for s in sentences)
    assert len(sentences) == 3
    assert "lost everything" in sentences[0].text
    assert sentences[-1].text.endswith("won?")


def test_windows_are_min_length_and_sentence_aligned():
    script = (
        "I was completely broke last year and nobody believed I could come back. "
        "Then I found one mistake that changed everything for me. "
        "Now I make more money than my old boss and I want to show you how. "
        "First you need to stop doing the obvious thing everyone else does. "
        "The second step is the part nobody talks about because it actually works."
    )
    words, duration = _words(script)
    sentences = select.segment_sentences(words)
    windows = select.grow_windows(sentences, min_seconds=14.0)
    assert windows
    for w in windows:
        assert w.duration >= 14.0 - 1e-6, w
        assert w.duration <= 60.0 + 1e-6, w
        # Edges land on sentence starts/ends, never mid-word.
        assert any(abs(s.start - w.start) < 1e-6 for s in sentences), w
        assert any(abs(s.end - w.end) < 1e-6 for s in sentences), w


def test_nms_drops_overlaps_and_caps():
    windows = [
        select.Window(10, 25, "a", 20, 2.0, 1.0),
        select.Window(12, 27, "b", 20, 2.0, 0.9),
        select.Window(100, 115, "c", 20, 2.0, 0.8),
    ]
    kept = select.non_max_suppress(windows)
    assert len(kept) == 2
    assert kept[0].start == 10 and kept[-1].start == 100


def test_event_timeline_mentions_audio_visual_and_vision():
    energy = [-40.0] * 60
    energy[20] = -10.0
    scenes = [18.0, 40.0]
    speech = [1.0] * 60
    window = select.Window(10.0, 30.0, "x", 5, 1.0, 1.0)
    text = select.event_timeline(
        window, energy=energy, scenes=scenes, speech=speech,
        vision_note="character reaction",
    )
    assert "audio:" in text and "visual:" in text and "vision:" in text
    assert "character reaction" in text


def test_regions_skip_music_only_and_honour_budget():
    speech = [0.0] * 100 + [1.0] * 100 + [0.0] * 100
    energy = [-20.0] * 300
    scenes = [50.0, 150.0, 250.0]
    regs = regions.plan_regions(speech, energy, scenes, 300.0, max_audio_seconds=1000.0)
    assert regs
    assert all(r.speech_fraction >= 0.2 for r in regs)
    assert sum(r.end - r.start for r in regs) <= 1000.0
    assert not regions.plan_regions([0.0] * 100, [-20.0] * 100, [], 100.0)


def test_regions_handles_mismatched_signal_lengths():
    # Audio-derived signals can be a second shorter than the container duration.
    regs = regions.plan_regions([1.0] * 50, [-20.0] * 30, [], 50.0)
    assert regs
    assert regs[-1].end <= 50.0


def test_rubric_composite_and_kill_criteria(monkeypatch):
    captured = {}

    def fake_post(messages, temperature, timeout=300):
        captured["temperature"] = temperature
        return json.dumps(
            {
                "start": 0, "end": 20, "label": "insight",
                "hook": "Nobody talks about this",
                "reason": "strong hook and payoff",
                "scores": {
                    "hook_strength": 9, "emotional_peak": 8, "payoff_delivery": 8,
                    "standalone_clarity": 8, "pace_energy": 7, "quotability": 8,
                    "length_fit": 8,
                },
                "composite": 80, "keep": True,
            }
        )

    monkeypatch.setattr(local_scoring, "_post", fake_post)
    data = local_scoring.score_window("text", "timeline", "en")
    assert abs(data["composite"] - 81.5) < 0.6  # weighted sum x 10
    assert data["keep"] is True
    assert captured["temperature"] == local_scoring.settings.score_temperature

    weak = dict(json.loads(fake_post([], 0)))
    weak["scores"] = {k: 2 for k in local_scoring.DIMENSIONS}
    monkeypatch.setattr(
        local_scoring, "_post",
        lambda *a, **k: json.dumps({**weak, "keep": True, "composite": 20}),
    )
    rejected = local_scoring.score_window("text", "", "en")
    assert rejected["keep"] is False


def test_rerank_orders_relatively(monkeypatch):
    monkeypatch.setattr(
        local_scoring, "_post",
        lambda *a, **k: json.dumps({"order": [30, 10], "drop": [20]}),
    )
    items = [{"start": s} for s in (10, 20, 30)]
    result = local_scoring.rerank(items)
    assert result["order"][0] == 30
    assert 20 in result["drop"]
    assert set(result["order"]) == {10, 30}


def test_language_is_passed_to_the_scoring_prompt(monkeypatch):
    seen = {}

    def fake_post(messages, temperature, timeout=300):
        seen["system"] = messages[0]["content"]
        return json.dumps(
            {"start": 0, "end": 20, "label": "insight", "hook": "x",
             "reason": "ok", "scores": {k: 7 for k in local_scoring.DIMENSIONS},
             "composite": 70, "keep": True}
        )

    monkeypatch.setattr(local_scoring, "_post", fake_post)
    local_scoring.score_window("Nadie sabía esto", "", "es")
    assert "es" in seen["system"].lower()


def test_sane_language_rejects_mislabelled_english():
    words = [Word(i * 0.4, i * 0.4 + 0.35, t) for i, t in enumerate(
        "I have to fix your car because the engine is giving up on me".split()
    )]
    assert pipeline.sane_language("ur", words) == "en"
    assert pipeline.sane_language("es", words) == "es"


def test_clean_words_strips_wrong_script_hallucinations():
    words = [
        pipeline.Word(0.0, 0.3, "hello"),
        pipeline.Word(0.4, 0.7, "دوسرا"),
        pipeline.Word(0.8, 1.1, "world"),
    ]
    kept = pipeline._clean_words(words, "en")
    assert [w.text for w in kept] == ["hello", "world"]
    # A genuinely Urdu run keeps its words.
    assert pipeline._clean_words(words, "ur") == words


def test_skill_files_exist_and_are_the_tuning_surface():
    base = ROOT / "skills" / "clip-scoring"
    skill = (base / "SKILL.md").read_text()
    rubric = (base / "rubric.md").read_text()
    score = (base / "prompt_score.md").read_text()
    rerank = (base / "prompt_rerank.md").read_text()
    assert "weight" in rubric.lower() and "kill criteria" in rubric.lower()
    assert "composite" in score and '"scores"' in score
    assert "order" in rerank and "drop" in rerank
    assert local_scoring.WEIGHTS
    assert abs(sum(local_scoring.WEIGHTS.values()) - 1.0) < 1e-9


def test_no_internal_branding_is_burned():
    card = {"id": "clip_1", "hook_text": "Watch", "question": "",
            "title_options": ["Watch"], "mode": "auto", "end_lines": []}
    from clip.engine import _render_window  # noqa: F401  (import sanity)

    assert card["end_lines"] == []
    caption = (ROOT / "worker" / "clip" / "caption.py").read_text()
    assert "Clipdesk Missions" not in caption
    engine = (ROOT / "worker" / "clip" / "engine.py").read_text()
    assert "MISSION" not in engine
