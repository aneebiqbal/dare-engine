"""Automatic moment detection.

Scores the whole recording once (transcript + audio + scene changes) and returns
ranked candidate windows, so the admin never types a timestamp. Cheap signals
run over the whole file; only the top candidates need the expensive video pass.

Compute path: CUDA Whisper when a GPU is present, else CPU int8. The choice is
logged and returned so the UI can show it.
"""
from __future__ import annotations

import array
import dataclasses
import math
import re
import subprocess

from .transcribe import Word, transcribe, unload

# Configurable marker phrases, lower-cased. Add to this list, not to code.
MARKER_PHRASES = (
    "clip that",
    "clip it",
    "oh my god",
    "oh god",
    "no way",
    "lets go",
    "let's go",
    "holy shit",
    "wow",
    "insane",
    "clutch",
    "gg",
    "lol",
)

WINDOW = 12.0
STEP = 2.0
MIN_WINDOW = 6.0
SAMPLE_RATE = 16000

# Weights, strongest signal first.
W_SPEECH = 1.0
W_MARKER = 2.0
W_PEAK = 1.0
W_SCENE = 0.8
W_BURST = 1.2
W_STRIKE = 0.6


@dataclasses.dataclass
class ComputePath:
    whisper_device: str
    whisper_compute_type: str
    encoder: str
    gpu: bool

    def as_dict(self) -> dict:
        return {
            "whisper_device": self.whisper_device,
            "whisper_compute_type": self.whisper_compute_type,
            "encoder": self.encoder,
            "gpu": self.gpu,
        }


@dataclasses.dataclass
class Candidate:
    start: float
    end: float
    score: float
    reasons: list[str]

    def as_dict(self) -> dict:
        return {
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "score": round(self.score, 3),
            "reasons": self.reasons,
        }


def detect_compute_path() -> ComputePath:
    """CUDA Whisper when a GPU is present, else CPU int8. Never assume a GPU."""
    from .transcribe import actual_compute, whisper_compute

    device, compute = actual_compute() or whisper_compute()
    from .engine import detect_encoder

    enc = detect_encoder()
    return ComputePath(device, compute, enc, device in ("cuda", "mlx"))


def _duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def _audio_energy(path: str) -> list[float]:
    """Per-second RMS in dB, streamed from FFmpeg. Never holds the file."""
    proc = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    frame = SAMPLE_RATE * 2  # one second of signed 16-bit mono
    energy: list[float] = []
    buf = b""
    while True:
        chunk = proc.stdout.read(frame)
        if not chunk:
            break
        buf += chunk
        while len(buf) >= frame:
            block, buf = buf[:frame], buf[frame:]
            samples = array.array("h")
            samples.frombytes(block)
            total = 0
            for s in samples:
                total += s * s
            rms = math.sqrt(total / len(samples))
            energy.append(20 * math.log10(rms / 32768.0 + 1e-9))
    proc.wait()
    return energy


