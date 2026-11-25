"""The automatic pipeline: sequencing, resume, cheap scan and edge handling."""
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "worker"))
sys.path.insert(0, str(ROOT / "shared"))

from clip import pipeline, scan, vision  # noqa: E402


def _video(path: pathlib.Path, seconds: int = 8) -> pathlib.Path:
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-nostats",
         "-f", "lavfi", "-i", f"testsrc=duration={seconds}:size=320x240:rate=10",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
         "-shortest", str(path)],
        capture_output=True, check=True,
    )
    return path


# ------------------------------------------------------------------ sequencing


def test_stage_order_is_the_published_pipeline():
    assert pipeline.WORK_STAGES == [
        "ingest", "scan", "regions", "detect", "signals", "score", "cut", "render",
    ]


def test_progress_is_monotonic_across_a_stage():
    values = [pipeline.progress_for(stage, f) for stage in pipeline.WORK_STAGES for f in (0.0, 0.5, 1.0)]
    assert values == sorted(values)
    assert pipeline.progress_for("ingest", 0.0) == 0
    assert pipeline.progress_for("render", 1.0) == 100


def test_estimate_grows_with_duration_and_clip_count():
    small = pipeline.estimate_total(60, 40, 20, 5)
    long = pipeline.estimate_total(7200, 3000, 60, 10)
    many = pipeline.estimate_total(60, 40, 20, 20)
    assert small < long
    assert small < many
    assert all(v > 0 for v in (small, long, many))


# --------------------------------------------------------------------- resume


def test_resume_runs_only_incomplete_stages(monkeypatch):
    calls = []
    run = {
        "id": "r1", "state": "running", "top_n": 5,
        "stage_timings": {"ingest": 1.0, "scan": 2.0},
        "action": "Resuming", "timestamps": [],
        "signals": {"energy": [], "scenes": [], "speech": []},
    }
    class FakeReporter:
        def __init__(self, *a, **k):
            pass

        def action(self, *a, **k):
            pass

        def progress(self, *a, **k):
            pass

        def complete(self, stage, seconds, text):
            pass

    monkeypatch.setattr(pipeline, "_get_run", lambda rid: run)
    monkeypatch.setattr(pipeline, "_update_run", lambda rid, fields: None)
    monkeypatch.setattr(pipeline, "Reporter", FakeReporter)
    monkeypatch.setattr(pipeline, "_finish", lambda ctx: calls.append("done"))
    monkeypatch.setattr(
        pipeline, "STAGE_FN",
        {s: (lambda ctx, s=s: calls.append(s)) for s in pipeline.WORK_STAGES},
    )
    pipeline.run_pipeline("r1")
    assert calls == [
        "regions", "detect", "signals", "score", "cut", "render", "done",
    ]


def test_done_run_is_a_no_op(monkeypatch):
    monkeypatch.setattr(pipeline, "_get_run", lambda rid: {"state": "done"})
    called = []
    monkeypatch.setattr(pipeline, "_update_run", lambda *a: called.append(a))
    pipeline.run_pipeline("r1")
    assert called == []


# ------------------------------------------------------------------ cheap scan


def test_cheap_scan_never_loads_a_model(tmp_path, monkeypatch):
    """The whole-video scan is FFmpeg only: a broken Whisper must not matter."""
    video = _video(tmp_path / "clip.mp4")

    def boom(*a, **k):
        raise AssertionError("the cheap scan must not transcribe")

    from clip import detect

    monkeypatch.setattr(detect, "transcribe", boom)
    result = scan.cheap_scan(str(video))
    assert result.duration >= 7.0
    assert result.candidates
    assert all(c.start < c.end for c in result.candidates)


def test_speech_activity_marks_silence_without_a_model(tmp_path):
    silent = tmp_path / "silent.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-nostats",
         "-f", "lavfi", "-i", "testsrc=duration=6:size=320x240:rate=10",
         "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
         "-shortest", str(silent)],
        capture_output=True, check=True,
    )
    active = scan.speech_activity(str(silent))
    assert len(active) >= 5
    assert sum(active) == 0


def test_a_silent_video_is_flagged_and_still_scanned(tmp_path):
    silent = tmp_path / "silent.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-nostats",
         "-f", "lavfi", "-i", "testsrc=duration=8:size=320x240:rate=10",
         "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
         "-shortest", str(silent)],
        capture_output=True, check=True,
    )
    result = scan.cheap_scan(str(silent))
    assert result.no_speech is True
    assert result.candidates


def test_a_missing_source_volume_pauses_instead_of_crashing(tmp_path, monkeypatch):
    from worker_app import storage

    def boom(*a, **k):
        raise OSError("volume gone")

    monkeypatch.setattr(storage, "get_file", boom)
    ctx = pipeline.Ctx(
        run={"id": "r1", "source_key": "projects/r1/source.mp4"},
        work=str(tmp_path),
        reporter=object(),
    )
    with pytest.raises(pipeline.PipelinePaused):
        pipeline._ensure_source(ctx)


# --------------------------------------------------------------------- ranking


