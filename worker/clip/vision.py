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
import shutil
import subprocess
import tempfile
import time
import urllib.request

SAMPLE_FPS = float(os.environ.get("VISION_SAMPLE_FPS", "0.2"))   # one frame / 5 s
MAX_FRAMES = int(os.environ.get("VISION_MAX_FRAMES", "40"))
WINDOW = 12.0
FRAMES_PER_WINDOW = int(os.environ.get("VISION_FRAMES_PER_WINDOW", "2"))
MODEL = os.environ.get("VISION_MODEL", "qwen2.5vl:7b")
BRIDGE = os.environ.get("MODEL_BRIDGE_URL", "http://host.docker.internal:8798").rstrip("/")

PROMPT = (
    "You are a clip editor watching a gameplay recording. This frame is from "
    "{start:.1f}s to {end:.1f}s. Decide whether this window holds a striking, "
    "clippable moment worth a short vertical video. Answer with JSON only: "
    '{{"clippable": true|false, "score": 0.0-1.0, "reason": "one short sentence"}}'
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


def unload(model: str = MODEL, timeout: float = 10.0) -> bool:
    """Unload the VLM and verify it is gone. Ollama unloads asynchronously, so poll."""
    try:
        _post(BRIDGE + "/models/unload", {"name": model}, timeout=60)
    except Exception:
        return False
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status = _get(BRIDGE + "/models", timeout=10)
        except Exception:
            return False
        running = [m.get("name") for m in status.get("ollama", {}).get("running", [])]
        if model not in running:
            return True
        time.sleep(0.5)
    return False


def sample_window_frames(path: str, out_dir: str, start: float, end: float) -> list[str]:
    """A few frames from one candidate window. Never the whole video."""
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    length = max(1.0, end - start)
    rate = FRAMES_PER_WINDOW / length
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-y",
         "-ss", f"{start:.3f}", "-i", path, "-t", f"{length:.3f}",
         "-vf", f"fps={rate:g}", "-q:v", "3", str(out / "frame_%05d.jpg")],
        capture_output=True, check=True,
    )
    return [str(f) for f in sorted(out.glob("frame_*.jpg"))][:FRAMES_PER_WINDOW]


def score_windows(
    path: str,
    windows: list[tuple[float, float]],
    *,
    model: str = MODEL,
    sampler=None,
    describe_fn=None,
    unload_fn=None,
    thumb_dir: str | None = None,
    tmp_root: str | None = None,
) -> tuple[list[dict], dict]:
    """Score only the given windows, a few frames each, with the VLM.

    Returns one score per window (0.0 when the model finds nothing striking),
    plus meta. When `thumb_dir` is given the judged frame is copied there so it
    survives the temp directory. The model is unloaded and verified.
    """
    sampler = sampler or sample_window_frames
    describe_fn = describe_fn or describe
    unload_fn = unload_fn or unload
    started = time.time()
    scored: list[dict] = []
    frames_seen = 0
    errors = 0
    with tempfile.TemporaryDirectory(prefix="vision-win-", dir=tmp_root) as tmp:
        for start, end in windows:
            try:
                frames = sampler(path, tmp, start, end)
            except Exception:
                scored.append({"start": start, "end": end, "score": 0.0,
                               "reason": None, "thumb_path": None})
                continue
            frames_seen += len(frames)
            best: dict | None = None
            for frame in frames:
                reply = describe_fn(frame, start, end, model)
                if reply.get("error"):
                    errors += 1
                    continue
                value = float(reply.get("score") or 0.0)
                if best is None or value > best["score"]:
                    best = {
                        "start": start,
                        "end": end,
                        "score": value if reply.get("clippable") else 0.0,
                        "reason": str(reply.get("reason") or "").strip() or None,
                        "thumb_path": frame,
                    }
            if best and best.get("thumb_path") and thumb_dir:
                dest = pathlib.Path(thumb_dir) / f"{start:.0f}_{end:.0f}.jpg"
                try:
                    pathlib.Path(thumb_dir).mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(best["thumb_path"], dest)
                    best["thumb_path"] = str(dest)
                except OSError:
                    best["thumb_path"] = None
            scored.append(best or {"start": start, "end": end, "score": 0.0,
                                   "reason": None, "thumb_path": None})
        unloaded = unload_fn(model)
    return scored, {
        "sampled": True,
        "model": model,
        "windows": len(windows),
        "frames": frames_seen,
        "errors": errors,
        "unloaded": unloaded,
        "seconds": round(time.time() - started, 2),
    }


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
