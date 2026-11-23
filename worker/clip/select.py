"""Transcript-first moment detection.

Segment the (region) transcript into sentences, grow self-contained windows that
fit the target length, snap every edge to whole words/sentences and de-duplicate
overlaps. Also builds the compact multimodal event timeline the scoring LLM
reads alongside the words.

Design adopted from OpenShorts (sentence-aligned windows), ClipForge (speech-edge
snapping, quality-bar count) and cutawan (self-contained micro-stories).
"""
from __future__ import annotations

import dataclasses
import re

from .transcribe import Word

MIN_SECONDS = 14.0
TARGETS = (15.0, 25.0, 35.0, 45.0)
MAX_SECONDS = 60.0
PAUSE_SPLIT = 0.9
GAP_JOIN_MAX = 1.6
NMS_OVERLAP = 0.5
MAX_CANDIDATES = 80

# Cheap scroll-stopper cues used only to ORDER candidates before scoring; the
# LLM makes the real call. Language-light: punctuation, numbers and a few
# high-signal openers in the languages we expect.
HOOK_PATTERNS = (
    r"\?\s*$",
    r"\d",
    re.escape("!"),
    r"\b(no way|nobody|never|secret|mistake|wrong|insane|clutch|clip that|oh my god)",
    r"\b(nadie|nunca|secreto|error|incre[ií]ble|c[oó]mo)",
    r"\b(tidak|jangan|rahasia|salah|gila|kocak)",
)

_SENTENCE_END = re.compile(r"[.!?…]+[\"'”’]?\s*$")


@dataclasses.dataclass
class Sentence:
    start: float
    end: float
    text: str


@dataclasses.dataclass
class Window:
    start: float
    end: float
    text: str
    words: int
    density: float
    prior: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def segment_sentences(words: list[Word]) -> list[Sentence]:
    """Split on sentence-ending punctuation and long speech pauses."""
    sentences: list[Sentence] = []
    current: list[Word] = []
    for w in words:
        if current:
            gap = w.start - current[-1].end
            ends = bool(_SENTENCE_END.search(current[-1].text))
            if ends or gap >= PAUSE_SPLIT:
                sentences.append(_make_sentence(current))
                current = []
        current.append(w)
    if current:
        sentences.append(_make_sentence(current))
    # Attach only very short interjections ("okay.", "right.") to the last
    # sentence; never glue distinct thoughts together.
    merged: list[Sentence] = []
    for s in sentences:
        if (
            merged
            and len(merged[-1].text.split()) <= 2
            and s.start - merged[-1].end <= PAUSE_SPLIT
        ):
            prev = merged[-1]
            merged[-1] = Sentence(prev.start, s.end, f"{prev.text} {s.text}".strip())
        else:
            merged.append(s)
    return merged


def _make_sentence(words: list[Word]) -> Sentence:
    # Keep whatever punctuation the transcript carries; segmentation uses it when
    # present and speech pauses otherwise (Whisper words are often bare).
    return Sentence(
        words[0].start,
        words[-1].end,
        " ".join(w.text.strip() for w in words).strip(),
    )


def _prior(text: str, duration: float) -> float:
    density = len(text.split()) / max(1.0, duration)
    cue = any(re.search(p, text, re.IGNORECASE) for p in HOOK_PATTERNS)
    return density * (1.6 if cue else 1.0)


def grow_windows(
    sentences: list[Sentence],
    min_seconds: float = MIN_SECONDS,
    max_seconds: float = MAX_SECONDS,
) -> list[Window]:
    """Grow whole-sentence windows that form complete thoughts at the targets."""
    seen: set[tuple[int, int]] = set()
    raw: list[Window] = []
    for i, first in enumerate(sentences):
        j = i
        while j + 1 < len(sentences):
            nxt = sentences[j + 1]
            if nxt.end - first.start > max_seconds:
                break
            if nxt.start - sentences[j].end > GAP_JOIN_MAX:
                break
            j += 1
        full_end = sentences[j].end
        if full_end - first.start < min_seconds:
            continue
        for target in TARGETS:
            want = min(target, full_end - first.start)
            if want < min_seconds:
                continue
            k = j
            while k > i and sentences[k].end - first.start > want:
                k -= 1
            end = sentences[k].end
            if end - first.start < min_seconds:
                continue
            key = (round(first.start, 2), round(end, 2))
            if key in seen:
                continue
            seen.add(key)
            text = " ".join(s.text for s in sentences[i : k + 1]).strip()
            dur = end - first.start
            raw.append(
                Window(
                    first.start,
                    end,
                    text,
                    len(text.split()),
                    len(text.split()) / max(1.0, dur),
                    0.0,
                )
            )
    for w in raw:
        w.prior = _prior(w.text, w.duration)
    return raw


def non_max_suppress(windows: list[Window], limit: int = MAX_CANDIDATES) -> list[Window]:
    """Keep the strongest non-overlapping windows; drop >50% overlaps."""
    ordered = sorted(windows, key=lambda w: w.prior, reverse=True)
    kept: list[Window] = []
    for w in ordered:
        clash = any(_overlap(w, k) > NMS_OVERLAP for k in kept)
        if not clash:
            kept.append(w)
        if len(kept) >= limit:
            break
    kept.sort(key=lambda w: w.start)
    return kept


def _overlap(a: Window, b: Window) -> float:
    lo = max(a.start, b.start)
    hi = min(a.end, b.end)
    inter = max(0.0, hi - lo)
    return inter / max(1e-6, min(a.end - a.start, b.end - b.start))


def event_timeline(
    window: Window,
    *,
    energy: list[float],
    scenes: list[float],
    speech: list[float],
    vision_note: str = "",
) -> str:
    """Compact supporting evidence for the scoring LLM (not the main signal)."""
    lo, hi = int(max(0, window.start)), int(min(len(energy), window.end + 1))
    seg = energy[lo:hi] if hi > lo else []
    if not seg:
        return "no audio evidence"
    peak = max(seg)
    baseline = sorted(energy)[len(energy) // 2] if energy else -80.0
    peak_at = lo + seg.index(peak)
    bursts = sum(
        1
        for i in range(lo, min(hi, len(energy) - 1))
        if energy[i] < baseline - 3.0 and energy[i + 1] > baseline + 3.0
    )
    speech_seg = speech[lo:hi] if hi <= len(speech) else []
    speech_pct = round(100 * sum(speech_seg) / len(speech_seg)) if speech_seg else 0
    cuts = [t for t in scenes if window.start <= t < window.end]
    lines = [
        f"audio: peak {peak:.1f}dB (baseline {baseline:.1f}), loudest at "
        f"{peak_at - int(window.start)}s, {bursts} quiet-to-burst moment(s), "
        f"speech {speech_pct}%",
    ]
    lines.append(
        f"visual: {len(cuts)} scene cut(s)"
        + (f", first at {cuts[0] - window.start:.0f}s" if cuts else "")
    )
    if vision_note:
        lines.append(f"vision: {vision_note}")
    return "\n".join(lines)