def test_user_timestamps_are_added_and_out_of_range_ignored():
    candidates = [scan.CheapCandidate(10, 22, 5.0, ["loud moment"])]
    ranked, notes = scan.rank_candidates(
        candidates, [{"start": 100, "end": 110}, {"start": 190, "end": 205}], duration=200
    )
    starts = [(round(r.start), round(r.end)) for r in ranked]
    assert (100, 110) in starts
    assert any("outside the video" in n for n in notes)
    # The AI suggestion survives alongside the user's window.
    assert any(r.origin == "ai" for r in ranked)
    assert any(r.origin == "user" for r in ranked)


def test_overlapping_candidates_are_deduplicated():
    candidates = [
        scan.CheapCandidate(10, 22, 5.0, []),
        scan.CheapCandidate(11, 23, 4.0, []),
        scan.CheapCandidate(40, 52, 3.0, []),
    ]
    ranked, _ = scan.rank_candidates(candidates, [], duration=60)
    assert len(ranked) == 2


def test_fallback_hook_picks_the_densest_phrase():
    words = [
        pipeline.Word(0.0, 0.4, "okay"),
        pipeline.Word(1.0, 1.2, "that"),
        pipeline.Word(1.2, 1.4, "was"),
        pipeline.Word(1.4, 1.6, "insane"),
    ]
    assert "insane" in pipeline._fallback_hook(words)
    assert pipeline._fallback_hook([]) == "Watch this"


def test_render_cut_builds_a_vertical_short_from_a_cached_cut(tmp_path):
    from clip.engine import render_cut
    from clip.transcribe import Word

    src = _video(tmp_path / "src.mp4", seconds=12)
    cut = tmp_path / "cut.mp4"
    pipeline._cut_window(str(src), str(cut), 2.0, 10.0)
    result = render_cut(
        str(cut),
        [Word(0.5, 0.9, "hello"), Word(1.0, 1.4, "world")],
        {
            "id": "pipe_1", "hook_text": "hello world", "question": "",
            "title_options": [""], "mode": "auto",
            "end_lines": ["CLIPDESK", "Clip 1"],
        },
        str(tmp_path / "out"),
    )
    assert pathlib.Path(result.out_path).is_file()
    assert pathlib.Path(result.thumb_path).is_file()
    assert pathlib.Path(result.srt_path).is_file()
    assert pipeline._dimensions(result.out_path) == (1080, 1920)
    # The selected window IS the story: nothing is dropped by a template.
    assert abs(result.duration - 8.0) < 0.6, result.duration
    meta = json.loads(pathlib.Path(result.metadata_path).read_text())
    assert "MISSION" not in json.dumps(meta)
    ass = pathlib.Path(result.srt_path).read_text()
    assert "CLIPDESK" not in ass.upper()


# ----------------------------------------------------------------- vision pass


def test_vision_scores_only_the_given_windows_and_unloads(tmp_path):
    frames = []
    for i in range(4):
        p = tmp_path / f"f{i}.jpg"
        p.write_bytes(b"\xff\xd8\xff\xe0fake")
        frames.append(str(p))
    seen = []

    def sampler(path, out, start, end):
        seen.append((start, end))
        return frames[:2]

    def describe(frame, start, end, model):
        return {"clippable": True, "score": 0.8, "reason": "a clutch"}

    unloaded = []
    scored, meta = vision.score_windows(
        "unused.mp4", [(10, 22), (30, 42)],
        sampler=sampler, describe_fn=describe,
        unload_fn=lambda model: unloaded.append(model),
        thumb_dir=str(tmp_path / "thumbs"),
    )
    assert seen == [(10, 22), (30, 42)]
    assert [round(s["score"], 1) for s in scored] == [0.8, 0.8]
    assert unloaded == [vision.MODEL]
    assert meta["frames"] == 4
    assert (tmp_path / "thumbs" / "10_22.jpg").exists()


# --------------------------------------------------------------- edge handling


def test_probe_rejects_a_non_video(tmp_path):
    bad = tmp_path / "bad.mp4"
    bad.write_text("not a video")
    with pytest.raises(pipeline.PipelineError):
        pipeline._probe(str(bad))


def test_render_pauses_when_the_disk_is_full(tmp_path, monkeypatch):
    class Usage:
        free = 10_000_000

    monkeypatch.setattr("shutil.disk_usage", lambda path: Usage())
    with pytest.raises(pipeline.PipelinePaused):
        pipeline._require_disk(str(tmp_path), needed_mb=1000)


def test_large_sources_are_downscaled_before_the_cut(tmp_path):
    src = tmp_path / "big.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-nostats",
         "-f", "lavfi", "-i", "testsrc=duration=6:size=2560x1440:rate=12",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
         "-shortest", str(src)],
        capture_output=True, check=True,
    )
    out = tmp_path / "cut.mp4"
    pipeline._cut_window(str(src), str(out), 1.0, 5.0)
    width, height = pipeline._dimensions(out)
    assert width <= 1920 and height <= 1080


def test_pipeline_handler_is_registered_on_the_shared_lane():
    from worker_app import jobs, handlers  # noqa: F401

    assert "run_pipeline" in jobs.HANDLERS
