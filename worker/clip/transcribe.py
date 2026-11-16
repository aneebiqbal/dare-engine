"""faster-whisper word timestamps over the mission window only."""
from __future__ import annotations

import dataclasses
import os
import threading

_lock = threading.Lock()
_model = None


@dataclasses.dataclass(frozen=True)
class Word:
    start: float
    end: float
    text: str


def _load():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(
            os.environ.get("WHISPER_MODEL", "small"),
            device=os.environ.get("WHISPER_DEVICE", "cpu"),
            compute_type=os.environ.get("WHISPER_COMPUTE_TYPE", "int8"),
        )
    return _model


def transcribe(path: str) -> list[Word]:
    """Word-level timestamps, in seconds from the start of `path`."""
    with _lock:
        segments, _info = _load().transcribe(
            path, word_timestamps=True, vad_filter=True, beam_size=1
        )
    words: list[Word] = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append(Word(float(w.start), float(w.end), text))
    return words
