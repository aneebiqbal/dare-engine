"""Choose the audio regions worth transcribing.

A long video is never transcribed in full. The cheap whole-video scan already
produced per-second speech activity, RMS energy and scene cuts; we turn those
into a bounded set of regions that contain real speech and excitement, skipping
silent and music-only stretches.
"""
from __future__ import annotations

import dataclasses

MIN_SPAN = 8.0
MAX_SPAN = 120.0
GAP_JOIN = 5.0
DEFAULT_AUDIO_BUDGET = 5400.0  # 90 min of audio, enough for a 2 h stream


@dataclasses.dataclass
class Region:
    start: float
    end: float
    speech_fraction: float
    peak_db: float


def _baseline(energy: list[float]) -> float:
    return sorted(energy)[len(energy) // 2] if energy else -80.0


def plan_regions(
    speech: list[float],
    energy: list[float],
    scenes: list[float],
    duration: float,
    *,
    max_audio_seconds: float = DEFAULT_AUDIO_BUDGET,
    min_span: float = MIN_SPAN,
    max_span: float = MAX_SPAN,
    gap_join: float = GAP_JOIN,
) -> list[Region]:
    seconds = len(speech)
    if seconds == 0 or not energy:
        return []
    baseline = _baseline(energy)
    cut_near = [False] * seconds
    for t in scenes:
        lo = max(0, int(t) - 2)
        hi = min(seconds, int(t) + 3)
        for i in range(lo, hi):
            cut_near[i] = True

    interesting = [
        (speech[i] > 0 or energy[i] > baseline + 3.0 or cut_near[i])
        for i in range(seconds)
    ]

    spans: list[tuple[int, int]] = []
    i = 0
    while i < seconds:
        if not interesting[i]:
            i += 1
            continue
        j = i
        while j + 1 < seconds:
            if interesting[j + 1]:
                j += 1
                continue
            gap_end = j + 1
            while gap_end < seconds and not interesting[gap_end] and gap_end - j <= gap_join:
                gap_end += 1
            if gap_end < seconds and interesting[gap_end] and gap_end - j <= gap_join:
                j = gap_end
            else:
                break
        if j - i >= min_span:
            spans.append((i, j))
        i = j + 1

    regions: list[Region] = []
    for lo, hi in spans:
        seg = speech[lo : hi + 1]
        frac = sum(seg) / len(seg) if seg else 0.0
        # Music-only or near-silent stretch: no words to score, so skip it.
        if frac < 0.2:
            continue
        peak = max(energy[lo : hi + 1]) if hi >= lo else -80.0
        regions.append(Region(float(lo), float(hi + 1), round(frac, 3), round(peak, 1)))

    # Keep the most exciting spans first, honouring the audio budget.
    regions.sort(key=lambda r: (r.speech_fraction * max(0.0, r.peak_db + 60.0)), reverse=True)
    chosen: list[Region] = []
    used = 0.0
    for r in regions:
        length = r.end - r.start
        if used + length > max_audio_seconds:
            continue
        chosen.append(r)
        used += length
    chosen.sort(key=lambda r: r.start)

    # Split runaway spans so Whisper gets manageable chunks.
    out: list[Region] = []
    for r in chosen:
        cursor = r.start
        while cursor < r.end - 1:
            end = min(cursor + max_span, r.end)
            out.append(Region(cursor, end, r.speech_fraction, r.peak_db))
            cursor = end
    return out
