"""Real job handlers. Each renders one mission window into a Short."""
from __future__ import annotations

import pathlib
import tempfile

from clip.engine import render_short

from . import db, jobs, storage


@jobs.register("render_clip")
def render_clip(payload: dict) -> None:
    clip_id = payload["clip_id"]
    with tempfile.TemporaryDirectory(prefix="render-") as tmp:
        tmp = pathlib.Path(tmp)
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
