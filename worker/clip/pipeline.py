"""The automatic upload-to-Shorts pipeline — transcript-first moment selection.

Stages:

    ingest → scan → regions → detect → signals → score → cut → render → done

The picker is transcript-first and LLM-scored against the rubric in
`skills/clip-scoring/`; the vision model is one fused signal, never the primary
picker. Hard rules honoured here:

- No model sees the whole video: Whisper transcribes only the chosen speech
  regions, the VLM looks at a few frames of a shortlist, and the scoring LLM only
  reads text. One model resident at a time, unloaded and verified between
  stages.
- Every stage records its own completion. A killed run resumes at the next
  incomplete stage; each candidate resumes at its own status.
- Each finished Short is published as soon as it renders.
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

from . import regions as regions_mod
from . import select as select_mod
from . import vision as vision_mod
from .detect import _audio_energy, _duration, _scene_changes
from .engine import Result, codec_args, detect_encoder, render_cut
from .local_scoring import ScoringError, available as scorer_available, score_window, unload as unload_scorer
from .scan import speech_activity
from .select import Window, event_timeline, grow_windows, non_max_suppress, segment_sentences
from .transcribe import Word, actual_compute, last_language, transcribe, unload, whisper_compute
from .vision import FRAMES_PER_WINDOW, score_windows

# Relative cost of each stage, measured on this machine and replaced with real
# timings as the run progresses.
RATES = {
    "scan": 0.12,       # seconds of FFmpeg scan per second of video
    "regions": 0.15,    # seconds of transcription per second of region audio
    "detect": 2.0,      # fixed
    "signals": 8.0,     # seconds per vision frame
    "score": 4.0,       # seconds per scored candidate
    "cut": 10.0,        # per clip
    "render": 22.0,     # per clip
}
MAX_CANDIDATES = select_mod.MAX_CANDIDATES
VISION_SHORTLIST = 20
RERANK_FINALISTS = 24

WORK_STAGES = [
    "ingest", "scan", "regions", "detect", "signals", "score", "cut", "render",
]
STAGE_BASE = {
    "ingest": 0, "scan": 5, "regions": 15, "detect": 22,
    "signals": 32, "score": 45, "cut": 55, "render": 70, "done": 100,
}
STAGE_PROGRESS = {
    "ingest": 5, "scan": 15, "regions": 22, "detect": 32,
    "signals": 45, "score": 55, "cut": 70, "render": 100,
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


def estimate_total(duration: float, region_audio: float, n_candidates: int, n_clips: int) -> int:
    return int(
        10 + duration * RATES["scan"] + region_audio * RATES["regions"]
        + RATES["detect"] + VISION_SHORTLIST * FRAMES_PER_WINDOW * RATES["signals"]
        + n_candidates * RATES["score"] + n_clips * RATES["cut"] + n_clips * RATES["render"]
    )


def _stage_units(stage: str, run: dict, candidates: list[dict]) -> float:
    if stage == "scan":
        return max(1.0, float(run.get("duration_seconds") or 0.0))
    if stage == "regions":
        regions = run.get("regions") or []
        return max(1.0, sum(float(r.get("end", 0)) - float(r.get("start", 0)) for r in regions))
    if stage == "detect":
        return 1.0
    if stage == "signals":
        return max(1.0, min(VISION_SHORTLIST, len(candidates)) * FRAMES_PER_WINDOW)
    if stage == "score":
        return max(1.0, len(candidates))
    return float(max(1, len(candidates)))


def _reestimate(ctx: Ctx, stage: str, seconds: float) -> None:
    run = _get_run(ctx.run["id"])
    timings = dict(run.get("stage_timings") or {})
    rates = dict(RATES)
    rates.update(run.get("rates") or {})
    units = _stage_units(stage, run, [c for c in _get_candidates(run["id"]) if c["selected"]])
    rates[stage] = round(seconds / max(1e-6, units), 4)

    duration = float(run.get("duration_seconds") or 0.0)
    regions = run.get("regions") or []
    planned = [c for c in _get_candidates(run["id"]) if c["selected"]]
    all_candidates = _get_candidates(run["id"])
    region_audio = (
        sum(float(r.get("end", 0)) - float(r.get("start", 0)) for r in regions)
        or duration * 0.75
    )
    n_candidates = len(all_candidates) or 60
    n_clips = len(planned) or min(10, int(run.get("max_clips") or 40))
    remaining = 0.0
    if "scan" not in timings:
        remaining += duration * rates["scan"]
    if "regions" not in timings:
        remaining += region_audio * rates["regions"]
    if "detect" not in timings:
        remaining += rates["detect"]
    if "signals" not in timings:
        remaining += min(VISION_SHORTLIST, n_candidates) * FRAMES_PER_WINDOW * rates["signals"]
    if "score" not in timings:
        remaining += n_candidates * rates["score"]
    if "cut" not in timings:
        remaining += n_clips * rates["cut"]
    if "render" not in timings:
        remaining += n_clips * rates["render"]
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
    lang = last_language() or ""
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
    from worker_app.config import settings

    if settings.storage_driver == "local":
        local = pathlib.Path(settings.storage_local_dir) / ctx.run["source_key"]
        if local.is_file():
            ctx.source_path = str(local)
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


def _save_signals(ctx: Ctx, signals: dict) -> None:
    # Durable, not temp: a retried attempt resumes with the same scan.
    _update_run(ctx.run["id"], {"signals": json.dumps(signals)})


def _load_signals(ctx: Ctx) -> dict:
    run = _get_run(ctx.run["id"])
    return run.get("signals") or {}


def _stage_ingest(ctx: Ctx) -> None:
    rep = ctx.reporter
    rep.action("Reading the uploaded video")
    path = _ensure_source(ctx)
    duration, width, height = _probe(path)
    _update_run(
        ctx.run["id"],
        {
            "duration_seconds": duration,
            "width": width,
            "height": height,
            "compute_path": _compute_path(),
            "action": "Scanning audio and scene changes",
        },
    )
    eta = estimate_total(duration, min(duration * 0.75, regions_mod.DEFAULT_AUDIO_BUDGET), 60, 10)
    _update_run(ctx.run["id"], {"eta_seconds": eta, "remaining_seconds": eta})
    rep.progress(
        "ingest", 1.0,
        f"{duration / 60:.1f} min · {width}×{height} · about {max(1, eta // 60)} min total",
    )


def _stage_scan(ctx: Ctx) -> None:
    rep = ctx.reporter
    rep.action("Scanning audio and scene changes")
    path = _ensure_source(ctx)
    duration = float(ctx.run.get("duration_seconds") or _duration(path))
    energy = _audio_energy(path)
    scenes = _scene_changes(path)
    speech = speech_activity(path)
    speech_fraction = sum(speech) / len(speech) if speech else 0.0
    no_speech = speech_fraction < 0.15
    _save_signals(ctx, {"energy": energy, "scenes": scenes, "speech": speech})
    notes = []
    if no_speech:
        notes.append("no speech detected; nothing to caption")
    _update_run(
        ctx.run["id"],
        {"no_speech": no_speech, "notes": json.dumps(notes)},
    )
    rep.progress(
        "scan", 1.0,
        f"Scanned {duration / 60:.1f} min · {len(scenes)} cuts · "
        f"speech {speech_fraction * 100:.0f}%",
    )


def _cut_region_audio(src: str, out: str, start: float, end: float) -> None:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-nostats",
         "-ss", f"{max(0.0, start):.3f}", "-i", src,
         "-t", f"{max(0.5, end - start):.3f}",
         "-vn", "-ac", "1", "-ar", "16000", out],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg region cut failed: {proc.stderr[-500:]}")


def _stage_regions(ctx: Ctx) -> None:
    """Transcribe only the speech regions. Never the whole video."""
    rep = ctx.reporter
    rep.action("Finding speech regions")
    run = _get_run(ctx.run["id"])
    signals = _load_signals(ctx)
    regions = regions_mod.plan_regions(
        signals["speech"], signals["energy"], signals["scenes"],
        float(run.get("duration_seconds") or 0.0),
    )
    if not regions:
        _update_run(run["id"], {"regions": json.dumps([]), "transcript": json.dumps([])})
        _append_note(run["id"], "no speech regions found; no clips can be made")
        rep.progress("regions", 1.0, "No speech regions found")
        return
    rep.action(f"Transcribing {sum(r.end - r.start for r in regions) / 60:.0f} min of speech")
    path = _ensure_source(ctx)
    device, compute = whisper_compute()
    # Resume per region: keep whatever words earlier attempts produced.
    words_abs = [
        Word(float(w["start"]), float(w["end"]), str(w["text"]))
        for w in (run.get("transcript") or [])
    ]
    done_regions: set[int] = set()
    for i, region in enumerate(regions):
        if any(
            region.start <= (w.start + w.end) / 2 < region.end for w in words_abs
        ):
            done_regions.add(i)
    languages: dict[str, int] = {}
    # Lock the spoken language after the first region so Whisper cannot drift
    # into a wrong-script hallucination over a long video.
    chosen_language = run.get("language")
    from worker_app import events

    events.log("model_load", f"whisper {device}/{compute}")
    for i, region in enumerate(regions):
        if i in done_regions:
            continue
        wav = os.path.join(ctx.work, f"region_{i:04d}.wav")
        _cut_region_audio(path, wav, region.start, region.end)
        words = transcribe(wav, chosen_language)
        detected = last_language()
        if detected:
            languages[detected] = languages.get(detected, 0) + len(words)
        if chosen_language is None and detected:
            chosen_language = sane_language(detected, words_abs + list(words))
        for w in words:
            words_abs.append(Word(w.start + region.start, w.end + region.start, w.text))
        words_abs.sort(key=lambda w: w.start)
        # Checkpoint every region so a dropped connection cannot cost the stage.
        _update_run(
            run["id"],
            {
                "transcript": json.dumps(
                    [{"start": w.start, "end": w.end, "text": w.text} for w in words_abs]
                ),
                "language": max(languages, key=languages.get) if languages else "en",
            },
        )
        rep.progress(
            "regions", (i + 1) / len(regions),
            f"Transcribing speech {i + 1} of {len(regions)}", model=f"whisper:{device}/{compute}",
        )
    unload()
    events.log("model_unload", "whisper")
    words_abs.sort(key=lambda w: w.start)
    words_abs = _clean_words(words_abs, language)
    transcript = [{"start": w.start, "end": w.end, "text": w.text} for w in words_abs]
    base_language = run.get("language") or "en"
    language = max(languages, key=languages.get) if languages else base_language
    language = sane_language(language, words_abs)
    notes = []
    if len(languages) > 1:
        notes.append(f"mixed languages detected: {', '.join(sorted(languages))}; scoring in {language}")
    if not transcript:
        notes.append("no words transcribed; no clips can be made")
    _update_run(
        run["id"],
        {
            "regions": json.dumps([{"start": r.start, "end": r.end} for r in regions]),
            "transcript": json.dumps(transcript),
            "language": language,
            "notes": json.dumps(notes),
        },
    )
    rep.progress("regions", 1.0, f"Transcribed {len(transcript)} words in {language}")


def _window_text(transcript: list[dict], start: float, end: float) -> str:
    return " ".join(
        w["text"] for w in transcript
        if start <= (w["start"] + w["end"]) / 2 < end
    ).strip()


def _stage_detect(ctx: Ctx) -> None:
    rep = ctx.reporter
    rep.action("Growing sentence-aligned moments")
    run = _get_run(ctx.run["id"])
    transcript = run.get("transcript") or []
    if not transcript:
        rep.progress("detect", 1.0, "No transcript to detect from")
        return
    words = [Word(float(w["start"]), float(w["end"]), str(w["text"])) for w in transcript]
    sentences = segment_sentences(words)
    min_seconds = float(run.get("min_seconds") or 14)
    windows = grow_windows(sentences, min_seconds=min_seconds)
    # Exact user timestamps are added as high-priority candidates, never as a
    # replacement for the AI suggestions.
    user_starts: set[int] = set()
    for ts in run.get("timestamps") or []:
        try:
            start = float(ts.get("start"))
            end = max(float(ts.get("end")), start + min_seconds)
        except (TypeError, ValueError):
            continue
        text = _window_text(transcript, start, min(end, float(run["duration_seconds"])))
        if not text:
            continue
        user_starts.add(round(start, 2))
        windows.append(Window(start, min(end, float(run["duration_seconds"])), text,
                              len(text.split()), 0.0, 999.0))
    windows = non_max_suppress(windows)
    rows = [
        {
            "start": w.start, "end": w.end,
            "cheap_score": round(w.prior, 4), "final_score": round(w.prior, 4),
            "reasons": ["you marked this"] if round(w.start, 2) in user_starts else [],
            "origin": "user" if round(w.start, 2) in user_starts else "ai",
            "selected": False,
        }
        for w in windows
    ]
    _replace_candidates(run["id"], rows)
    _update_run(run["id"], {"timestamps": json.dumps([])})
    rep.progress("detect", 1.0, f"Grew {len(rows)} candidate moments")


def _stage_signals(ctx: Ctx) -> None:
    """Fuse the cheap timeline with a shortlist vision read (never the picker)."""
    rep = ctx.reporter
    run = _get_run(ctx.run["id"])
    candidates = _get_candidates(run["id"])
    if not candidates:
        rep.progress("signals", 1.0, "No candidates to inspect")
        return
    signals = _load_signals(ctx)
    rep.action(f"Reading visuals for {min(VISION_SHORTLIST, len(candidates))} candidates")
    from worker_app import events, storage
    from worker_app.config import settings

    shortlist = sorted(candidates, key=lambda c: c["cheap_score"], reverse=True)[:VISION_SHORTLIST]
    notes: list[str] = []
    vision_reason: dict[str, str] = {}
    vision_score: dict[str, float] = {}
    path = _ensure_source(ctx)
    try:
        scored, meta = score_windows(
            path,
            [(c["start_seconds"], c["end_seconds"]) for c in shortlist],
            model=settings.vision_model,
            thumb_dir=os.path.join(ctx.work, "thumbs"),
            tmp_root=ctx.work,
        )
        by_window = {(round(s["start"], 3), round(s["end"], 3)): s for s in scored}
        for c in shortlist:
            s = by_window.get((round(c["start_seconds"], 3), round(c["end_seconds"], 3)), {})
            vision_score[str(c["id"])] = float(s.get("score") or 0.0)
            reason = (s.get("reason") or "").strip()
            vision_reason[str(c["id"])] = reason[:200]
            if reason:
                thumb = None
                if s.get("thumb_path"):
                    thumb = f"projects/{run['id']}/thumbs/{c['id']}.jpg"
                    try:
                        storage.put_file(thumb, s["thumb_path"])
                    except Exception:
                        thumb = None
                _update_candidate(c["id"], {"vision_reason": reason[:200], "thumb_key": thumb})
        if meta.get("errors", 0) and meta.get("errors") == meta.get("frames"):
            notes.append("vision unavailable (bridge unreachable); ranking uses audio/scene signals only")
    except Exception as exc:
        notes.append(f"vision unavailable ({type(exc).__name__}); ranking uses audio/scene signals only")
        try:
            vision_mod.unload(settings.vision_model)
        except Exception:
            pass

    for c in candidates:
        window = Window(
            float(c["start_seconds"]), float(c["end_seconds"]), "", 0, 0.0, 0.0
        )
        timeline = event_timeline(
            window,
            energy=signals["energy"],
            scenes=signals["scenes"],
            speech=signals["speech"],
            vision_note=vision_reason.get(str(c["id"]), ""),
        )
        _update_candidate(c["id"], {"timeline": timeline})

    for note in notes:
        _append_note(run["id"], note)
    rep.progress("signals", 1.0, f"Fused audio/scene{'' if vision_score else ' (vision off)'} signals")


def _fallback_composite(candidates: list[dict]) -> None:
    peak = max((c["cheap_score"] for c in candidates), default=0.0) or 1.0
    for c in candidates:
        value = round(40.0 + 60.0 * (float(c["cheap_score"]) / peak), 1)
        _update_candidate(
            c["id"],
            {
                "scores": json.dumps({"cheap_fallback": value}),
                "composite": value,
                "reason": "scoring LLM unavailable; ranked by the cheap audio/scene score",
                "label": "story",
                "hook": "",
                "keep": True,
            },
        )


def _stage_score(ctx: Ctx) -> None:
    """Rubric scoring against the skill files, kill criteria, then rerank."""
    rep = ctx.reporter
    run = _get_run(ctx.run["id"])
    candidates = _get_candidates(run["id"])
    if not candidates:
        rep.progress("score", 1.0, "No candidates to score")
        return
    language = run.get("language") or "en"
    transcript = run.get("transcript") or []
    # Score only the strongest shortlist (plus any exact user timestamps); the
    # rest are marked out without a call so a rich video stays fast.
    from worker_app.config import settings as wsettings

    limit = int(getattr(wsettings, "score_max_candidates", 40))
    ranked = sorted(candidates, key=lambda c: float(c["cheap_score"]), reverse=True)
    users = [c for c in ranked if c["origin"] == "user"]
    ai = [c for c in ranked if c["origin"] != "user"]
    shortlist = users + ai[: max(0, limit - len(users))]
    shortlisted = {str(c["id"]) for c in shortlist}
    for c in candidates:
        if str(c["id"]) not in shortlisted:
            _update_candidate(
                c["id"], {"keep": False, "reason": "below the scoring shortlist"}
            )
    candidates = shortlist
    rep.action(f"Scoring {len(candidates)} moments against the rubric", model=settings_model())
    from worker_app import events

    events.log("model_load", f"scorer {settings_model()}")
    scorer_ok = scorer_available()
    if not scorer_ok:
        _append_note(run["id"], "scoring LLM unavailable; kept candidates by the cheap score")
        _fallback_composite(candidates)
    else:
        scored_ids: set[str] = set()
        for i, c in enumerate(candidates):
            text = _window_text(transcript, float(c["start_seconds"]), float(c["end_seconds"]))
            try:
                data = score_window(text, c.get("timeline") or "", language)
            except Exception as exc:  # noqa: BLE001 - degrade to cheap ranking, never hang
                _append_note(
                    run["id"], f"scoring LLM failed on one candidate ({type(exc).__name__}); "
                    "remaining candidates use the cheap score"
                )
                break
            _update_candidate(
                c["id"],
                {
                    "label": str(data.get("label") or "story"),
                    "hook": str(data.get("hook") or "")[:160],
                    "reason": str(data.get("reason") or "")[:300],
                    "scores": json.dumps(data.get("scores") or {}),
                    "composite": float(data.get("composite") or 0.0),
                    "keep": bool(data.get("keep")),
                },
            )
            scored_ids.add(str(c["id"]))
            rep.progress(
                "score", (i + 1) / len(candidates),
                f"Scoring moment {i + 1} of {len(candidates)}",
                model=settings_model(),
            )
        remaining = [c for c in candidates if str(c["id"]) not in scored_ids]
        if remaining:
            _fallback_composite(remaining)

    unloaded = unload_scorer()
    events.log("model_unload", f"scorer {settings_model()} unloaded={unloaded}")
    if not unloaded:
        _append_note(run["id"], "scoring model may still be resident; verify on the Models page")

    # Quality bar, minimum length, no arbitrary cap beyond max_clips.
    bar = float(run.get("quality_bar") or 60)
    min_seconds = float(run.get("min_seconds") or 14)
    max_clips = int(run.get("max_clips") or 40)
    finalists = [
        c for c in _get_candidates(run["id"])
        if c.get("keep") and float(c.get("composite") or 0) >= bar
        and float(c["end_seconds"]) - float(c["start_seconds"]) >= min_seconds
    ]
    finalists.sort(key=lambda c: float(c.get("composite") or 0), reverse=True)
    finalists = finalists[:max_clips]

    if scorer_ok and len(finalists) >= 2:
        from .local_scoring import rerank

        items = [
            {
                "start": float(c["start_seconds"]),
                "end": float(c["end_seconds"]),
                "label": c.get("label") or "story",
                "hook": c.get("hook") or "",
                "transcript": _window_text(
                    transcript, float(c["start_seconds"]), float(c["end_seconds"])
                ),
                "composite": float(c.get("composite") or 0),
            }
            for c in finalists[:RERANK_FINALISTS]
        ]
        try:
            result = rerank(items)
            order = [int(round(s)) for s in result.get("order", [])]
            drops = {int(round(s)) for s in result.get("drop", [])}
            rank = {s: i for i, s in enumerate(order)}
            finalists.sort(
                key=lambda c: (
                    rank.get(int(round(float(c["start_seconds"]))), 999),
                    -float(c.get("composite") or 0),
                )
            )
            for c in finalists:
                if int(round(float(c["start_seconds"]))) in drops:
                    c["selected"] = False
        except Exception as exc:  # noqa: BLE001
            _append_note(run["id"], f"rerank unavailable ({type(exc).__name__}); kept composite order")

    # Variety: no single label dominates the set.
    cap = max(2, (len(finalists) + 2) // 3 + 1)
    counts: dict[str, int] = {}
    kept = []
    for c in finalists:
        label = c.get("label") or "story"
        if counts.get(label, 0) >= cap:
            c["selected"] = False
        else:
            counts[label] = counts.get(label, 0) + 1
            kept.append(c)

    kept_ids = {str(c["id"]) for c in kept}
    for c in _get_candidates(run["id"]):
        _update_candidate(c["id"], {"selected": str(c["id"]) in kept_ids})

    if not kept:
        _append_note(
            run["id"],
            "no moment cleared the quality bar; lower quality_bar to get results",
        )
    rep.progress("score", 1.0, f"Selected {len(kept)} self-contained moments")


def settings_model() -> str:
    from worker_app.config import settings

    return settings.scoring_model


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


def _cut_window(src: str, out: str, start: float, end: float) -> None:
    """Seek to the exact speech edge; re-encode only this short window."""
    width, height = _dimensions(src)
    vf: list[str] = []
    if width and height and width * height > 1920 * 1080:
        vf = [
            "scale=1920:1080:force_original_aspect_ratio=decrease",
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        ]
    cmd = ["ffmpeg", "-y", "-ss", f"{max(0.0, start):.3f}", "-i", src,
           "-t", f"{max(0.5, end - start):.3f}"]
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


def _slice_words(transcript: list[dict], start: float, end: float) -> list[Word]:
    return [
        Word(float(w["start"]) - start, float(w["end"]) - start, str(w["text"]))
        for w in transcript
        if start <= (w["start"] + w["end"]) / 2 < end
    ]


def _stage_cut(ctx: Ctx) -> None:
    rep = ctx.reporter
    run = _get_run(ctx.run["id"])
    selected = [c for c in _get_candidates(run["id"]) if c["selected"]]
    todo = [c for c in selected if c["status"] not in ("cut", "rendered")]
    if not todo:
        rep.progress("cut", 1.0, "Clips already cut")
        return
    rep.action(f"Cutting {len(todo)} moments")
    path = _ensure_source(ctx)
    transcript = run.get("transcript") or []
    from worker_app import storage

    for i, c in enumerate(todo):
        cut_key = f"projects/{run['id']}/cuts/{c['id']}.mp4"
        local = os.path.join(ctx.work, f"cut_{c['id']}.mp4")
        try:
            _cut_window(path, local, float(c["start_seconds"]), float(c["end_seconds"]))
            storage.put_file(cut_key, local)
        except Exception as exc:
            _update_candidate(c["id"], {"status": "failed", "error": str(exc)[:300]})
            continue
        words = _slice_words(transcript, float(c["start_seconds"]), float(c["end_seconds"]))
        if not words:
            _append_note(
                run["id"],
                f"no transcript words inside {c['start_seconds']:.0f}-{c['end_seconds']:.0f}s; "
                "captioned without words",
            )
        _update_candidate(
            c["id"],
            {
                "status": "cut",
                "cut_key": cut_key,
                "transcript": json.dumps(
                    [{"start": w.start, "end": w.end, "text": w.text} for w in words]
                ),
            },
        )
        rep.progress("cut", (i + 1) / len(todo), f"Cutting moment {i + 1} of {len(todo)}")


NON_LATIN_SCRIPTS = {
    "ur", "ar", "fa", "he", "hi", "bn", "pa", "zh", "ja", "ko", "ru", "uk",
    "el", "th", "ta", "te", "ml", "kn", "gu", "mr", "ne", "si", "km", "lo",
    "my", "ka", "hy", "am", "ka",
}


def _clean_words(words: list[Word], language: str) -> list[Word]:
    """Drop non-Latin-script tokens from a Latin-language transcript.

    Whisper hallucinates Urdu/Hindi lines inside quiet game audio when it
    auto-detects per region; those words must never reach captions or hooks.
    """
    if language in NON_LATIN_SCRIPTS:
        return words
    kept: list[Word] = []
    for w in words:
        letters = [c for c in w.text if c.isalpha()]
        if len(letters) >= 3:
            ascii_letters = sum(1 for c in letters if c.isascii())
            if ascii_letters / len(letters) < 0.5:
                continue
        kept.append(w)
    return kept


def sane_language(code: str | None, words: list[Word]) -> str:
    """Whisper sometimes mislabels English game audio (e.g. as Urdu). If the
    detected language uses a non-Latin script but the transcript is Latin, trust
    the text."""
    code = code or "en"
    sample = " ".join(w.text for w in words[:200])
    letters = sum(1 for c in sample if c.isalpha())
    if letters and code in NON_LATIN_SCRIPTS:
        ascii_letters = sum(1 for c in sample if c.isascii() and c.isalpha())
        if ascii_letters / letters > 0.8:
            return "en"
    return code


def _fallback_hook(words: list[Word]) -> str:
    """Densest short phrase, used only when the scoring LLM gave no hook line."""
    best, best_density = "", 0.0
    for i in range(len(words)):
        span = words[i : i + 6]
        if len(span) < 3:
            break
        density = len(span) / max(0.5, float(span[-1].end - span[0].start))
        text = " ".join(w.text for w in span).strip()
        if density > best_density and text:
            best, best_density = text, density
    return (best or "Watch this")[:80]


def _card(candidate: dict, index: int, words: list[Word] | None = None) -> dict:
    hook = (candidate.get("hook") or "").strip()
    if not hook and words:
        hook = _fallback_hook(words)
    # The hook is burned on screen: keep it short even if the model was verbose.
    display = hook
    if len(display) > 60:
        display = display[:57].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return {
        "id": f"clip_{index + 1}",
        "hook_text": display or "Watch this",
        "question": "",
        "title_options": [hook[:100]],
        "mode": "auto",
        "label": candidate.get("label") or "",
        # No internal branding is burned into the output.
        "end_lines": [],
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
    project_dir = f"projects/{run['id']}/clips/{candidate['id']}"
    storage.put_file(f"{project_dir}/short.mp4", result.out_path)
    storage.put_file(f"{project_dir}/thumb.jpg", result.thumb_path)
    storage.put_file(f"{project_dir}/captions.srt", result.srt_path)
    storage.put_file(f"{project_dir}/metadata.json", result.metadata_path)
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
                    clip_id, key, metadata.get("title") or candidate.get("hook") or "Short",
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
    todo = [c for c in selected if c["status"] == "cut"]
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
        result = render_cut(local, words, _card(c, i, words), out_dir)
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
    rendered = sum(1 for c in _get_candidates(run["id"]) if c["status"] == "rendered")
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
    "regions": _stage_regions,
    "detect": _stage_detect,
    "signals": _stage_signals,
    "score": _stage_score,
    "cut": _stage_cut,
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
    # A recorded scan whose signals are missing (an older interrupted run) is not
    # resumable — force the scan again so every later stage has its inputs.
    if timings.get("scan") and not run.get("signals"):
        timings.pop("scan", None)
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
            _update_run(run_id, {"state": "paused", "error": str(exc), "action": str(exc)})
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