def _scene_changes(path: str) -> list[float]:
    """Timestamps of scene cuts from FFmpeg's scene detector."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-vf", "select=gt(scene\\,0.35),showinfo", "-an", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    return [float(m.group(1)) for m in re.finditer(r"pts_time:([0-9.]+)", proc.stderr)]


def _frame_stats(path: str) -> list[tuple[float, float]]:
    """Per-second (mean luma 0-255, contrast 0-255) from 1 fps 32x32 gray frames.

    Cheap: ~1 KB per second. Used so the cold open never lands on a dark or
    blown-out frame.
    """
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-vf", "fps=1,scale=32:32,format=gray", "-f", "rawvideo", "-"],
        capture_output=True,
    )
    frame = 32 * 32
    raw = proc.stdout
    stats: list[tuple[float, float]] = []
    for i in range(0, len(raw) - frame + 1, frame):
        block = raw[i:i + frame]
        mean = sum(block) / frame
        contrast = math.sqrt(sum((b - mean) ** 2 for b in block) / frame)
        stats.append((mean, contrast))
    return stats


def _strike(mean: float, contrast: float) -> float:
    """0..1: a visible, contrasty frame. Dark and blown-out frames score 0."""
    brightness = mean / 255.0
    if brightness < 0.08 or brightness > 0.95:
        return 0.0
    return max(0.0, min(1.0, (contrast / 255.0) * 2.0)) * (1.0 - abs(brightness - 0.45))


def _marker_seconds(words: list[Word]) -> set[int]:
    """Seconds where a marker phrase starts in the transcript."""
    lowered = [w.text.lower().strip(".,!?") for w in words]
    hits: set[int] = set()
    for phrase in MARKER_PHRASES:
        parts = phrase.split()
        for i in range(len(lowered) - len(parts) + 1):
            if lowered[i:i + len(parts)] == parts:
                hits.add(int(words[i].start))
    return hits


def _score_window(
    start: float,
    end: float,
    words: list[Word],
    energy: list[float],
    scenes: list[float],
    markers: set[int],
    frames: list[tuple[float, float]] | None = None,
) -> tuple[float, list[str]]:
    duration = max(1e-6, end - start)
    lo, hi = int(math.floor(start)), int(math.ceil(end))

    speech = [w for w in words if start <= (w.start + w.end) / 2 < end]
    speech_score = len(speech) / duration

    seg = energy[lo:hi]
    peak = max(seg) if seg else -80.0
    baseline = sorted(energy)[len(energy) // 2] if energy else -80.0
    peak_score = max(0.0, peak - baseline) / 20.0

    rise = 0.0
    for a, b in zip(seg, seg[1:]):
        if b - a > 2.0:
            rise += b - a
    rise_score = rise / 20.0

    marker_score = sum(1 for s in markers if lo <= s < hi)

    scene_score = sum(1 for t in scenes if start <= t < end) / duration

    burst = 0
    for i in range(lo, min(hi, len(energy) - 1)):
        if energy[i] < baseline - 3.0 and energy[i + 1] > baseline + 3.0:
            burst = 1
            break

    strike = 0.0
    if frames:
        lo_f, hi_f = lo, min(hi, len(frames))
        if hi_f > lo_f:
            strike = sum(_strike(*frames[i]) for i in range(lo_f, hi_f)) / (hi_f - lo_f)

    score = (
        W_SPEECH * speech_score
        + W_MARKER * marker_score
        + W_PEAK * peak_score
        + W_SCENE * scene_score
        + W_BURST * burst
        + W_STRIKE * strike
        + 0.3 * rise_score
    )

    reasons = []
    if speech_score >= 1.5:
        reasons.append("commentary")
    if marker_score:
        reasons.append("marker phrase")
    if peak_score >= 0.5:
        reasons.append("loud moment")
    if scene_score >= 0.15:
        reasons.append("fast cuts")
    if burst:
        reasons.append("quiet then burst")
    if rise_score >= 0.5:
        reasons.append("rising voice")
    if strike >= 0.08:
        reasons.append("striking frame")
    if not reasons:
        reasons.append("steady action")
    return score, reasons


def _peak_second(
    words: list[Word],
    lo: float,
    hi: float,
    energy: list[float],
    frames: list[tuple[float, float]] | None = None,
) -> float:
    """The strongest second in a window.

    Commentary density first, then visual strikingness: a dark or blown-out
    second is never chosen as the cold open.
    """
    scores: dict[int, float] = {}
    for w in words:
        mid = (w.start + w.end) / 2
        if lo <= mid < hi:
            scores[int(mid)] = scores.get(int(mid), 0.0) + 1.0
    if not scores:
        return (lo + hi) / 2

    def key(second: int):
        strike = _strike(*frames[second]) if frames and second < len(frames) else 0.0
        loud = energy[second] if second < len(energy) else -80.0
        return (scores.get(second, 0.0) > 0, strike, scores.get(second, 0.0), loud)

    return float(max(scores, key=key))


def detect_moments(path: str, top_n: int = 5) -> tuple[list[Candidate], ComputePath]:
    """Rank candidate windows over the whole recording. No timestamps typed."""
    duration = _duration(path)
    words = transcribe(path)
    unload()
    energy = _audio_energy(path)
    scenes = _scene_changes(path)
    frames = _frame_stats(path)
    markers = _marker_seconds(words)
    compute = detect_compute_path()

    candidates: list[Candidate] = []
    t = 0.0
    while t + MIN_WINDOW <= duration + 1e-6:
        end = min(duration, t + WINDOW)
        peak = _peak_second(words, t, end, energy, frames)
        # Centre the window on its peak so the cold open lands on the moment.
        start = max(0.0, min(peak - WINDOW / 2.0, max(0.0, duration - WINDOW)))
        end = min(duration, start + WINDOW)
        score, reasons = _score_window(start, end, words, energy, scenes, markers, frames)
        candidates.append(Candidate(start, end, score, reasons))
        t += STEP

    candidates.sort(key=lambda c: c.score, reverse=True)

    # Merge overlapping winners so the admin sees distinct moments.
    chosen: list[Candidate] = []
    for c in candidates:
        if all(c.end <= o.start or c.start >= o.end for o in chosen):
            chosen.append(c)
        if len(chosen) >= top_n:
            break
    chosen.sort(key=lambda c: c.start)
    return chosen, compute
