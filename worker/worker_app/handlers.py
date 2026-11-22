"""Real job handlers. Each renders one mission window into a Short."""
from __future__ import annotations

import json
import pathlib
import tempfile
import time
import uuid

from clip.engine import Result, render_short
from clip.llm import get_llm
from clip.transcribe import Word
from clip.tts import speak
from clip.voice import mix_voice_over

from . import db, jobs, storage
from .config import settings

STAGES = {
    "fetch": 10,
    "transcribe": 30,
    "select": 50,
    "render": 90,
    "store": 100,
}


def _run_ffmpeg(cmd: list[str]) -> None:
    import subprocess

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr[-1500:]}")


def _stage(clip_id: str, stage: str, progress: int, error: str | None = None,
           job_id: str | None = None) -> None:
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE clips SET stage = %s, progress = %s, error = %s WHERE id = %s",
                (stage, progress, error, clip_id),
            )
    if job_id:
        jobs.set_stage(job_id, stage)


def _clip_row(clip_id: str):
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT state, file_key, transcript, recording_key, source_start, "
                "source_end, trim_start, trim_end, layout, caption_style, voice_over, "
                "voice, render_key FROM clips WHERE id = %s",
                (clip_id,),
            )
            return cur.fetchone()


@jobs.register("render_clip")
def render_clip(payload: dict) -> None:
    clip_id = payload["clip_id"]
    row = _clip_row(clip_id)
    if row is None:
        raise RuntimeError(f"clip {clip_id} not found")
    (state, file_key, transcript, recording_key, source_start, source_end,
     trim_start, trim_end, layout, caption_style, voice_over, voice, render_key) = row

    idem = f"render:{clip_id}:{payload.get('start')}:{payload.get('end')}:" \
           f"{payload.get('layout')}:{payload.get('caption_style')}:" \
           f"{payload.get('voice_over')}:{payload.get('voice')}"
    if state == "ready" and file_key and render_key == idem:
        return  # idempotent: a retried job does not render twice

    with tempfile.TemporaryDirectory(prefix="render-") as tmp:
        tmp = pathlib.Path(tmp)
        _stage(clip_id, "fetch", STAGES["fetch"], job_id=payload.get("_job_id"))

        if payload.get("recording_dir"):
            directory = pathlib.Path(payload["recording_dir"])
            segments = sorted(directory.glob("*.m4s")) + sorted(directory.glob("*.mp4"))
            if not segments:
                raise RuntimeError(f"no segments in {directory}")
            listing = tmp / "segments.txt"
            listing.write_text("".join(f"file '{s}'\n" for s in segments))
            recording = tmp / "timeline.mp4"
            _run_ffmpeg(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                 "-c", "copy", str(recording)]
            )
            recording_key = None
        else:
            recording = tmp / "recording.mp4"
            storage.get_file(payload["recording_key"], str(recording))
            recording_key = payload.get("recording_key") or recording_key

        start = float(payload["trim_start"] if payload.get("trim_start") is not None else payload["start"])
        end = float(payload["trim_end"] if payload.get("trim_end") is not None else payload["end"])

        # Transcript cache: reuse when the cached window covers this trim.
        # shortcut: cache is per clip row and only reused when the trim fits the
        # cached window; upgrade to a recording-keyed transcript store when trims
        # go outside it.
        words_abs = None
        cached = None
        if transcript and recording_key and source_start is not None and source_end is not None:
            if source_start <= start and end <= source_end:
                cached = transcript
        if cached:
            words_abs = [Word(float(w["start"]), float(w["end"]), w["text"]) for w in cached]

        _stage(clip_id, "transcribe", STAGES["transcribe"], job_id=payload.get("_job_id"))
        _stage(clip_id, "select", STAGES["select"], job_id=payload.get("_job_id"))
        _stage(clip_id, "render", STAGES["render"], job_id=payload.get("_job_id"))

        card = payload["card"]
        result: Result = render_short(
            str(recording),
            card,
            start,
            end,
            str(tmp / "out"),
            payload.get("result", ""),
            payload.get("layout") or layout,
            get_llm(),
            words_abs=words_abs,
            caption_style=payload.get("caption_style") or caption_style or "word",
            template_id=payload.get("template_id"),
        )

        out_path = result.out_path
        if payload.get("voice_over") and payload.get("voice"):
            hook = speak(card.get("hook_text", ""), payload["voice"], str(tmp / "hook.wav"),
                         settings.tts_model_dir, settings.tts_command)
            outro_text = f"Mission {str(card.get('id', '')).replace('m_', '')}. Clipdesk Missions."
            outro = speak(outro_text, payload["voice"], str(tmp / "outro.wav"),
                          settings.tts_model_dir, settings.tts_command)
            total = result.duration
            cues = [(0.0, hook), (max(0.0, total - 3.0), outro)]
            mixed = tmp / "short-voiced.mp4"
            mix_voice_over(out_path, cues, str(mixed))
            out_path = str(mixed)

        key = f"clips/{clip_id}/short.mp4"
        storage.put_file(key, out_path)
        storage.put_file(f"clips/{clip_id}/thumb.jpg", result.thumb_path)
        storage.put_file(f"clips/{clip_id}/captions.srt", result.srt_path)
        storage.put_file(f"clips/{clip_id}/metadata.json", result.metadata_path)

        if recording_key is None:
            recording_key = payload.get("recording_key")
        with db.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE clips SET file_key = %s, state = 'ready', stage = 'store', "
                    "progress = 100, error = NULL, template = %s, duration_seconds = %s, "
                    "title = %s, transcript = %s, recording_key = %s, source_start = %s, "
                    "source_end = %s, render_key = %s, layout = %s, caption_style = %s, "
                    "voice_over = %s, voice = %s WHERE id = %s",
                    (
                        key,
                        result.layout,
                        result.duration,
                        card.get("hook_text", ""),
                        json.dumps(
                            [{"start": w.start, "end": w.end, "text": w.text}
                             for w in (result.words_abs or [])]
                        ),
                        recording_key,
                        start - 10.0,
                        end + 5.0,
                        idem,
                        payload.get("layout") or layout,
                        payload.get("caption_style") or caption_style or "word",
                        bool(payload.get("voice_over")),
                        payload.get("voice"),
                        clip_id,
                    ),
                )
        if payload.get("_job_id"):
            jobs.set_stage(payload["_job_id"], "store")


