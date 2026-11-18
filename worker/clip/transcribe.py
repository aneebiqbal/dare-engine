"""faster-whisper word timestamps over the mission window only."""
from __future__ import annotations

import dataclasses
import threading

_lock = threading.Lock()
_model = None


@dataclasses.dataclass(frozen=True)
class Word:
    start: float
    end: float
    text: str


def whisper_compute() -> tuple[str, str]:
    """CUDA Whisper when a GPU is present, else CPU int8.

    An explicit non-default WHISPER_DEVICE/WHISPER_COMPUTE_TYPE wins, so an
    operator can pin the path; the default pair means "detect".
    """
    from app.config import settings

    device, compute = settings.whisper_device, settings.whisper_compute_type
    if device == "cpu" and compute == "int8":
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda", "float16"
        except Exception:
            pass
    return device, compute


def _load():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        from app.config import settings

        device, compute = whisper_compute()
        _model = WhisperModel(
            settings.whisper_model,
            device=device,
            compute_type=compute,
        )
    return _model


def transcribe(path: str) -> list[Word]:
    """Word-level timestamps, in seconds from the start of `path`."""
    with _lock:
        segments, _info = _load().transcribe(
            path, word_timestamps=True, vad_filter=False, beam_size=1
        )
    words: list[Word] = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append(Word(float(w.start), float(w.end), text))
    return words
