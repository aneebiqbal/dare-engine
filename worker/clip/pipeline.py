"""The automatic upload-to-Shorts pipeline.

One uploaded video becomes a run that moves through sequential stages:

    ingest → scan → rank → vision → cut → transcribe → render → done

Hard rules honoured here:

- No model ever sees the whole video. The cheap scan is FFmpeg only; the vision
  model scores a few frames per shortlisted window; Whisper transcribes only
  the cut clips.
- One model resident at a time. The vision model is unloaded and verified
  before the cut; Whisper is unloaded and verified before the render. The whole
  run holds the single-project advisory lock (see the worker handler).
- Every stage records its own completion. A killed run resumes at the next
  incomplete stage and each candidate resumes at its own status, so completed
  work is never repeated.
- Each finished Short is published as soon as it renders, so the user sees
  output before the whole job finishes.
"""
from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import time
import urllib.request
import uuid
from datetime import datetime, timezone

from . import vision as vision_mod
from .engine import Result, codec_args, detect_encoder, render_cut
from .scan import CheapCandidate, SHORTLIST, cheap_scan, rank_candidates
from .transcribe import Word, actual_compute, transcribe, unload, whisper_compute
from .vision import FRAMES_PER_WINDOW, score_windows

# Relative cost of each stage, measured on this machine and updated with real
# timings as the run progresses. Only the starting estimate uses these.
RATES = {
    "scan": 0.6,        # seconds of FFmpeg scan per second of video
    "vision": 8.0,      # seconds per sampled frame
    "cut": 1.5,         # per clip
    "transcribe": 0.12, # per second of cut audio
    "render": 12.0,     # per clip
}
CLIP_SECONDS = 16.0
MAX_CUT_PIXELS = 1920 * 1080
CUT_PRE = 2.0
CUT_POST = 2.0

WORK_STAGES = ["ingest", "scan", "rank", "vision", "cut", "transcribe", "render"]
# Where each stage starts and ends on the 0-100 bar. A stage's completed
# progress is the next stage's start.
STAGE_BASE = {
    "ingest": 0, "scan": 5, "rank": 15, "vision": 20,
    "cut": 45, "transcribe": 55, "render": 70, "done": 100,
}
STAGE_PROGRESS = {
    "ingest": 5, "scan": 15, "rank": 20, "vision": 45,
    "cut": 55, "transcribe": 70, "render": 100,
}


class PipelineError(RuntimeError):
    """A hard failure: the run cannot continue."""


class PipelinePaused(RuntimeError):
    """A recoverable stop (disk, source volume). Resume when it is fixed."""


@dataclasses.dataclass
class Ctx:
    run: dict
    work: str
    reporter: "Reporter"
    source_path: str = ""


# ------------------------------------------------------------------ database


def _get_run(run_id: str) -> dict | None:
    from worker_app import db

    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pipeline_runs WHERE id = %s", (run_id,))
            row = cur.fetchone()
            if row is None:
                return None
            cols = [d.name for d in cur.description]
            return dict(zip(cols, row))


def _update_run(run_id: str, fields: dict) -> None:
    if not fields:
        return
    from worker_app import db

    sets = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values())
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE pipeline_runs SET {sets}, updated_at = now() WHERE id = %s",
                (*values, run_id),
            )


def _get_candidates(run_id: str) -> list[dict]:
    from worker_app import db

    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM pipeline_candidates WHERE run_id = %s ORDER BY start_seconds",
                (run_id,),
            )
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def _replace_candidates(run_id: str, rows: list[dict]) -> None:
    from worker_app import db

    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pipeline_candidates WHERE run_id = %s", (run_id,))
            for r in rows:
                cur.execute(
                    "INSERT INTO pipeline_candidates "
                    "(run_id, start_seconds, end_seconds, cheap_score, final_score, "
                    " reasons, origin, selected) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        run_id, r["start"], r["end"], r["cheap_score"],
                        r["final_score"], json.dumps(r["reasons"]),
                        r["origin"], bool(r.get("selected", True)),
                    ),
                )


def _update_candidate(candidate_id: str, fields: dict) -> None:
    from worker_app import db

    sets = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values())
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE pipeline_candidates SET {sets} WHERE id = %s",
                (*values, candidate_id),
            )


def _append_note(run_id: str, note: str) -> None:
    run = _get_run(run_id)
    notes = list((run or {}).get("notes") or [])
    if note not in notes:
        notes.append(note)
    _update_run(run_id, {"notes": json.dumps(notes)})