@jobs.register("detect_moments")
def detect_moments(payload: dict) -> None:
    """Part A: score the whole recording and store ranked candidate windows."""
    from clip.detect import detect_compute_path, detect_moments as run_detection

    recording_id = payload["recording_id"]
    key = payload["storage_key"]
    top_n = int(payload.get("top_n", 5))
    # Store the path before the expensive pass so the studio shows which
    # compute path is live, not only after the candidates land.
    compute = detect_compute_path()
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE studio_recordings SET whisper_device=%s, "
                "whisper_compute_type=%s, encoder=%s WHERE id=%s",
                (compute.whisper_device, compute.whisper_compute_type,
                 compute.encoder, recording_id),
            )
    with tempfile.TemporaryDirectory(prefix="detect-") as tmp:
        path = str(pathlib.Path(tmp) / "recording.mp4")
        storage.get_file(key, path)
        candidates, _ = run_detection(path, top_n=top_n)
    with db.session() as conn:
        with conn.cursor() as cur:
            for c in candidates:
                cur.execute(
                    "INSERT INTO studio_candidates "
                    "(recording_id, start_seconds, end_seconds, score, reasons) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (recording_id, c.start, c.end, c.score, json.dumps(c.reasons)),
                )


@jobs.register("suggest_clips")
def suggest_clips(payload: dict) -> None:
    """Part B: a sampled VLM pass that proposes clips the detector never marked.

    Optional and off by default. The VLM loads only for this pass and is
    unloaded (verified) inside `clip.vision.suggest`.
    """
    from clip.vision import suggest

    recording_id = payload["recording_id"]
    key = payload["storage_key"]
    with tempfile.TemporaryDirectory(prefix="vision-") as tmp:
        path = str(pathlib.Path(tmp) / "recording.mp4")
        storage.get_file(key, path)
        suggestions, meta = suggest(
            path, top_n=int(payload.get("top_n", 5)), model=settings.vision_model
        )
        with db.session() as conn:
            with conn.cursor() as cur:
                for s in suggestions:
                    cur.execute(
                        "INSERT INTO studio_candidates "
                        "(recording_id, start_seconds, end_seconds, score, reasons, source) "
                        "VALUES (%s, %s, %s, %s, %s, 'vision') RETURNING id",
                        (recording_id, s.start, s.end, s.score, json.dumps([s.reason])),
                    )
                    candidate_id = cur.fetchone()[0]
                    thumb_key = f"studio-candidates/{candidate_id}/thumb.jpg"
                    try:
                        storage.put_file(thumb_key, s.thumb_path)
                    except Exception:
                        thumb_key = None
                    if thumb_key:
                        cur.execute(
                            "UPDATE studio_candidates SET thumb_key = %s WHERE id = %s",
                            (thumb_key, candidate_id),
                        )
                cur.execute(
                    "UPDATE studio_recordings SET vision_model = %s, vision_seconds = %s "
                    "WHERE id = %s",
                    (meta.get("model"), meta.get("seconds_added"), recording_id),
                )
    if payload.get("_job_id"):
        jobs.set_stage(payload["_job_id"], "vision")


