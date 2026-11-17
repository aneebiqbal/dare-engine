"""Real job handlers. Each renders one mission window into a Short."""
from __future__ import annotations

import json
import pathlib
import tempfile

from clip.engine import Result, render_short
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


def _stage(clip_id: str, stage: str, progress: int, error: str | None = None) -> None:
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE clips SET stage = %s, progress = %s, error = %s WHERE id = %s",
                (stage, progress, error, clip_id),
            )


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
        _stage(clip_id, "fetch", STAGES["fetch"])

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

        _stage(clip_id, "transcribe", STAGES["transcribe"])
        _stage(clip_id, "select", STAGES["select"])
        _stage(clip_id, "render", STAGES["render"])

        card = payload["card"]
        result: Result = render_short(
            str(recording),
            card,
            start,
            end,
            str(tmp / "out"),
            payload.get("result", ""),
            payload.get("layout") or layout,
            None,
            words_abs=words_abs,
            caption_style=payload.get("caption_style") or caption_style or "word",
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
