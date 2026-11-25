"""The sampled vision pass: a small VLM proposes extra clips the admin never marked."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "worker"))

from clip import vision  # noqa: E402

JPEG = b"\xff\xd8\xff\xe0fake-jpeg"


class FakeBridge:
    def __init__(self, replies):
        self.replies = replies
        self.unloaded = []

    def describe(self, image, start, end, model):
        return self.replies.get(round(start), {"clippable": False, "score": 0.0, "reason": ""})

    def unload(self, model):
        self.unloaded.append(model)


def _frames(tmp_path, seconds):
    frames = []
    for t in seconds:
        p = tmp_path / f"f{t}.jpg"
        p.write_bytes(JPEG)
        frames.append((float(t), str(p)))
    return frames


def test_ranks_clippable_windows_and_merges_overlaps(tmp_path):
    # Frames at 0,5,10,15 produce windows starting at 0,0,4,9. Only the 4s
    # window is clippable, so exactly one suggestion survives the merge.
    bridge = FakeBridge({4.0: {"clippable": True, "score": 0.9, "reason": "a kill"}})
    frames = _frames(tmp_path, [0, 5, 10, 15])
    suggestions, meta = vision.suggest(
        "unused.mp4",
        top_n=5,
        sampler=lambda path, out: frames,
        describe_fn=bridge.describe,
        unload_fn=bridge.unload,
        model="qwen2.5vl:7b",
    )
    assert len(suggestions) == 1
    assert suggestions[0].start == 4
    assert suggestions[0].reason == "a kill"
    assert suggestions[0].score == 0.9
    assert suggestions[0].thumb_path.endswith(".jpg")
    assert meta["frames"] == 4


def test_unloads_the_vision_model_after_the_pass(tmp_path):
    bridge = FakeBridge({})
    vision.suggest(
        "unused.mp4",
        sampler=lambda path, out: _frames(tmp_path, [0]),
        describe_fn=bridge.describe,
        unload_fn=bridge.unload,
        model="qwen2.5vl:7b",
    )
    assert bridge.unloaded == ["qwen2.5vl:7b"]


def test_reports_seconds_added_and_the_model(tmp_path):
    bridge = FakeBridge({0.0: {"clippable": True, "score": 0.5, "reason": "x"}})
    _, meta = vision.suggest(
        "unused.mp4",
        sampler=lambda path, out: _frames(tmp_path, [0]),
        describe_fn=bridge.describe,
        unload_fn=bridge.unload,
        model="minicpm-v",
    )
    assert meta["model"] == "minicpm-v"
    assert meta["seconds_added"] >= 0
    assert meta["sampled"] is True


def test_skips_windows_the_model_rejects(tmp_path):
    bridge = FakeBridge({})
    suggestions, _ = vision.suggest(
        "unused.mp4",
        sampler=lambda path, out: _frames(tmp_path, [0, 5, 10]),
        describe_fn=bridge.describe,
        unload_fn=bridge.unload,
    )
    assert suggestions == []


def test_prompt_formats_without_raising():
    # The prompt embeds a literal JSON example; .format must not read its braces.
    text = vision.PROMPT.format(start=1.0, end=13.0)
    assert "clippable" in text
    assert "{start" not in text


def test_unload_polls_until_the_model_is_gone(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(vision, "_post", lambda *a, **k: {})
    def fake_get(url, timeout=10):
        calls["n"] += 1
        return {"ollama": {"running": [{"name": "m"}] if calls["n"] == 1 else []}}
    monkeypatch.setattr(vision, "_get", fake_get)
    assert vision.unload("m") is True
    assert calls["n"] == 2


def test_unload_false_when_it_stays_resident(monkeypatch):
    monkeypatch.setattr(vision, "_post", lambda *a, **k: {})
    monkeypatch.setattr(vision, "_get", lambda *a, **k: {"ollama": {"running": [{"name": "m"}]}})
    assert vision.unload("m", timeout=0.2) is False