def _title_card(text: str, out_path: str, ref_path: str) -> None:
    """A 2 s title card matched to the clip's size, frame rate and audio."""
    import json as _json
    import subprocess as _sp

    probe = _sp.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate", "-of", "json", ref_path],
        capture_output=True, text=True, check=True,
    )
    stream = _json.loads(probe.stdout)["streams"][0]
    width, height = stream["width"], stream["height"]
    num, _, den = str(stream["r_frame_rate"]).partition("/")
    fps = float(num) / float(den or 1)
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    textfile = pathlib.Path(out_path).with_suffix(".txt")
    textfile.write_text(text)
    _run_ffmpeg(
        ["ffmpeg", "-y",
         "-f", "lavfi", "-i", f"color=c=0x06070a:s={width}x{height}:d=2:r={fps:g}",
         "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
         "-vf", f"drawtext=fontfile={font}:textfile={textfile}:fontcolor=white:fontsize=52"
                f":x=(w-text_w)/2:y=(h-text_h)/2",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-shortest", out_path]
    )


@jobs.register("build_long_form")
def build_long_form(payload: dict) -> None:
    """Concatenate a session's finished Shorts into one long-form video."""
    lf_id = payload["long_form_id"]
    intro = payload.get("intro") or ""
    outro = payload.get("outro") or ""
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT clip_ids FROM long_forms WHERE id = %s", (lf_id,))
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(f"long form {lf_id} not found")
            clip_ids = list(row[0] or [])
            cur.execute(
                "UPDATE long_forms SET state = 'building', error = NULL WHERE id = %s",
                (lf_id,),
            )
            keys = []
            for cid in clip_ids:
                cur.execute("SELECT file_key FROM clips WHERE id = %s", (cid,))
                found = cur.fetchone()
                if found and found[0]:
                    keys.append((cid, found[0]))
    try:
        with tempfile.TemporaryDirectory(prefix="longform-") as tmp:
            tmp = pathlib.Path(tmp)
            parts = []
            for cid, key in keys:
                part = tmp / f"{len(parts):03d}_{cid}.mp4"
                storage.get_file(key, str(part))
                parts.append(part)
            if parts and intro:
                card = tmp / "intro.mp4"
                _title_card(intro, str(card), str(parts[0]))
                parts.insert(0, card)
            if parts and outro:
                card = tmp / "outro.mp4"
                _title_card(outro, str(card), str(parts[-1]))
                parts.append(card)
            listing = tmp / "concat.txt"
            listing.write_text("".join(f"file '{p}'\n" for p in parts))
            out = tmp / "long.mp4"
            _run_ffmpeg(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                 "-c", "copy", str(out)]
            )
            file_key = f"long-forms/{lf_id}/long.mp4"
            storage.put_file(file_key, str(out))
        with db.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE long_forms SET state = 'ready', file_key = %s WHERE id = %s",
                    (file_key, lf_id),
                )
    except Exception as exc:
        with db.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE long_forms SET state = 'failed', error = %s WHERE id = %s",
                    (str(exc), lf_id),
                )
        raise


@jobs.register("preview_voice")
def preview_voice(payload: dict) -> None:
    voice_over_id = payload["voice_over_id"]
    out_dir = pathlib.Path(tempfile.mkdtemp(prefix="voice-"))
    wav = speak(
        payload["text"],
        payload["voice"],
        str(out_dir / "preview.wav"),
        settings.tts_model_dir,
        settings.tts_command,
    )
    audio_key = f"voice-overs/{voice_over_id}/preview.wav"
    storage.put_file(audio_key, wav)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE voice_overs SET state = 'ready', audio_key = %s, duration = 0 "
                "WHERE id = %s",
                (audio_key, voice_over_id),
            )


# The single-project lane. A session-level advisory lock, not a flag, so two
# workers cannot analyse two projects at once even if their claims interleave.
PROJECT_LOCK_KEY = 0x434C4B44  # "CLKD"


