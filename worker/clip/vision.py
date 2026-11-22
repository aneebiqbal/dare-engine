"""A bounded, sampled vision pass that suggests clips the admin never marked.

The cheap audio/scene detector finds moments from sound. This pass adds a small
vision-language model that actually looks at frames: it samples a few frames per
minute (never every frame), asks the VLM whether each window is a striking,
clippable moment, and returns ranked suggestions with a reason and the frame.

Memory discipline: the VLM is loaded only for this pass and unloaded immediately
after, verified against the model inventory. It never runs alongside Whisper or
the LLM.

Compute path: an Ollama vision model (Qwen2.5-VL-7B, Apache-2.0) on the host
bridge. With no bridge or no vision model the pass reports `sampled: false` and
adds nothing — it never pretends.
"""
from __future__ import annotations

import base64
import dataclasses
import json
import os
import pathlib
import subprocess
import tempfile
import time
import urllib.request

SAMPLE_FPS = float(os.environ.get("VISION_SAMPLE_FPS", "0.2"))   # one frame / 5 s
MAX_FRAMES = int(os.environ.get("VISION_MAX_FRAMES", "40"))
WINDOW = 12.0
MODEL = os.environ.get("VISION_MODEL", "qwen2.5vl:7b")
BRIDGE = os.environ.get("MODEL_BRIDGE_URL", "http://host.docker.internal:8798").rstrip("/")

PROMPT = (
    "You are a clip editor watching a gameplay recording. This frame is from "
    "{start:.1f}s to {end:.1f}s. Decide whether this window holds a striking, "
    "clippable moment worth a short vertical video. Answer with JSON only: "
    '{"clippable": true|false, "score": 0.0-1.0, "reason": "one short sentence"}'
)


@dataclasses.dataclass
class Suggestion:
    start: float
    end: float
    score: float
    reason: str
    thumb_path: str

    def as_dict(self) -> dict:
        return {
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "score": round(self.score, 3),
            "reason": self.reason,
        }


def sample_frames(path: str, out_dir: str) -> list[tuple[float, str]]:
    """Extract one frame every 1/SAMPLE_FPS seconds. Returns (second, file)."""
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", path,
         "-vf", f"fps={SAMPLE_FPS:g}", "-q:v", "4", str(out / "frame_%05d.jpg")],
        capture_output=True, check=True,
    )
    frames = sorted(out.glob("frame_*.jpg"))
    return [((i + 1) / SAMPLE_FPS, str(f)) for i, f in enumerate(frames)][:MAX_FRAMES]


def _post(url: str, payload: dict, timeout: float = 300) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _get(url: str, timeout: float = 10) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read())


def describe(frame_path: str, start: float, end: float, model: str = MODEL) -> dict:
    """Ask the host bridge's VLM about one frame. Never raises: a bad reply is a skip."""
    try:
        raw = pathlib.Path(frame_path).read_bytes()
    except OSError as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    try:
        return _post(
            BRIDGE + "/vlm",
            {
                "image": base64.b64encode(raw).decode(),
                "prompt": PROMPT.format(start=start, end=end),
                "model": model,
            },
        )
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def unload(model: str = MODEL) -> bool:
    """Unload the VLM and verify it is gone. Real, not assumed."""
    try:
        _post(BRIDGE + "/models/unload", {"name": model}, timeout=60)
        status = _get(BRIDGE + "/models", timeout=10)
    except Exception:
        return False
    running = [m.get("name") for m in status.get("ollama", {}).get("running", [])]
    return model not in running


def _overlaps(a: Suggestion, b: Suggestion) -> bool:
    return not (a.end <= b.start or a.start >= b.end)


def suggest(
    path: str,
    top_n: int = 5,
    *,
    sampler=None,
    describe_fn=None,
    unload_fn=None,
    model: str = MODEL,
    tmp_root: str | None = None,
) -> tuple[list[Suggestion], dict]:
    """Rank sampled windows. Returns (suggestions, meta).

    `sampler`, `describe_fn` and `unload_fn` are injectable so the pass is
    unit-testable without a model or a recording.
    """
    sampler = sampler or sample_frames
    describe_fn = describe_fn or describe
    unload_fn = unload_fn or unload
    started = time.time()
    owner = tempfile.TemporaryDirectory(prefix="vision-", dir=tmp_root)
    with owner as tmp:
        try:
            frames = sampler(path, tmp)
        except Exception as exc:
            return [], {
                "sampled": False,
                "error": f"{type(exc).__name__}: {exc}",
                "model": model,
                "frames": 0,
                "seconds_added": round(time.time() - started, 2),
            }
        scored: list[Suggestion] = []
        for t, frame in frames:
            start = max(0.0, t - WINDOW / 2.0)
            reply = describe_fn(frame, start, start + WINDOW, model)
            if not reply.get("clippable"):
                continue
            scored.append(
                Suggestion(
                    start=start,
                    end=start + WINDOW,
                    score=float(reply.get("score") or 0.0),
                    reason=str(reply.get("reason") or "").strip(),
                    thumb_path=frame,
                )
            )
        scored.sort(key=lambda s: s.score, reverse=True)
        chosen: list[Suggestion] = []
        for s in scored:
            if all(not _overlaps(s, c) for c in chosen):
                chosen.append(s)
            if len(chosen) >= top_n:
                break
        chosen.sort(key=lambda s: s.start)
        unloaded = unload_fn(model)
        return chosen, {
            "sampled": True,
            "model": model,
            "frames": len(frames),
            "unloaded": unloaded,
            "seconds_added": round(time.time() - started, 2),
        }