# ------------------------------------------------------------------ reporting


def progress_for(stage: str, frac: float) -> int:
    i = WORK_STAGES.index(stage)
    start = STAGE_BASE[stage]
    end = STAGE_BASE[WORK_STAGES[i + 1]] if i + 1 < len(WORK_STAGES) else 100
    return int(start + max(0.0, min(1.0, frac)) * (end - start))


def estimate_total(duration: float, top_n: int) -> int:
    return int(
        duration * RATES["scan"]
        + top_n * FRAMES_PER_WINDOW * RATES["vision"]
        + top_n * RATES["cut"]
        + top_n * CLIP_SECONDS * RATES["transcribe"]
        + top_n * RATES["render"]
    )


def _stage_units(stage: str, run: dict, selected: list[dict]) -> float:
    if stage == "scan":
        return max(1.0, float(run.get("duration_seconds") or 0.0))
    if stage == "vision":
        return max(1.0, len(selected) * FRAMES_PER_WINDOW)
    if stage == "transcribe":
        return max(1.0, len(selected) * CLIP_SECONDS)
    return float(max(1, len(selected)))


def _reestimate(ctx: Ctx, stage: str, seconds: float) -> None:
    """Fold the real stage time into the rates, then recompute the remaining ETA."""
    run = _get_run(ctx.run["id"])
    timings = dict(run.get("stage_timings") or {})
    rates = dict(RATES)
    rates.update(run.get("rates") or {})
    units = _stage_units(stage, run, [c for c in _get_candidates(run["id"]) if c["selected"]])
    rates[stage] = round(seconds / max(1e-6, units), 4)

    selected = [c for c in _get_candidates(run["id"]) if c["selected"]]
    duration = float(run.get("duration_seconds") or 0.0)
    remaining = 0.0
    if "scan" not in timings:
        remaining += duration * rates["scan"]
    if "vision" not in timings:
        remaining += max(1, len(selected)) * FRAMES_PER_WINDOW * rates["vision"]
    if "cut" not in timings:
        remaining += len(selected) * rates["cut"]
    if "transcribe" not in timings:
        remaining += len(selected) * CLIP_SECONDS * rates["transcribe"]
    if "render" not in timings:
        remaining += len(selected) * rates["render"]
    elapsed = sum(float(v) for v in timings.values())
    _update_run(
        run["id"],
        {
            "rates": json.dumps(rates),
            "remaining_seconds": int(remaining),
            "eta_seconds": int(elapsed + remaining),
        },
    )


class Reporter:
    def __init__(self, run_id: str, job_id: str | None = None):
        self.run_id = run_id
        self.job_id = job_id

    def action(self, text: str, model: str | None = None) -> None:
        fields = {"action": text}
        if model is not None:
            fields["model_loaded"] = model
        _update_run(self.run_id, fields)

    def progress(self, stage: str, frac: float, text: str, model: str | None = None) -> None:
        fields = {"progress": progress_for(stage, frac), "action": text}
        if model is not None:
            fields["model_loaded"] = model
        _update_run(self.run_id, fields)
        if self.job_id:
            from worker_app import jobs

            jobs.set_stage(self.job_id, stage)

    def complete(self, stage: str, seconds: float, text: str) -> None:
        run = _get_run(self.run_id)
        timings = dict((run or {}).get("stage_timings") or {})
        timings[stage] = round(seconds, 2)
        _update_run(
            self.run_id,
            {
                "stage": stage,
                "stage_timings": json.dumps(timings),
                "progress": STAGE_PROGRESS[stage],
                "action": text,
            },
        )
        _reestimate(Ctx(run=run or {}, work="", reporter=self), stage, seconds)


# -------------------------------------------------------------------- stages


def _compute_path() -> str:
    try:
        device, compute = whisper_compute()
    except Exception:
        device, compute = "cpu", "int8"
    try:
        encoder = detect_encoder()
    except Exception:
        encoder = "libx264"
    return f"asr={device}/{compute} encoder={encoder}"


