"""Cheap whole-video scan and candidate ranking. No model, ever.

This is the stage that makes a 2-hour upload tractable: FFmpeg reads audio
energy, scene cuts and 1 fps frame stats once, and the detector turns them into
a dense shortlist. A model never sees the whole file.

User timestamps are merged as high-priority candidates. They are added to the
AI suggestions, never a replacement for them.
"""
from __future__ import annotations

import dataclasses
import math
import re
import subprocess

from .detect import _audio_energy, _duration, _frame_stats, _scene_changes, _strike

WINDOW = 12.0
STEP = 2.0
MIN_WINDOW = 6.0
SHORTLIST = 20
AI_KEEP = 15
SPEECH_MIN_FRACTION = 0.15

# Weights, strongest signal first.
W_PEAK = 1.0
W_SCENE = 0.8
W_BURST = 1.2
W_STRIKE = 0.6
W_SPEECH = 0.8
W_RISE = 0.3


@dataclasses.dataclass
class CheapCandidate:
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


@dataclasses.dataclass
class Ranked:
    start: float
    end: float
    cheap_score: float
    final_score: float
    reasons: list[str]
    origin: str = "ai"  # ai | user
    vision_score: float | None = None
    vision_reason: str | None = None

    def as_dict(self) -> dict:
        return {
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "cheap_score": round(self.cheap_score, 3),
            "final_score": round(self.final_score, 3),
            "reasons": self.reasons,
            "origin": self.origin,
            "vision_score": round(self.vision_score, 3) if self.vision_score is not None else None,
            "vision_reason": self.vision_reason,
        }


@dataclasses.dataclass
class ScanResult:
    duration: float
    candidates: list[CheapCandidate]
    speech_fraction: float
    no_speech: bool

    def as_dict(self) -> dict:
        return {
            "duration": round(self.duration, 2),
            "candidates": [c.as_dict() for c in self.candidates],
            "speech_fraction": round(self.speech_fraction, 3),
            "no_speech": self.no_speech,
        }


def _median(values: list[float]) -> float:
    return sorted(values)[len(values) // 2] if values else -80.0


def speech_activity(path: str) -> list[float]:
    """Per-second speech activity from FFmpeg's silencedetect. No model.

    1.0 = active (not silence), 0.0 = silence. A file with no audio stream is
    all silence, which the pipeline reports as "no speech detected".
    """
    duration = _duration(path)
    seconds = max(1, int(math.ceil(duration)))
    active = [1.0] * seconds
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-af", "silencedetect=noise=-35dB:d=0.4", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    starts = [float(m) for m in re.findall(r"silence_start:\s*(-?[0-9.]+)", proc.stderr)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*(-?[0-9.]+)", proc.stderr)]
    for raw_start, raw_end in zip(starts, ends):
        lo = max(0, int(math.floor(raw_start)))
        hi = min(seconds, int(math.ceil(raw_end)))
        for i in range(lo, hi):
            active[i] = 0.0
    # A trailing silence with no silence_end runs to the end of the file.
    if len(starts) > len(ends):
        lo = max(0, int(math.floor(starts[-1])))
        for i in range(lo, seconds):
            active[i] = 0.0
    return active


def _score_window(
    start: float,
    end: float,
    energy: list[float],
    scenes: list[float],
    speech: list[float],
    frames: list[tuple[float, float]],
) -> tuple[float, list[str]]:
    duration = max(1e-6, end - start)
    lo, hi = int(math.floor(start)), int(math.ceil(end))

    seg = energy[lo:hi]
    peak = max(seg) if seg else -80.0
    baseline = _median(energy)
    peak_score = max(0.0, peak - baseline) / 20.0

    rise = 0.0
    for a, b in zip(seg, seg[1:]):
        if b - a > 2.0:
            rise += b - a
    rise_score = rise / 20.0

    scene_score = sum(1 for t in scenes if start <= t < end) / duration

    burst = 0
    for i in range(lo, min(hi, len(energy) - 1)):
        if energy[i] < baseline - 3.0 and energy[i + 1] > baseline + 3.0:
            burst = 1
            break

    lo_f, hi_f = lo, min(hi, len(frames))
    strike = (
        sum(_strike(*frames[i]) for i in range(lo_f, hi_f)) / (hi_f - lo_f)
        if hi_f > lo_f else 0.0
    )
    speech_density = (
        sum(speech[lo:hi]) / len(speech[lo:hi]) if hi > lo and hi <= len(speech) else 0.0
    )

    score = (
        W_PEAK * peak_score
        + W_SCENE * scene_score
        + W_BURST * burst
        + W_STRIKE * strike
        + W_SPEECH * speech_density
        + W_RISE * rise_score
    )
    reasons = []
    if speech_density >= 0.6:
        reasons.append("commentary")
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
    start: float, end: float, energy: list[float], frames: list[tuple[float, float]]
) -> float:
    """The strongest second in a window: loud first, then visually striking."""
    lo, hi = int(math.floor(start)), int(math.ceil(end))
    best = (start + end) / 2.0
    best_key = None
    for i in range(lo, min(hi, len(energy))):
        strike = _strike(*frames[i]) if i < len(frames) else 0.0
        key = (energy[i], strike)
        if best_key is None or key > best_key:
            best_key = key
            best = float(i)
    return best