def _analysis_active(recording_id: str) -> bool:
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM jobs WHERE kind IN ('detect_moments', 'suggest_clips') "
                "AND payload->>'recording_id' = %s AND state IN ('queued', 'running')",
                (recording_id,),
            )
            return cur.fetchone()[0] > 0


def _enqueue_analysis(recording_id: str, storage_key: str, vision: bool) -> None:
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO jobs (kind, payload, idempotency_key) "
                "VALUES ('detect_moments', %s, %s)",
                (
                    json.dumps({
                        "recording_id": recording_id,
                        "storage_key": storage_key,
                        "top_n": 5,
                    }),
                    f"detect:{recording_id}:{uuid.uuid4().hex}",
                ),
            )
            if vision:
                cur.execute(
                    "INSERT INTO jobs (kind, payload, idempotency_key) "
                    "VALUES ('suggest_clips', %s, %s)",
                    (
                        json.dumps({
                            "recording_id": recording_id,
                            "storage_key": storage_key,
                            "top_n": 5,
                        }),
                        f"vision:{recording_id}:{uuid.uuid4().hex}",
                    ),
                )


def _unlock_project_lane(conn) -> None:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_unlock(%s)", (PROJECT_LOCK_KEY,))
        conn.commit()
    except Exception:
        conn.rollback()


def _run_project_analysis(project_id: str) -> None:
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT recording_id, vision FROM projects WHERE id = %s", (project_id,)
            )
            row = cur.fetchone()
            if row is None:
                return
            recording_id, vision = row
            if recording_id is None:
                cur.execute(
                    "UPDATE projects SET stage_note = "
                    "'Waiting for a recording: attach one to analyse.' WHERE id = %s",
                    (project_id,),
                )
                return
            cur.execute(
                "SELECT storage_key FROM studio_recordings WHERE id = %s",
                (str(recording_id),),
            )
            rec = cur.fetchone()
            if rec is None:
                cur.execute(
                    "UPDATE projects SET stage_note = "
                    "'The recording is gone; attach it again.' WHERE id = %s",
                    (project_id,),
                )
                return
            storage_key = rec[0]
            cur.execute(
                "UPDATE projects SET stage_note = 'Analysis queued.' WHERE id = %s",
                (project_id,),
            )
    recording_id = str(recording_id)
    if not _analysis_active(recording_id):
        _enqueue_analysis(recording_id, storage_key, bool(vision))
    # Hold the lane until this project's analysis drains, so the next queued
    # project starts after, never beside it.
    deadline = time.time() + 3600
    while time.time() < deadline and _analysis_active(recording_id):
        time.sleep(3)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM studio_candidates WHERE recording_id = %s",
                (recording_id,),
            )
            candidates = cur.fetchone()[0]
            cur.execute(
                "SELECT kind, error FROM jobs WHERE kind IN ('detect_moments', 'suggest_clips') "
                "AND payload->>'recording_id' = %s AND state = 'failed' "
                "ORDER BY updated_at DESC LIMIT 1",
                (recording_id,),
            )
            failed = cur.fetchone()
            if failed:
                note = f"Analysis failed ({failed[0]}): {(failed[1] or '')[:120]}"
            elif candidates:
                note = f"Analysis complete: {candidates} candidates."
            else:
                note = "Analysis found no clippable candidates."
            cur.execute(
                "UPDATE projects SET stage_note = %s WHERE id = %s", (note, project_id)
            )


@jobs.register("run_project")
def run_project(payload: dict) -> None:
    """Analyse the oldest queued project. One at a time, across all workers."""
    conn = db.connect(direct=True)
    try:
        with conn.cursor() as cur:
            while True:
                cur.execute("SELECT pg_try_advisory_lock(%s)", (PROJECT_LOCK_KEY,))
                if cur.fetchone()[0]:
                    break
                conn.rollback()
                time.sleep(2)
            # Claim the oldest queued project, not necessarily the one this job
            # was enqueued for, so the queue is FIFO even under concurrency.
            cur.execute(
                "UPDATE projects SET queued_at = NULL, updated_at = now() "
                "WHERE id = (SELECT id FROM projects WHERE queued_at IS NOT NULL "
                "ORDER BY queued_at, created_at LIMIT 1) RETURNING id"
            )
            row = cur.fetchone()
            conn.commit()
        if row is None:
            _unlock_project_lane(conn)
            return
        try:
            _run_project_analysis(str(row[0]))
        finally:
            _unlock_project_lane(conn)
    finally:
        conn.close()
