"""Real job handlers. Each renders one mission window into a Short."""
from __future__ import annotations

import pathlib
import tempfile

from clip.engine import render_short

from . import db, jobs, storage


def _run_ffmpeg(cmd: list[str]) -> None:
    import subprocess

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr[-1500:]}")


@jobs.register("render_clip")
def render_clip(payload: dict) -> None:
    clip_id = payload["clip_id"]
    with tempfile.TemporaryDirectory(prefix="render-") as tmp:
        tmp = pathlib.Path(tmp)

        if payload.get("recording_dir"):
            # Relay path: concatenate the recorded segments, then cut the window.
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
        else:
            recording = tmp / "recording.mp4"
            storage.get_file(payload["recording_key"], str(recording))

        result = render_short(
            str(recording),
            payload["card"],
            float(payload["start"]),
            float(payload["end"]),
            str(tmp / "out"),
            payload.get("result", ""),
        )

        key = f"clips/{clip_id}/short.mp4"
        storage.put_file(key, result.out_path)
        storage.put_file(f"clips/{clip_id}/thumb.jpg", result.thumb_path)
        storage.put_file(f"clips/{clip_id}/captions.srt", result.srt_path)

    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE clips SET file_key = %s, state = 'ready', template = %s, "
                "duration_seconds = %s, title = %s WHERE id = %s",
                (
                    key,
                    result.layout,
                    result.duration,
                    payload["card"].get("hook_text", ""),
                    clip_id,
                ),
            )