def cheap_scan(path: str, shortlist: int = SHORTLIST) -> ScanResult:
    """Rank candidate windows over the whole recording. No timestamps, no model."""
    duration = _duration(path)
    energy = _audio_energy(path)
    scenes = _scene_changes(path)
    frames = _frame_stats(path)
    speech = speech_activity(path)
    speech_fraction = sum(speech) / len(speech) if speech else 0.0
    no_speech = speech_fraction < SPEECH_MIN_FRACTION

    candidates: list[CheapCandidate] = []
    t = 0.0
    while t + MIN_WINDOW <= duration + 1e-6:
        end = min(duration, t + WINDOW)
        peak = _peak_second(t, end, energy, frames)
        start = max(0.0, min(peak - WINDOW / 2.0, max(0.0, duration - WINDOW)))
        end = min(duration, start + WINDOW)
        score, reasons = _score_window(start, end, energy, scenes, speech, frames)
        candidates.append(CheapCandidate(start, end, score, reasons))
        t += STEP

    candidates.sort(key=lambda c: c.score, reverse=True)
    chosen: list[CheapCandidate] = []
    for c in candidates:
        if all(c.end <= o.start or c.start >= o.end for o in chosen):
            chosen.append(c)
        if len(chosen) >= shortlist:
            break
    chosen.sort(key=lambda c: c.start)
    return ScanResult(duration, chosen, speech_fraction, no_speech)


def _overlaps(a_start: float, a_end: float, b_start: float, b_end: float) -> bool:
    return not (a_end <= b_start or a_start >= b_end)


def rank_candidates(
    candidates: list[CheapCandidate],
    timestamps: list[dict],
    duration: float,
    shortlist: int = SHORTLIST,
) -> tuple[list[Ranked], list[str]]:
    """Merge cheap candidates and user timestamps into a ranked shortlist.

    The AI suggestions are always kept (top `AI_KEEP`); user windows are added
    as high-priority candidates and never replace them. Returns (ranked, notes).
    """
    notes: list[str] = []
    peak = max((c.score for c in candidates), default=0.0) or 1.0
    ai = [
        Ranked(c.start, c.end, c.score / peak, c.score / peak, list(c.reasons), "ai")
        for c in candidates
    ]
    ai.sort(key=lambda c: c.final_score, reverse=True)
    selected: list[Ranked] = []
    for c in ai:
        if all(not _overlaps(c.start, c.end, s.start, s.end) for s in selected):
            selected.append(c)
        if len(selected) >= AI_KEEP:
            break

    users: list[Ranked] = []
    for ts in timestamps or []:
        try:
            start = float(ts.get("start"))
            end = float(ts.get("end"))
        except (TypeError, ValueError):
            notes.append(f"ignored a timestamp that is not a number: {ts!r}")
            continue
        if start < 0 or end <= start or end > duration + 1e-6:
            notes.append(
                f"ignored a timestamp outside the video ({start:.1f}-{end:.1f}s)"
            )
            continue
        users.append(
            Ranked(start, end, 0.9, 0.9, ["you marked this"], "user")
        )
    users.sort(key=lambda c: c.start)

    for u in users:
        clash = next(
            (s for s in selected if _overlaps(u.start, u.end, s.start, s.end)), None
        )
        if clash is not None:
            # The user's exact window wins over the overlapping AI window.
            selected.remove(clash)
        if len(selected) < shortlist:
            selected.append(u)

    selected.sort(key=lambda c: c.start)
    return selected[:shortlist], notes