def _probe(path: str) -> tuple[float, int, int]:
    proc = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-show_entries", "stream=codec_type,width,height",
         "-of", "json", path],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise PipelineError("the source video is unreadable")
    try:
        data = json.loads(proc.stdout)
        duration = float(data["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError):
        raise PipelineError("the source video is unreadable")
    if duration < 1.0:
        raise PipelineError("the source video is too short to clip")
    width = height = 0
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            width, height = int(stream.get("width", 0)), int(stream.get("height", 0))
            break
    if not width or not height:
        raise PipelineError("the source video has no video stream")
    return duration, width, height


def _ensure_source(ctx: Ctx) -> str:
    if ctx.source_path and os.path.exists(ctx.source_path):
        return ctx.source_path
    suffix = pathlib.Path(ctx.run["source_key"]).suffix or ".mp4"
    dest = os.path.join(ctx.work, f"source{suffix}")
    try:
        from worker_app import storage

        storage.get_file(ctx.run["source_key"], dest)
    except Exception as exc:
        raise PipelinePaused(
            f"the source volume is unavailable ({type(exc).__name__}); reconnect it and resume"
        )
    if not os.path.exists(dest):
        raise PipelinePaused("the source volume is unavailable; reconnect it and resume")
    ctx.source_path = dest
    return dest


def _stage_ingest(ctx: Ctx) -> None:
    rep = ctx.reporter
    rep.action("Reading the uploaded video")
    path = _ensure_source(ctx)
    duration, width, height = _probe(path)
    eta = estimate_total(duration, int(ctx.run.get("top_n") or 10))
    _update_run(
        ctx.run["id"],
        {
            "duration_seconds": duration,
            "width": width,
            "height": height,
            "eta_seconds": eta,
            "remaining_seconds": eta,
            "compute_path": _compute_path(),
        },
    )
    rep.progress(
        "ingest", 1.0,
        f"{duration / 60:.1f} min · {width}×{height} · about {max(1, eta // 60)} min total",
    )


def _stage_scan(ctx: Ctx) -> None:
    rep = ctx.reporter
    rep.action("Scanning audio and scene changes")
    path = _ensure_source(ctx)
    result = cheap_scan(path, shortlist=SHORTLIST)
    rows = [
        {
            "start": c.start, "end": c.end, "cheap_score": c.score,
            "final_score": c.score, "reasons": c.reasons, "origin": "ai",
            "selected": True,
        }
        for c in result.candidates
    ]
    _replace_candidates(ctx.run["id"], rows)
    notes = []
    if result.no_speech:
        notes.append("no speech detected; captions use the hook and end card only")
    _update_run(ctx.run["id"], {"no_speech": result.no_speech, "notes": json.dumps(notes)})
    rep.progress("scan", 1.0, f"Found {len(result.candidates)} candidate moments")


def _stage_rank(ctx: Ctx) -> None:
    rep = ctx.reporter
    rep.action("Ranking candidates")
    run = _get_run(ctx.run["id"])
    cands = _get_candidates(run["id"])
    cheap = [
        CheapCandidate(c["start_seconds"], c["end_seconds"], c["cheap_score"], c["reasons"])
        for c in cands
    ]
    duration = float(run.get("duration_seconds") or 0.0)
    ranked, notes = rank_candidates(cheap, run.get("timestamps") or [], duration)
    _replace_candidates(
        run["id"],
        [
            {
                "start": r.start, "end": r.end, "cheap_score": r.cheap_score,
                "final_score": r.final_score, "reasons": r.reasons,
                "origin": r.origin, "selected": True,
            }
            for r in ranked
        ],
    )
    if notes:
        _update_run(run["id"], {"notes": json.dumps(notes)})
    rep.progress("rank", 1.0, f"Ranked {len(ranked)} windows")


def _stage_vision(ctx: Ctx) -> None:
    rep = ctx.reporter
    run = _get_run(ctx.run["id"])
    selected = [c for c in _get_candidates(run["id"]) if c["selected"]]
    if not selected:
        rep.progress("vision", 1.0, "No candidates to vision-score")
        return
    from worker_app.config import settings

    model = settings.vision_model
    rep.action(f"Vision-scoring {len(selected)} candidates", model=f"vision:{model}")
    from worker_app import events

    events.log("model_load", f"vision {model}")
    path = _ensure_source(ctx)
    windows = [(c["start_seconds"], c["end_seconds"]) for c in selected]
    thumb_dir = os.path.join(ctx.work, "thumbs")
    scored: list[dict] = []
    meta: dict = {}
    try:
        scored, meta = score_windows(
            path, windows, model=model, thumb_dir=thumb_dir, tmp_root=ctx.work
        )
    except Exception as exc:
        meta = {"error": f"{type(exc).__name__}: {exc}", "unloaded": True}
        _append_note(run["id"], f"vision unavailable ({type(exc).__name__}); using cheap scores")
        try:
            vision_mod.unload(model)
        except Exception:
            pass
    by_window = {
        (round(float(s["start"]), 3), round(float(s["end"]), 3)): s for s in scored
    }
    updates = []
    for c in selected:
        s = by_window.get(
            (round(float(c["start_seconds"]), 3), round(float(c["end_seconds"]), 3)), {}
        )
        vision_score = float(s.get("score") or 0.0)
        final = 0.5 * float(c["cheap_score"]) + 0.5 * vision_score
        updates.append((c, vision_score, final, s))
    updates.sort(key=lambda u: u[2], reverse=True)
    top_n = int(run.get("top_n") or 10)
    keep = {id(u[0]) for u in updates[:top_n]}
    for c, vision_score, final, s in updates:
        thumb_key = None
        if s.get("thumb_path"):
            thumb_key = f"projects/{run['id']}/thumbs/{c['id']}.jpg"
            try:
                from worker_app import storage

                storage.put_file(thumb_key, s["thumb_path"])
            except Exception:
                thumb_key = None
        _update_candidate(
            c["id"],
            {
                "vision_score": vision_score,
                "vision_reason": s.get("reason"),
                "final_score": final,
                "thumb_key": thumb_key,
                "selected": id(c) in keep,
            },
        )
    if updates and all(u[1] == 0.0 for u in updates):
        if meta.get("errors", 0) and meta.get("errors") == meta.get("frames"):
            _append_note(
                run["id"],
                "vision unavailable (the model bridge could not be reached); "
                "using the best cheap-scored moments",
            )
        else:
            _append_note(
                run["id"],
                "the vision pass found nothing striking; using the best cheap-scored moments",
            )
    if meta.get("error"):
        _append_note(run["id"], f"vision reported: {meta['error']}")
    rep.progress("vision", 1.0, f"Vision scored {len(selected)} windows")


def _dimensions(path: str) -> tuple[int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", path],
        capture_output=True, text=True,
    ).stdout.strip()
    try:
        width, height = out.split("x")
        return int(width), int(height)
    except ValueError:
        return 0, 0


def _media_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True,
    ).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def _cut_window(src: str, out: str, start: float, end: float) -> None:
    """Seek, never copy the whole file. Re-encode only the short window."""
    seek = max(0.0, start - CUT_PRE)
    length = (end + CUT_POST) - seek
    width, height = _dimensions(src)
    vf: list[str] = []
    if width and height and width * height > MAX_CUT_PIXELS:
        vf = [
            "scale=1920:1080:force_original_aspect_ratio=decrease",
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        ]
    cmd = ["ffmpeg", "-y", "-ss", f"{seek:.3f}", "-i", src, "-t", f"{length:.3f}"]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += [
        "-pix_fmt", "yuv420p", *codec_args(),
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", out,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg cut failed: {proc.stderr[-800:]}")


def _require_disk(path: str, needed_mb: int = 1000) -> None:
    free = shutil.disk_usage(path).free
    if free < needed_mb * 1_000_000:
        raise PipelinePaused(
            f"disk is almost full ({free / 1_000_000:.0f} MB free, need {needed_mb} MB); "
            "free space and resume"
        )


def _stage_cut(ctx: Ctx) -> None:
    rep = ctx.reporter
    run = _get_run(ctx.run["id"])
    selected = [c for c in _get_candidates(run["id"]) if c["selected"]]
    todo = [c for c in selected if c["status"] not in ("cut", "transcribed", "rendered")]
    if not todo:
        rep.progress("cut", 1.0, "Clips already cut")
        return
    rep.action(f"Cutting {len(todo)} clips")
    path = _ensure_source(ctx)
    for i, c in enumerate(todo):
        cut_key = f"projects/{run['id']}/cuts/{c['id']}.mp4"
        local = os.path.join(ctx.work, f"cut_{c['id']}.mp4")
        try:
            _cut_window(path, local, float(c["start_seconds"]), float(c["end_seconds"]))
            from worker_app import storage

            storage.put_file(cut_key, local)
        except PipelinePaused:
            raise
        except Exception as exc:
            _update_candidate(c["id"], {"status": "failed", "error": str(exc)[:300]})
            continue
        _update_candidate(c["id"], {"status": "cut", "cut_key": cut_key})
        rep.progress("cut", (i + 1) / len(todo), f"Cutting clip {i + 1} of {len(todo)}")


def _stage_transcribe(ctx: Ctx) -> None:
    rep = ctx.reporter
    run = _get_run(ctx.run["id"])
    selected = [c for c in _get_candidates(run["id"]) if c["selected"]]
    todo = [c for c in selected if c["status"] == "cut"]
    if not todo:
        rep.progress("transcribe", 1.0, "No new clips to transcribe")
        return
    device, compute = whisper_compute()
    rep.action(
        f"Transcribing {len(todo)} clips", model=f"whisper:{device}/{compute}"
    )
    from worker_app import events, storage

    events.log("model_load", f"whisper {device}/{compute}")
    try:
        for i, c in enumerate(todo):
            local = os.path.join(ctx.work, f"cut_{c['id']}.mp4")
            storage.get_file(c["cut_key"], local)
            words = transcribe(local)
            transcript = [
                {"start": w.start, "end": w.end, "text": w.text} for w in words
            ]
            transcript_key = f"projects/{run['id']}/transcripts/{c['id']}.json"
            tfile = os.path.join(ctx.work, f"transcript_{c['id']}.json")
            pathlib.Path(tfile).write_text(json.dumps(transcript))
            storage.put_file(transcript_key, tfile)
            _update_candidate(
                c["id"],
                {"status": "transcribed", "transcript": json.dumps(transcript)},
            )
            message = f"Transcribing clip {i + 1} of {len(todo)}"
            if not transcript:
                message += " (no speech detected)"
            rep.progress("transcribe", (i + 1) / len(todo), message)
    finally:
        unload()
        events.log("model_unload", "whisper")
    actual = actual_compute()
    if (device, compute) != tuple(actual or (device, compute)):
        _append_note(
            run["id"],
            f"whisper fell back to {actual[0]}/{actual[1]} (requested {device}/{compute})",
        )
    _update_run(
        run["id"],
        {"compute_path": f"asr={actual[0]}/{actual[1]} encoder={detect_encoder()}"},
    )


def _hook_text(words: list[dict]) -> str:
    if not words:
        return "Watch this"
    best, best_density = "", 0.0
    for i in range(len(words)):
        span = words[i:i + 6]
        if len(span) < 3:
            break
        span_start = float(span[0]["start"])
        span_end = float(span[-1]["end"])
        density = len(span) / max(0.5, span_end - span_start)
        text = " ".join(str(w["text"]) for w in span).strip()
        if density > best_density and text:
            best, best_density = text, density
    return (best or "Watch this")[:80]


def _card(ctx: Ctx, candidate: dict, index: int) -> dict:
    return {
        "id": f"pipe_{index + 1}",
        "hook_text": _hook_text(candidate.get("transcript") or []),
        "question": "",
        "title_options": [""],
        "mode": "auto",
        "end_lines": ["CLIPDESK", f"Clip {index + 1}"],
    }


def _publish(ctx: Ctx, candidate: dict, result: Result, words: list[Word]) -> str:
    from worker_app import db, storage

    run = ctx.run
    clip_id = str(uuid.uuid4())
    key = f"clips/{clip_id}/short.mp4"
    storage.put_file(key, result.out_path)
    storage.put_file(f"clips/{clip_id}/thumb.jpg", result.thumb_path)
    storage.put_file(f"clips/{clip_id}/captions.srt", result.srt_path)
    storage.put_file(f"clips/{clip_id}/metadata.json", result.metadata_path)
    transcript = json.dumps(
        [{"start": w.start, "end": w.end, "text": w.text} for w in words]
    )
    idem = f"pipeline:{run['id']}:{candidate['id']}"
    try:
        metadata = json.loads(pathlib.Path(result.metadata_path).read_text())
    except (OSError, json.JSONDecodeError):
        metadata = {}
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO clips (id, assignment_id, file_key, title, state, template, "
                "duration_seconds, stage, progress, layout, caption_style, transcript, "
                "recording_key, source_start, source_end, render_key) "
                "VALUES (%s, NULL, %s, %s, 'ready', %s, %s, 'store', 100, %s, %s, %s, "
                "%s, %s, %s, %s) RETURNING id",
                (
                    clip_id, key, metadata.get("title") or "Clip",
                    result.template, result.duration, result.layout,
                    metadata.get("caption_style", "word"), transcript,
                    run["source_key"], float(candidate["start_seconds"]),
                    float(candidate["end_seconds"]), idem,
                ),
            )
            cur.fetchone()
    return clip_id


def _stage_render(ctx: Ctx) -> None:
    rep = ctx.reporter
    run = _get_run(ctx.run["id"])
    selected = [c for c in _get_candidates(run["id"]) if c["selected"]]
    todo = [c for c in selected if c["status"] == "transcribed"]
    if not todo:
        rep.progress("render", 1.0, "No clips to render")
        return
    rep.action(f"Rendering {len(todo)} Shorts")
    _require_disk(ctx.work, needed_mb=1000)
    from worker_app import storage

    for i, c in enumerate(todo):
        local = os.path.join(ctx.work, f"cut_{c['id']}.mp4")
        if not os.path.exists(local):
            storage.get_file(c["cut_key"], local)
        words = [
            Word(float(w["start"]), float(w["end"]), str(w["text"]))
            for w in (c.get("transcript") or [])
        ]
        out_dir = os.path.join(ctx.work, f"render_{c['id']}")
        result = render_cut(local, words, _card(ctx, c, i), out_dir)
        clip_id = _publish(ctx, c, result, words)
        _update_candidate(c["id"], {"status": "rendered", "clip_id": clip_id})
        rep.progress("render", (i + 1) / len(todo), f"Rendering captions {i + 1} of {len(todo)}")


def _memory() -> dict:
    from worker_app.config import settings

    out: dict = {}
    try:
        with urllib.request.urlopen(settings.model_bridge_url + "/models", timeout=10) as resp:
            data = json.loads(resp.read())
        out["mlx_peak_bytes"] = (data.get("mlx") or {}).get("peak_memory_bytes")
        out["host"] = data.get("host")
        out["ollama_running"] = [
            m.get("name") for m in (data.get("ollama") or {}).get("running", [])
        ]
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def _finish(ctx: Ctx) -> None:
    rep = ctx.reporter
    run = _get_run(ctx.run["id"])
    from worker_app import storage

    storage.delete_prefix(f"projects/{run['id']}/cuts")
    rendered = sum(
        1 for c in _get_candidates(run["id"]) if c["status"] == "rendered"
    )
    memory = _memory()
    rep.action(f"Done — {rendered} Shorts saved", model="")
    _update_run(
        run["id"],
        {
            "state": "done",
            "stage": "done",
            "progress": 100,
            "remaining_seconds": 0,
            "model_loaded": "",
            "finished_at": datetime.now(timezone.utc),
            "memory": json.dumps(memory),
        },
    )
    from worker_app import events

    events.log("cleanup", f"pipeline {run['id']} done: {rendered} shorts")


STAGE_FN = {
    "ingest": _stage_ingest,
    "scan": _stage_scan,
    "rank": _stage_rank,
    "vision": _stage_vision,
    "cut": _stage_cut,
    "transcribe": _stage_transcribe,
    "render": _stage_render,
}


def run_pipeline(run_id: str, job_id: str | None = None) -> None:
    """Run every incomplete stage in order. Safe to call again after a kill."""
    run = _get_run(run_id)
    if run is None:
        raise PipelineError(f"pipeline run {run_id} not found")
    if run["state"] == "done":
        return
    started = run.get("started_at") or datetime.now(timezone.utc)
    _update_run(
        run_id,
        {"state": "running", "error": None, "started_at": started, "action": "Starting"},
    )
    rep = Reporter(run_id, job_id)
    timings = dict(run.get("stage_timings") or {})
    with tempfile.TemporaryDirectory(prefix=f"pipeline-{run_id}-") as work:
        ctx = Ctx(run=run, work=work, reporter=rep)
        try:
            for stage in WORK_STAGES:
                if stage in timings:
                    continue
                ctx.run = _get_run(run_id) or run
                started_at = time.time()
                STAGE_FN[stage](ctx)
                rep.complete(stage, time.time() - started_at, _get_run(run_id)["action"])
                timings[stage] = True
            _finish(ctx)
        except PipelinePaused as exc:
            _update_run(
                run_id, {"state": "paused", "error": str(exc), "action": str(exc)}
            )
            from worker_app import events

            events.log("pipeline_paused", f"{run_id}: {exc}")
        except Exception as exc:
            _update_run(
                run_id,
                {
                    "state": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "action": "Failed",
                },
            )
            from worker_app import events

            events.log("pipeline_failed", f"{run_id}: {type(exc).__name__}")
            raise
